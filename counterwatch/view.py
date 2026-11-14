"""Draws the advice panel as a PIL image. The tk window shows this image, and test mode saves the
same image as a PNG, so what is reviewed is exactly what the player sees.

Look: near-black navy, condensed slanted display type (Bahnschrift), a warm amber for SWAP, a
cool mint for STAY, coral for enemy threats, cyan for your team. Original, not Blizzard art.
"""
from __future__ import annotations

import re
import time
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import data

W, H = 720, 900
PAD = 32

BG = (10, 13, 20)
PANEL = (19, 24, 35)
PANEL_HI = (27, 34, 49)
LINE = (38, 47, 64)
INK = (238, 242, 248)
SOFT = (196, 204, 218)
MUTE = (128, 139, 160)
AMBER = (255, 178, 63)
MINT = (82, 230, 178)
CORAL = (255, 92, 110)
CYAN = (70, 205, 235)

FONTS = "C:/Windows/Fonts/"
ROLE_LABEL = {"tank": "TANK", "damage": "DAMAGE", "support": "SUPPORT"}


# ---------------------------------------------------------------- fonts / helpers
@lru_cache(maxsize=64)
def disp(size: int, style: str = "Bold Condensed") -> ImageFont.FreeTypeFont:
    try:
        f = ImageFont.truetype(FONTS + "bahnschrift.ttf", size)
        f.set_variation_by_name(style)
        return f
    except Exception:
        return ImageFont.truetype(FONTS + "arialbd.ttf", size)


@lru_cache(maxsize=64)
def body(size: int, weight: str = "") -> ImageFont.FreeTypeFont:
    file = {"": "segoeui.ttf", "semi": "seguisb.ttf", "bold": "segoeuib.ttf"}[weight]
    try:
        return ImageFont.truetype(FONTS + file, size)
    except Exception:
        try:
            return ImageFont.truetype(FONTS + "segoeui.ttf", size)
        except Exception:
            return ImageFont.load_default()


def tw(font, text: str) -> int:
    return int(font.getlength(text))


def wrap(text: str, font, width: int, max_lines: int = 99) -> list[str]:
    """Word-wrap. Never cuts text: when it needs more than max_lines, all the lines come back
    and the caller picks a smaller size or shorter copy (see fits)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if tw(font, trial) <= width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = w
    if cur:
        lines.append(cur)
    return lines


def fits(text: str, font, width: int, max_lines: int) -> list[str] | None:
    """The wrapped lines, or None when the whole text doesn't fit in max_lines."""
    lines = wrap(text, font, width)
    return lines if len(lines) <= max_lines and all(tw(font, l) <= width for l in lines) else None


def shorter(text: str) -> str | None:
    """The same advice one sentence shorter (drops the last sentence), or None."""
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return " ".join(parts[:-1]) if len(parts) > 1 else None


def slanted_text(img: Image.Image, xy, text: str, font, fill, slant: float = 0.16, outline: int = 0):
    """Draw text sheared to the right (an italic feel for the condensed display face).
    outline > 0 draws only the letter outlines, that many px wide (used for a call that is a guess)."""
    x, y = xy
    asc, desc = font.getmetrics()
    h = asc + desc
    w = tw(font, text) + int(h * slant) + 8 + 2 * outline
    layer = Image.new("L", (w, h + 4 + 2 * outline), 0)
    org = (int(h * slant) + outline, outline)
    if outline:
        ImageDraw.Draw(layer).text(org, text, font=font, fill=255, stroke_width=outline, stroke_fill=255)
        inner = Image.new("L", layer.size, 0)
        ImageDraw.Draw(inner).text(org, text, font=font, fill=255)
        from PIL import ImageChops
        layer = ImageChops.subtract(layer, inner)
    else:
        ImageDraw.Draw(layer).text(org, text, font=font, fill=255)
    layer = layer.transform(layer.size, Image.AFFINE, (1, slant, -slant * 0, 0, 1, 0),
                            resample=Image.BICUBIC)
    color = Image.new("RGB", layer.size, fill)
    img.paste(color, (int(x - h * slant - outline), int(y - outline)), layer)
    return w - int(h * slant)


def fit_display(text: str, max_w: int, start: int, minimum: int):
    size = start
    while size > minimum and tw(disp(size), text) + size * 0.2 > max_w:
        size -= 4
    return disp(size)


@lru_cache(maxsize=256)
def portrait(hero_id: str, size: int, grey: bool = False, dim: bool = False) -> Image.Image | None:
    p = data.portrait_path(hero_id)
    if not p:
        return None
    im = Image.open(p).convert("RGB").resize((size, size), Image.LANCZOS)
    if dim:
        im = Image.blend(im, Image.new("RGB", im.size, BG), 0.55)
    if grey:
        im = ImageOps.grayscale(im).convert("RGB")
        im = Image.blend(im, Image.new("RGB", im.size, BG), 0.45)
    return im


def slant_mask(w: int, h: int, cut: int) -> Image.Image:
    """Parallelogram mask: the angled cut is the panel's signature shape."""
    m = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(m).polygon([(cut * 4, 0), (w * 4, 0), ((w - cut) * 4, h * 4), (0, h * 4)], fill=255)
    return m.resize((w, h), Image.LANCZOS)


def slant_box(d: ImageDraw.ImageDraw, x, y, w, h, cut, fill=None, outline=None, width=1):
    pts = [(x + cut, y), (x + w, y), (x + w - cut, y + h), (x, y + h)]
    d.polygon(pts, fill=fill, outline=outline, width=width)


def _hero_names_in(text: str) -> set[str]:
    found = set()
    low = text.lower()
    for hid, h in data.heroes().items():
        n = h["name"].lower()
        if re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", low):
            found.add(hid)
    return found


# ---------------------------------------------------------------- the panel
def render(result: dict | None, status: dict | None = None) -> Image.Image:
    """result: pipeline output plus "timing" (ms) and "when"; status: {"mode", "note"}."""
    t0 = time.perf_counter()
    status = status or {}
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _top_bar(img, d, result, status)

    if result is None:
        _waiting(img, d, status)
    elif result.get("error"):
        _message(img, d, "ERROR", CORAL, result["error"], "The details are in logs/counterwatch.log.")
    elif not (result.get("state") or {}).get("board_open"):
        _message(img, d, "NO BOARD", MUTE, "The scoreboard wasn't open in that capture.",
                 "Hold Tab a beat longer, until the board is fully drawn.")
    else:
        try:
            if enemy_hidden(result.get("state") or {}):
                _hidden(img, d, result)
            else:
                _advice(img, d, result)
        except Exception as e:  # never let a bad field take the window down
            import logging, traceback
            logging.getLogger("counterwatch").error("draw failed: %s", traceback.format_exc())
            img.paste(BG, (0, 62, W, H - 50))
            _message(img, d, "ERROR", CORAL, f"Couldn't draw that advice: {e}", "See logs/counterwatch.log.")

    _footer(d, result)
    if result is not None:
        result.setdefault("timing", {})["draw_ms"] = (time.perf_counter() - t0) * 1000
    return img


def _top_bar(img, d, result, status):
    slant_box(d, PAD, 24, 22, 16, 6, fill=AMBER)
    d.text((PAD + 30, 21), "COUNTERWATCH", font=disp(19, "Bold SemiCondensed"), fill=INK)
    # right side: mode pill
    mode = status.get("mode", "live")
    label, col = {"live": ("LIVE", MINT), "replay": ("REPLAY", AMBER), "test": ("TEST IMAGE", CYAN),
                  "idle": ("WAITING FOR OVERWATCH", MUTE)}.get(mode, (mode.upper(), MUTE))
    f = disp(14, "SemiBold SemiCondensed")
    x = W - PAD - tw(f, label) - 18
    d.ellipse((x, 27, x + 8, 35), fill=col)
    d.text((x + 16, 22), label, font=f, fill=col)
    if result and "stub" in (result.get("sources") or {}).values():
        which = " + ".join(k for k, v in result["sources"].items() if v == "stub")
        tag = f"STUB {which.upper()}"
        x2 = x - tw(f, tag) - 34
        d.rounded_rectangle((x2, 19, x2 + tw(f, tag) + 18, 39), 10, outline=CORAL)
        d.text((x2 + 9, 21), tag, font=f, fill=CORAL)
    d.line((PAD, 60, W - PAD, 60), fill=LINE)


def _waiting(img, d, status):
    y = 200
    slanted_text(img, (PAD + 8, y), "HOLD TAB", disp(118), INK)
    d.text((PAD, y + 150), status.get("note") or "In Overwatch, hold Tab for a moment.",
           font=body(24, "semi"), fill=SOFT)
    lines = ["Counterwatch reads the scoreboard from the screen and calls your",
             "swap, or tells you to stay. Nothing is read from the game itself."]
    for i, line in enumerate(lines):
        d.text((PAD, y + 196 + i * 30), line, font=body(19), fill=MUTE)


def _message(img, d, call, col, line1, line2):
    y = 150
    slanted_text(img, (PAD + 8, y), call, disp(118), col)
    for i, line in enumerate(wrap(line1, body(26, "semi"), W - 2 * PAD, 3)):
        d.text((PAD, y + 150 + i * 36), line, font=body(26, "semi"), fill=INK)
    n = len(wrap(line1, body(26, "semi"), W - 2 * PAD, 3))
    d.text((PAD, y + 160 + n * 36), line2, font=body(19), fill=MUTE)


# ---------------------------------------------------------------- how sure the call is
SURE_AT = 0.5        # below this confidence any call is drawn as a guess
SWAP_SURE_AT = 0.65  # a swap needs this for the full-weight call; 50-65% reads "MAYBE SWAP"
MIN_ENEMIES = 3      # fewer enemy heroes read than this and the board is not clear enough


def _read_ok(row: dict) -> bool:
    return row.get("hero") in data.heroes() and (row.get("conf") is None or row["conf"] >= 0.5)


def _dupes(rows: list[dict]) -> set[str]:
    """A hero can only be on a team once, so a repeated id is a misread."""
    seen, dup = set(), set()
    for r in rows:
        h = r.get("hero")
        if h in data.heroes():
            (dup if h in seen else seen).add(h)
    return dup


def certainty(st: dict, adv: dict) -> dict:
    """{"sure": bool, "word": the caption when not sure, "why": one short line, "read": n, "conf"}."""
    enemy = st.get("enemy_team") or []
    dup = _dupes(enemy)
    read = sum(1 for r in enemy if _read_ok(r) and r["hero"] not in dup)
    conf = float(adv.get("confidence") or 0)
    if read < MIN_ENEMIES:
        why = "Hold Tab until the whole board is drawn, then check again: " \
              + (f"only {read} of 5 enemies were read." if read else "no enemies were read.")
        return {"sure": False, "word": "NEED A CLEARER BOARD", "why": why, "read": read, "conf": conf}
    if conf < SURE_AT:
        return {"sure": False, "word": "NOT SURE YET", "why": "It's close: play it for another fight, then check again.",
                "read": read, "conf": conf}
    if adv.get("action") == "swap" and adv.get("to") and conf < SWAP_SURE_AT:
        return {"sure": False, "word": "MAYBE SWAP", "maybe": True,
                "why": "Close call: swap only if the next fight goes the same way.",
                "read": read, "conf": conf}
    return {"sure": True, "word": None, "why": None, "read": read, "conf": conf}


def _clean_reasons(headline: str, reasons: list[str]) -> list[str]:
    """Drop a reason the headline already says (the engine often leads with reason 01)."""
    h = re.sub(r"[^a-z0-9 ]", "", headline.lower())
    hb = re.sub(r"[^a-z0-9 ]", "", headline.split(":", 1)[-1].lower()).strip()  # after "Into their X:"
    out = []
    for r in reasons:
        if not r:
            continue
        body_ = r.split(":", 1)[1] if ":" in r else r
        b = re.sub(r"[^a-z0-9 ]", "", body_.lower()).strip()
        if b and len(b) > 12 and (b in h or (len(hb) > 12 and hb in b)):
            continue
        out.append(r)
    return out[:3]


def swap_when(st: dict, adv: dict) -> str | None:
    """"now" (dead, so swap on this respawn), "next_death", or None (hero not read)."""
    if adv.get("when") in ("now", "next_death"):
        return adv["when"]
    me = adv.get("hero_now") or st.get("my_hero")
    if not me or me not in data.heroes():
        return None
    dead = any(r.get("dead") for r in st.get("my_team") or [] if r.get("hero") == me)
    return "now" if dead else "next_death"


def call_label(st: dict, adv: dict, cert: dict) -> tuple[str, bool]:
    """The caps line above the hero name: the timing a player needs mid-fight.
    Returns (text, urgent); urgent draws it as a solid bar (you are dead: act now)."""
    when = swap_when(st, adv)
    if cert.get("maybe"):
        return {"now": ("YOU'RE DEAD · MAYBE SWAP", False),
                "next_death": ("MAYBE SWAP ON NEXT DEATH", False)}.get(when, ("MAYBE PICK", False))
    if not cert["sure"]:
        return cert["word"] + "  ·  MAYBE SWAP", False
    return {"now": ("SWAP NOW, YOU'RE DEAD", True),
            "next_death": ("SWAP ON NEXT DEATH", False)}.get(when, ("PICK", False))


_CALL_PREFIX = re.compile(r"^\s*(?:swap to|go|stay|pick)\s+[^:;.]{1,40}?(?:\s+into their [^:;]{1,30})?\s*[:;]\s*",
                          re.I)


def why_line(headline: str) -> str:
    """The headline minus any "Swap to X:" / "Stay X;" lead-in: the call above already says it."""
    h = headline or ""
    for hid, rec in data.heroes().items():  # "Soldier: 76" would end the lead-in at its colon
        if ":" in rec["name"]:
            h = h.replace(rec["name"], rec["name"].replace(":", "∶"))
    t = _CALL_PREFIX.sub("", h).strip().replace("∶", ":")
    return t[:1].upper() + t[1:] if t else ""


# ---------------------------------------------------------------- match start: enemy hidden
def enemy_hidden(st: dict) -> bool:
    """True when the game itself is hiding the enemy (setup, before the gates open): the board
    read cleanly, at least four allies are known, and every enemy row is a confident "unknown"
    silhouette. A low-confidence read is a capture problem, not this, and keeps the advice
    screen with NEED A CLEARER BOARD."""
    en = st.get("enemy_team") or []
    allies = [r for r in st.get("my_team") or [] if r.get("hero") in data.heroes()]
    if not en or len(allies) < 4:
        return False
    for r in en:
        if r.get("hero") != "unknown":
            return False
        if r.get("conf") is not None and r["conf"] < 0.5:
            return False
    return True


STYLE_WORD = {"brawl": "brawl", "dive": "dive", "poke": "poke"}


def prefight(st: dict, adv: dict, bans=None) -> dict | None:
    """A soft opening pick for your role from your own team's comp alone (no enemy to judge).
    {"pick": id, "fits": bool (the pick is the hero you are on), "line": str, "alts": [ids]}."""
    heroes, c = data.heroes(), data.counters()
    me = st.get("my_hero") if st.get("my_hero") in heroes else None
    role = st.get("my_role") or data.role(me)
    if role not in ROLE_LABEL:
        return None
    mates = [r["hero"] for r in st.get("my_team") or [] if r.get("hero") in heroes and r["hero"] != me]
    arche: dict[str, set] = {}
    for a, ids in (c.get("archetypes") or {}).items():
        for i in ids:
            arche.setdefault(i, set()).add(a)
    syn = c.get("synergies") or {}
    counts: dict[str, int] = {}
    for m in mates:
        for a in arche.get(m, ()):
            counts[a] = counts.get(a, 0) + 1
    tank = next((m for m in mates if data.role(m) == "tank"), None)
    style = None
    if counts:
        best = max(counts.values())
        tops = [a for a, n in counts.items() if n == best]
        style = next((a for a in tops if tank and a in arche.get(tank, ())), tops[0]) if best >= 2 else None

    def fit(h):
        partners = [m for m in mates if m in syn.get(h, []) or h in syn.get(m, [])]
        return (style in arche.get(h, ()) if style else False), partners

    banned = set(bans or [])
    pool = [a for a in (adv.get("alternatives") or []) if a in heroes and a not in mates and a not in banned]
    pool += [h for h, r in heroes.items() if r["role"] == role and h not in mates and h not in banned
             and h not in pool and h != me and fit(h)[0]]
    good = [h for h in pool if h != me and data.role(h) == role and (fit(h)[0] or fit(h)[1])]
    if not style and not good:
        return None
    around = f" around {data.name(tank)}" if tank and style in arche.get(tank, ()) else ""
    built = f"Your team is set up to {STYLE_WORD.get(style, style)}{around}." if style else ""
    if me:
        in_style, partners = fit(me)
        if in_style or (not style and partners):
            why = f"pairs with {data.name(partners[0])}" if partners else f"suits a {style} comp"
            return {"pick": me, "fits": True, "alts": [],
                    "line": f"{built} {data.name(me)} {why}: start on it.".strip()}
    if not good:
        return None
    pick = good[0]
    p_style, p_partners = fit(pick)
    if style:
        mine = f" {data.name(me)} is a {sorted(arche[me])[0]} hero." if me and arche.get(me) and style not in arche[me] else ""
        tail = f" {data.name(pick)} fits the {style}." if p_style else f" {data.name(pick)} pairs with {data.name(p_partners[0])}."
    else:
        mine, tail = "", f" {data.name(pick)} pairs with {data.name(p_partners[0])}." if p_partners else ""
    return {"pick": pick, "fits": False, "alts": good[1:3], "line": (built + mine + tail).strip()}


def _hidden(img, d, result):
    st, adv = result["state"], result.get("advice") or {}
    me = st.get("my_hero") if st.get("my_hero") in data.heroes() else None
    role = st.get("my_role") or data.role(me)
    y = 84
    who = "MATCH START"
    if me:
        who += f"  ·  ON {data.name(me).upper()}"
    if role:
        who += f"  ·  {ROLE_LABEL.get(role, role.upper())}"
    d.text((PAD + 2, y), who, font=disp(18, "SemiBold SemiCondensed"), fill=MUTE)

    # the state, not a call: the game is hiding them, nothing to judge yet
    f1 = fit_display("ENEMY HIDDEN", W - 2 * PAD - 10, 112, 60)
    slanted_text(img, (PAD + 8, y + 26), "ENEMY HIDDEN", f1, INK)
    y2 = y + 26 + f1.size + 4
    f2 = fit_display("UNTIL THE GATES OPEN", W - 2 * PAD - 10, 52, 32)
    slanted_text(img, (PAD + 8, y2), "UNTIL THE GATES OPEN", f2, CYAN)
    y = y2 + f2.size + 22
    d.text((PAD, y), "The game hides their picks during setup, so there is nothing to counter yet.",
           font=body(19), fill=MUTE)
    y += 46

    pf = prefight(st, adv, result.get("bans"))
    if pf:
        ps = 104
        tx = PAD + 20 + ps + 18
        nm = data.name(pf["pick"]).upper()
        fn = fit_display(nm, W - PAD - 16 - tx, 58, 34)
        tw_ = W - PAD - 20 - tx
        lf = body(19) if fits(pf["line"], body(19), tw_, 3) else body(17)
        lines = wrap(pf["line"], lf, tw_)
        text_h = fn.size + 8 + len(lines) * 26
        if pf["alts"] and y + 42 + max(ps, text_h + 44) + 18 + 14 + 52 > H - 58 - 2 * 92 - 12:
            pf["alts"] = []  # never let the OR row push into the comps
        alt_h = 44 if pf["alts"] else 0
        bh = 42 + max(ps, text_h + alt_h) + 18
        d.rectangle((PAD, y, W - PAD, y + bh), fill=PANEL)
        d.rectangle((PAD, y, PAD + 4, y + bh), fill=MINT)
        lab = "PRE-FIGHT PICK" + (f"  ·  {ROLE_LABEL.get(role, '')}" if role else "")
        d.text((PAD + 20, y + 14), lab, font=disp(17, "Bold SemiCondensed"), fill=MINT)
        px, py = PAD + 20, y + 42
        p = portrait(pf["pick"], ps - 6)
        if p:
            img.paste(Image.new("RGB", (ps, ps), MINT), (px, py), slant_mask(ps, ps, 18))
            img.paste(p, (px + 3, py + 3), slant_mask(ps - 6, ps - 6, 17))
        slanted_text(img, (tx + 4, py - 4), nm, fn, INK)
        for i, line in enumerate(lines):
            d.text((tx + 2, py + fn.size + 6 + i * 26), line, font=lf, fill=SOFT)
        if pf["alts"]:
            ay = py + text_h + 6
            d.text((tx + 2, ay + 5), "OR", font=disp(16, "Bold SemiCondensed"), fill=MUTE)
            ax = tx + 36
            for a_ in pf["alts"]:
                ax = _mini_chip(img, d, ax, ay, a_) + 10
        y += bh + 14

    # what to do next
    bh = 52
    d.rectangle((PAD, y, W - PAD, y + bh), fill=PANEL)
    d.rectangle((PAD, y, PAD + 4, y + bh), fill=AMBER)
    d.text((PAD + 20, y + 17), "NEXT", font=disp(17, "Bold SemiCondensed"), fill=AMBER)
    d.text((PAD + 104, y + 12), "Hold Tab again after first contact.", font=body(22, "semi"), fill=INK)

    comps_h = 2 * 92
    cy = H - 58 - comps_h
    _comp(img, d, cy, "YOUR TEAM", CYAN, st.get("my_team") or [], me=me)
    _comp(img, d, cy + 92, "ENEMY  ·  HIDDEN BY THE GAME", CORAL, st.get("enemy_team") or [], hidden=True)


# ---------------------------------------------------------------- the advice screen
def _advice(img, d, result):
    st, adv = result["state"], result.get("advice") or {}
    cert = certainty(st, adv)
    sure = cert["sure"]
    swap = adv.get("action") == "swap" and adv.get("to")
    accent = (AMBER if swap else MINT) if sure else SOFT
    hero = adv.get("to") if swap else (adv.get("hero_now") or st.get("my_hero"))

    # --- hero block: slanted portrait + the call
    y = 84
    ph = 184
    p = portrait(hero, ph - 8, dim=not sure) if hero in data.heroes() else None
    if p:
        frame = Image.new("RGB", (ph, ph), accent if sure else LINE)
        img.paste(frame, (PAD, y), slant_mask(ph, ph, 30))
        img.paste(p, (PAD + 4, y + 4), slant_mask(ph - 8, ph - 8, 29))
    else:
        slant_box(d, PAD, y, ph, ph, 30, fill=PANEL, outline=LINE)
        d.text((PAD + ph // 2, y + ph // 2), "?", font=disp(90), fill=MUTE, anchor="mm")

    x = PAD + ph + 18
    avail = W - PAD - x
    now = adv.get("hero_now") or st.get("my_hero")
    role = st.get("my_role") or data.role(now)
    who = f"ON {data.name(now).upper()}" if now else "HERO NOT READ"
    if role:
        who += f"  ·  {ROLE_LABEL.get(role, role.upper())}"
    d.text((x + 6, y + 2), who, font=disp(18, "SemiBold SemiCondensed"), fill=MUTE)

    if sure:
        if swap:
            cap, urgent = call_label(st, adv, cert)
            fc = fit_display(cap, avail - 30, 40, 26)
            if urgent:  # dead right now: a solid amber bar, the one thing to do this second
                bw_ = tw(fc, cap) + int(fc.size * 0.2) + 28
                slant_box(d, x + 2, y + 28, bw_, fc.size + 10, 10, fill=AMBER)
                slanted_text(img, (x + 18, y + 30 + (40 - fc.size) * 0.3), cap, fc, BG)
            else:
                slanted_text(img, (x + 6, y + 30 + (40 - fc.size) * 0.5), cap, fc, accent)
            nm = data.name(hero).upper()
            f = fit_display(nm, avail, 104, 48)
            slanted_text(img, (x + 4, y + 72 + (104 - f.size) * 0.6), nm, f, INK)
        else:
            slanted_text(img, (x + 4, y + 18), "STAY", disp(150), accent)
    else:
        # a guess: the caption says so (MAYBE SWAP / NOT SURE YET); the call stays a solid
        # word at reduced contrast, never an outline, so it still reads from across a desk
        cap = call_label(st, adv, cert)[0] if swap else cert["word"]
        slanted_text(img, (x + 6, y + 30), cap, fit_display(cap, avail - 6, 34, 22), AMBER)
        call = data.name(hero).upper() if swap else "STAY"
        dim = MUTE if cert["read"] < MIN_ENEMIES else SOFT
        # same box as a sure swap, so the word never runs into the "% SURE" / "READ" line
        f = fit_display(call, avail, 104 if swap else 96, 48)
        slanted_text(img, (x + 4, y + 72 + (104 - f.size) * 0.6), call, f, dim)

    # confidence: a readable number, not a footnote. With too few enemies read there is
    # nothing to be sure about, so it says how much of the board was read instead.
    conf = cert["conf"]
    by = y + ph - 12
    bw = 170
    if cert["read"] < MIN_ENEMIES:
        d.text((x + 6, by - 9), f"{cert['read']} OF 5 ENEMIES READ", font=disp(21, "Bold SemiCondensed"), fill=AMBER)
    else:
        d.rounded_rectangle((x + 6, by, x + 6 + bw, by + 8), 4, fill=PANEL_HI)
        d.rounded_rectangle((x + 6, by, x + 6 + max(8, int(bw * conf)), by + 8), 4,
                            fill=accent if sure else AMBER)
        d.text((x + bw + 20, by - 9), f"{round(conf * 100)}% SURE", font=disp(21, "Bold SemiCondensed"),
               fill=accent if sure else AMBER)

    # --- text: the largest type that fits, then both comps right underneath
    comps_h = 2 * 92
    foot_top = H - 58
    top = y + ph + 26
    headline = why_line(adv.get("headline") or "")
    reasons = _clean_reasons(headline, adv.get("reasons") or [])
    htp = adv.get("how_to_play") or ""
    alts = [a for a in (adv.get("alternatives") or []) if a in data.heroes()][:3] if (sure and swap) else []
    note = cert["why"]
    if note and any("tab" in r.lower().split() for r in reasons):
        note = None  # the engine already says to check Tab again

    tiers = [(31, 22, 20, 40, 30), (29, 21, 19, 38, 28), (27, 19, 18, 36, 26), (25, 18, 17, 33, 24)]

    def plan(tier, max_rl, n_r, head_lines, use_alts, play):
        """One candidate layout, or None if any block would need more lines than it has:
        text is never cut; a smaller size or a shorter play line is tried instead."""
        hs, rs, ps, hl, rl_h = tier
        hf, rf, pf = body(hs, "semi"), body(rs), body(ps)
        head = fits(headline, hf, W - 2 * PAD, head_lines) if headline else []
        rl = [fits(r, rf, W - 2 * PAD - 44, max_rl) for r in reasons[:n_r]]
        pl = fits(play, pf, W - 2 * PAD - 120, 4) if play else []
        nl = fits(note, pf, W - 2 * PAD - 120, 2) if note else []
        if head is None or pl is None or nl is None or any(r is None for r in rl):
            return None
        h = len(head) * hl + 14 + sum(rl_h * len(x) + 12 for x in rl)
        h += (24 + (rl_h - 2) * len(pl) + 14) if pl else 0
        h += (24 + (rl_h - 2) * len(nl) + 14) if nl else 0
        h += 44 if use_alts else 0
        return dict(hf=hf, rf=rf, pf=pf, hl=hl, rl_h=rl_h, head=head, rl=rl, pl=pl, nl=nl,
                    alts=alts if use_alts else [], h=h)

    budget = foot_top - comps_h - 24 - top
    layout = None
    # content first (every reason beats bigger type), then the biggest type that fits it;
    # the OR picks are only worth keeping while the type stays large
    options = [(t, c) for c in ((3, 3, 2, True), (2, 3, 2, True)) for t in tiers[:2]]
    options += [(t, c) for c in ((3, 3, 2, False), (2, 3, 2, False), (2, 2, 2, False), (2, 2, 1, False))
                for t in tiers]
    plays = [htp]
    while plays[-1] and shorter(plays[-1]):
        plays.append(shorter(plays[-1]))
    for play in plays:  # the full play line first; a sentence shorter only if nothing fits
        for tier, (max_rl, n_r, head_lines, use_alts) in options:
            if use_alts and not alts:
                continue
            cand = plan(tier, max_rl, n_r, head_lines, use_alts, play)
            if cand and cand["h"] <= budget:
                layout = cand
                break
        if layout:
            break
    if layout is None:  # last resort: smallest type, fewer blocks, still never cut
        for n_r in (2, 1, 0):
            layout = plan(tiers[-1], 4, n_r, 3, False, plays[-1])
            if layout:
                break

    L = layout
    y = top
    for line in L["head"]:
        d.text((PAD, y), line, font=L["hf"], fill=INK if sure else SOFT)
        y += L["hl"]
    y += 14
    for i, lines in enumerate(L["rl"]):
        d.text((PAD, y + 2), f"{i + 1:02d}", font=disp(L["rf"].size + 1, "Bold SemiCondensed"),
               fill=accent if sure else MUTE)
        for line in lines:
            d.text((PAD + 44, y), line, font=L["rf"], fill=SOFT)
            y += L["rl_h"]
        y += 12
    for label, lines, col in (("PLAY IT", L["pl"], accent), ("NEXT", L["nl"], AMBER)):
        if not lines:
            continue
        step = L["rl_h"] - 2
        bh = 24 + step * len(lines)
        d.rectangle((PAD, y, W - PAD, y + bh), fill=PANEL)
        d.rectangle((PAD, y, PAD + 4, y + bh), fill=col)
        d.text((PAD + 20, y + 13), label, font=disp(17, "Bold SemiCondensed"), fill=col)
        for i, line in enumerate(lines):
            d.text((PAD + 104, y + 11 + step * i), line, font=L["pf"], fill=INK)
        y += bh + 14
    if L["alts"]:
        d.text((PAD, y + 5), "OR", font=disp(16, "Bold SemiCondensed"), fill=MUTE)
        ax = PAD + 34
        for a in L["alts"]:
            ax = _mini_chip(img, d, ax, y, a) + 10
        y += 44

    # comps follow the text; any spare room goes to the bottom edge, not between the two
    cy = min(y + 14, foot_top - comps_h)
    _comp(img, d, cy, "YOUR TEAM", CYAN, st.get("my_team") or [], me=st.get("my_hero"))
    en = st.get("enemy_team") or []
    label = "ENEMY" if sure else f"ENEMY  ·  {cert['read']} OF 5 READ"
    _comp(img, d, cy + 92, label, CORAL, en, threats=_threats(st, adv) if cert["read"] else set())


def _threats(st: dict, adv: dict) -> set[str]:
    """The enemy heroes the advice is about: the engine's own list if it gives one, else the
    enemies named in the headline / play line first, then in the reasons. At most two, and
    never a hero the reader saw twice (that is a misread, not a threat)."""
    rows = st.get("enemy_team") or []
    dup = _dupes(rows)
    enemy = [r.get("hero") for r in rows if r.get("hero") not in dup]
    if adv.get("threats"):
        return set(adv["threats"]) & set(enemy)
    ours = {adv.get("hero_now"), adv.get("to"), st.get("my_hero"), *(adv.get("alternatives") or [])}
    for text in (" ".join([adv.get("headline") or "", adv.get("how_to_play") or ""]),
                 " ".join(adv.get("reasons") or [])):
        theirs = {h for h, n in ((h, data.name(h).lower()) for h in enemy if h in data.heroes())
                  if f"their {n}" in text.lower()}
        hits = [h for h in _ordered_names(text) if h in enemy and (h not in ours or h in theirs)]
        if hits:
            return set(hits[:2])
    return set()


def _ordered_names(text: str) -> list[str]:
    low, found = text.lower(), []
    for hid, h in data.heroes().items():
        m = re.search(r"(?<![a-z])" + re.escape(h["name"].lower()) + r"(?![a-z])", low)
        if m:
            found.append((m.start(), hid))
    return [h for _, h in sorted(found)]


def _mini_chip(img, d, x, y, hero_id) -> int:
    p = portrait(hero_id, 30)
    nm = data.name(hero_id)
    f = body(17, "semi")
    w = 30 + 10 + tw(f, nm) + 12
    d.rounded_rectangle((x, y, x + w, y + 30), 4, fill=PANEL)
    if p:
        img.paste(p, (x, y))
    d.text((x + 40, y + 3), nm, font=f, fill=SOFT)
    return x + w


def _comp(img, d, y, label, col, rows, me=None, threats=frozenset(), hidden=False):
    """One team as five chips. Every tag that applies is shown (THREAT, YOU, DEAD, UNSURE),
    stacked under the name, so one never hides another."""
    d.text((PAD, y), label, font=disp(15, "Bold SemiCondensed"), fill=col)
    n = max(5, len(rows))
    gap = 8
    cw = (W - 2 * PAD - gap * (n - 1)) // n
    y += 22
    ch = 62
    dup = _dupes(rows)
    me_marked = False
    for i in range(n):
        r = rows[i] if i < len(rows) else {"hero": "empty"}
        x = PAD + i * (cw + gap)
        hid = r.get("hero", "unknown")
        known = hid in data.heroes()
        dead = bool(r.get("dead"))
        unsure = known and (hid in dup or (r.get("conf") is not None and r["conf"] < 0.5))
        threat = hid in threats and not unsure
        mine = me is not None and hid == me and not me_marked
        me_marked = me_marked or mine

        fill = PANEL_HI if (threat or mine) else PANEL
        d.rectangle((x, y, x + cw, y + ch), fill=fill)
        if threat:
            d.rectangle((x, y, x + cw, y + ch), outline=CORAL, width=2)
        elif mine:
            d.rectangle((x, y, x + cw, y + ch), outline=CYAN, width=2)
        d.rectangle((x, y, x + 3, y + ch), fill=col)

        ps = ch - 12
        p = portrait(hid, ps, grey=dead) if known else None
        if p:
            img.paste(p, (x + 8, y + 6))
            if unsure:  # a small amber "?" corner on the portrait
                d.polygon([(x + 8 + ps - 18, y + 6), (x + 8 + ps, y + 6), (x + 8 + ps, y + 6 + 18)], fill=AMBER)
                d.text((x + 8 + ps - 5, y + 11), "?", font=disp(12), fill=BG, anchor="mm")
        else:
            d.rectangle((x + 8, y + 6, x + 8 + ps, y + 6 + ps), fill=BG)
            d.text((x + 8 + ps // 2, y + 6 + ps // 2), "–" if hid == "empty" else "?",
                   font=disp(28), fill=MUTE, anchor="mm")

        tags = []
        if threat:
            tags.append(("THREAT", CORAL))
        if mine:
            tags.append(("YOU", CYAN))
        if dead:
            tags.append(("DEAD", MUTE))
        if unsure:
            tags.append(("UNSURE", AMBER))
        if hidden and not known and r.get("role") in ROLE_LABEL:
            tags.append((ROLE_LABEL[r["role"]], MUTE))

        tx = x + 8 + ps + 7
        room = x + cw - 4 - tx
        nm = data.name(hid) if known else ("Empty" if hid == "empty" else ("Hidden" if hidden else "Unknown"))
        name_col = (MUTE if dead else INK) if known else MUTE
        parts = nm.replace(":", "").split()
        size = 17
        lines = [nm]
        while size > 13 and tw(disp(size, "Bold Condensed"), nm) > room:
            size -= 1
        if tw(disp(size, "Bold Condensed"), nm) > room and len(parts) > 1 and len(tags) < 2:
            size, lines = 16, [parts[0], " ".join(parts[1:])]
        f = disp(size, "Bold Condensed")
        for j, ln in enumerate(lines):
            while tw(f, ln) > room and len(ln) > 2:
                ln = ln[:-1]
            d.text((tx, y + 6 + j * 16), ln, font=f, fill=name_col)

        tf = disp(13, "Bold SemiCondensed")
        tags = tags[:2]  # the portrait still shows grey (dead) and the amber corner (unsure)
        for k, (t, tc) in enumerate(reversed(tags)):
            d.text((tx, y + ch - 19 - k * 15), t, font=tf, fill=tc)


def _footer(d, result):
    y = H - 34
    d.line((PAD, y - 12, W - PAD, y - 12), fill=LINE)
    if not result:
        d.text((PAD, y), "Advice appears here within a second of holding Tab.", font=body(14), fill=MUTE)
        return
    t = result.get("timing") or {}
    total = t.get("total_ms")
    parts = [f"{k.replace('_ms', '')} {t[k]:.0f}" for k in ("hold_ms", "capture_ms", "read_ms", "advise_ms")
             if t.get(k) is not None]
    left = "  ·  ".join(parts) + " ms" if parts else ""
    if result.get("when"):
        left = f"{result['when']}    {left}"
    if result.get("bans"):
        left += "    bans: " + ", ".join(data.name(b) for b in result["bans"])
    d.text((PAD, y), left, font=body(14), fill=MUTE)
    if total is not None:
        good = total < 700
        right = f"{total:.0f} ms from Tab" if t.get("hold_ms") is not None else f"{total:.0f} ms"
        f = disp(17, "Bold SemiCondensed")
        d.text((W - PAD - tw(f, right), y - 2), right, font=f, fill=MINT if good else AMBER)
