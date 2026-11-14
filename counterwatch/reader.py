"""Scoreboard reader: Tab board screenshot -> which heroes are on each team.

Pipeline (see data/scoreboard_layout.md for the measured geometry):

1. Normalise the frame to the virtual 1920x1080 canvas and find the board (geometry.py).
2. For every row: read the role icon on the coloured strip (shape of its white pixels against
   per-role templates; no icon = an empty "waiting for player" row), cut out the portrait, and
   look for the respawn ring that marks a dead player.
3. Identify the portrait by nearest neighbour over per-hero reference crops:
   * real scoreboard portrait crops cut from the labelled test captures
     (assets/scoreboard_refs.npz, built by tools/reader/build_refs.py), and
   * the official hero art in assets/heroes (weaker, covers heroes never seen on a board).
   Features are tint-robust: Lab colour standardised per channel (removes team tint and the
   darkening of dead portraits) plus a HOG edge descriptor. For a dead portrait the centre (where
   the respawn ring is drawn) is blanked on both sides before comparing, and the scoreboard crops
   and the official views are ranked separately and combined (see _classify_dead).
4. The local player's row is the ally row drawn brighter than the rest. my_hero is that row's hero
   when it is alive and clear; otherwise the big portrait in the hero panel (never dimmed, never
   tinted) decides, and failing that the last confident read this session (reset_session()).

Only pixels of the captured frame are used. Nothing reads game memory, files or network.
"""
from __future__ import annotations

import os
import time

import cv2
import numpy as np

from . import data
from .geometry import find_board, normalise, portrait_box

REFS = os.path.join(data.ROOT, "assets", "scoreboard_refs.npz")
ROLES = ("tank", "damage", "support")
S = 64  # portrait working size

_hog = cv2.HOGDescriptor((S, S), (16, 16), (8, 8), (8, 8), 9)
_yy, _xx = np.mgrid[:S, :S]
_R = np.hypot(_yy - (S - 1) / 2, _xx - (S - 1) / 2)
_CENTRE = _R < 20          # covered by the respawn ring on a dead portrait
_TH = np.linspace(0, 2 * np.pi, 48, endpoint=False)

UNKNOWN_MIN = 1.45   # a "?" silhouette matches its references almost perfectly (~1.9)
EMPTY_MIN = 0.65
OFFICIAL_WEIGHT = 0.90  # official art is a different style; real crops win when present
DEAD_UNSURE = 0.04      # dead portrait whose best two heroes (relative score) are this close -> "unknown"
PANEL_MIN = 0.70        # hero-panel portrait must match a reference this well (seen: 0.90-1.92 real, <=0.46 no panel)
MEMORY_S = 300.0        # how long the last confident read of your own hero is trusted


# ----------------------------------------------------------------------------- features
def _feat(crop: np.ndarray, masked: bool = False) -> np.ndarray:
    c = crop
    if masked:
        c = crop.copy()
        fill = crop[~_CENTRE].reshape(-1, 3).mean(axis=0)
        c[_CENTRE] = fill.astype(np.uint8)
    small = cv2.resize(c, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2Lab)
    if masked:
        m = cv2.resize(_CENTRE.astype(np.uint8), (16, 16), interpolation=cv2.INTER_NEAREST).astype(bool)
        keep = lab[~m]
        lab = (lab - keep.mean(axis=0)) / (keep.std(axis=0) + 1e-3)
        lab[m] = 0
    else:
        lab = (lab - lab.mean(axis=(0, 1))) / (lab.std(axis=(0, 1)) + 1e-3)
    a = lab.reshape(-1)
    a /= np.linalg.norm(a) + 1e-6
    g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    h = _hog.compute(g).reshape(-1)
    h = h - h.mean()
    h /= np.linalg.norm(h) + 1e-6
    return np.concatenate([a, h]).astype(np.float32)


def _strip_feat(strip: np.ndarray) -> tuple[np.ndarray, float]:
    """White-pixel shape of the role icon, and how much of the strip is icon."""
    hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
    white = ((hsv[:, :, 1] < 70) & (hsv[:, :, 2] > 190)).astype(np.float32)
    frac = float(white.mean())
    v = cv2.resize(white, (20, 40), interpolation=cv2.INTER_AREA).reshape(-1)
    v = v - v.mean()
    v /= np.linalg.norm(v) + 1e-6
    return v, frac


_TH64 = np.linspace(0, 2 * np.pi, 64, endpoint=False)


def _ring_edge(g: np.ndarray) -> float:
    """Fraction of directions with a sharp bright-to-dark radial edge at the ring's outer radius."""
    best = 0.0
    c = (S - 1) / 2
    for r in (16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5):
        mi = cv2.remap(g, (c + np.cos(_TH64) * (r - 1.5)).astype(np.float32)[None],
                       (c + np.sin(_TH64) * (r - 1.5)).astype(np.float32)[None], cv2.INTER_LINEAR)
        mo = cv2.remap(g, (c + np.cos(_TH64) * (r + 1.5)).astype(np.float32)[None],
                       (c + np.sin(_TH64) * (r + 1.5)).astype(np.float32)[None], cv2.INTER_LINEAR)
        best = max(best, float(((mi - mo) > 25).mean()))
    return best


def is_dead(crop: np.ndarray) -> bool:
    """A dead player's portrait is dimmed with a respawn ring (grey skull or red/white timer)."""
    s = _ring_score(crop)
    if s >= 0.95:
        return True
    if s < 0.85:
        return False
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    red = ((hsv[..., 0] < 10) | (hsv[..., 0] > 165)) & (hsv[..., 1] > 120) & (hsv[..., 2] > 130)
    return _ring_edge(np.where(red, 230.0, g).astype(np.float32)) >= 0.70


def _ring_score(crop: np.ndarray) -> float:
    """Fraction of directions where a bright/red circle of radius ~16 px stands out (respawn ring)."""
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    red = ((hsv[..., 0] < 10) | (hsv[..., 0] > 165)) & (hsv[..., 1] > 120) & (hsv[..., 2] > 130)
    g = np.where(red, 255.0, g)
    best = 0.0
    c = (S - 1) / 2
    for r in (15, 16, 17):
        rr = np.arange(r - 2, r + 3)
        xi = (c + np.outer(np.cos(_TH), rr)).round().astype(int)
        yi = (c + np.outer(np.sin(_TH), rr)).round().astype(int)
        band = g[yi, xi].max(axis=1)
        xo = (c + np.cos(_TH) * (r + 6)).round().astype(int)
        yo = (c + np.sin(_TH) * (r + 6)).round().astype(int)
        best = max(best, float(((band - g[yo, xo]) > 30).mean()))
    return best


# ----------------------------------------------------------------------------- references
class _Refs:
    def __init__(self):
        labels, tags, kinds, crops = [], [], [], []
        role_v, role_l = [], []
        if os.path.exists(REFS):
            z = np.load(REFS, allow_pickle=False)
            for c, lab, tag in zip(z["crops"], z["labels"], z["tags"]):
                crops.append(c)
                labels.append(str(lab))
                tags.append(str(tag))
                kinds.append("crop")
            for s, r in zip(z["strips"], z["strip_roles"]):
                role_v.append(_strip_feat(s)[0])
                role_l.append(str(r))
        for hid in data.heroes():
            p = data.portrait_path(hid)
            if not p:
                continue
            for c in _official_crops(p):
                crops.append(c)
                labels.append(hid)
                tags.append("official")
                kinds.append("official")
        self.labels = np.array(labels)
        self.tags = np.array(tags)
        self.weight = np.array([OFFICIAL_WEIGHT if k == "official" else 1.0 for k in kinds], np.float32)
        self.crops = np.stack(crops)
        self.F = np.stack([_feat(c) for c in crops])
        self.Fm = np.stack([_feat(c, masked=True) for c in crops])
        self.classes = sorted(set(labels))
        self.cls_idx = {c: i for i, c in enumerate(self.classes)}
        self.lab_idx = np.array([self.cls_idx[x] for x in labels])
        # role icon templates: mean shape per role
        self.role_t = {}
        for r in ROLES:
            vs = [v for v, l in zip(role_v, role_l) if l == r]
            if vs:
                m = np.mean(vs, axis=0)
                self.role_t[r] = m / (np.linalg.norm(m) + 1e-6)



def _official_crops(path: str) -> list[np.ndarray]:
    """The official art zoomed out and shifted a little (and mirrored) to look like the
    scoreboard's head-and-shoulders crop: 18 views per hero."""
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    bg = np.array([110, 60, 20], np.float32)
    if img.ndim == 3 and img.shape[2] == 4:
        a = img[:, :, 3:4].astype(np.float32) / 255
        img = (img[:, :, :3] * a + bg * (1 - a)).astype(np.uint8)
    img = cv2.resize(img[:, :, :3], (256, 256))
    n = int(256 * 1.2)
    o = (n - 256) // 2
    out = []
    for dx in (-0.08, 0.0, 0.08):
        for dy in (0.0, 0.08, 0.15):
            canvas = np.empty((n, n, 3), np.uint8)
            canvas[:] = bg.astype(np.uint8)
            oy = min(max(0, o + int(dy * n)), n - 256)
            ox = min(max(0, o + int(dx * n)), n - 256)
            canvas[oy:oy + 256, ox:ox + 256] = img
            c = cv2.resize(canvas, (S, S), interpolation=cv2.INTER_AREA)
            out += [c, np.ascontiguousarray(c[:, ::-1])]
    return out


_refs: _Refs | None = None


def refs() -> _Refs:
    global _refs
    if _refs is None:
        _refs = _Refs()
    return _refs


# ----------------------------------------------------------------------------- per row
def _role_bonus(c: str, role: str | None) -> float:
    heroes = data.heroes()
    if c not in heroes or not role:
        return 0.0
    return 0.03 if (heroes[c]["role"] == role or c in _ROLE_CHANGED) else -0.25


def _rel(best: np.ndarray, hero_mask: np.ndarray) -> np.ndarray:
    """Per-source standardised class scores: how far each hero stands out from the source's field."""
    ok = best > -9
    v = best[ok & hero_mask]
    if len(v) < 3:
        return np.full(best.shape, np.nan, np.float32)
    return np.where(ok, (best - np.median(v)) / (v.std() + 1e-6), np.nan)


def _classify(crop: np.ndarray, dead: bool, role: str | None, exclude_tag: str | None):
    """(hero id | "unknown", confidence, best raw similarity) for one 64x64 portrait."""
    R = refs()
    heroes = data.heroes()
    f = _feat(crop, masked=dead)
    raw = (R.Fm if dead else R.F) @ f
    visible = np.ones(len(raw), bool) if exclude_tag is None else (R.tags != exclude_tag)
    if dead:
        return _classify_dead(raw, visible, role)
    sims = np.where(visible, raw * R.weight, -9.0)
    best = np.full(len(R.classes), -9.0, np.float32)
    np.maximum.at(best, R.lab_idx, sims)
    scores = {}
    for c, s in zip(R.classes, best):
        if s <= -9:
            continue
        scores[c] = float(s) + _role_bonus(c, role)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    hero_ranked = [kv for kv in ranked if kv[0] in heroes]
    top_raw = float(best.max())
    top, top_s = ranked[0]
    if top == "unknown" and top_s < UNKNOWN_MIN:
        top, top_s = hero_ranked[0]
    if top == "empty":
        top, top_s = hero_ranked[0]  # empty rows are decided from the role strip, not here
    if top in heroes:
        second = next((s for c, s in hero_ranked if c != top), 0.0)
        margin = top_s - second
        conf = max(0.0, min(1.0, 0.5 * top_s / 2 + 2.0 * margin))
        return top, round(conf, 3), top_raw
    return top, round(min(1.0, top_s / 2), 3), top_raw


def _classify_dead(raw: np.ndarray, visible: np.ndarray, role: str | None):
    """A dead portrait keeps only its rim (the respawn ring covers the face), so the absolute
    similarity is low and real scoreboard crops of *any* hero beat the official art of the right
    one just by sharing the scoreboard style. Rank each source on its own instead: standardise the
    per-hero best score within the scoreboard crops and within the ring-masked official views, and
    average the two (official alone when a hero has no visible crop)."""
    R = refs()
    heroes = data.heroes()
    hero_mask = np.array([c in heroes for c in R.classes])
    off = R.tags == "official"
    bc = np.full(len(R.classes), -9.0, np.float32)
    bo = np.full(len(R.classes), -9.0, np.float32)
    np.maximum.at(bc, R.lab_idx, np.where(visible & ~off, raw, -9.0))
    np.maximum.at(bo, R.lab_idx, np.where(visible & off, raw, -9.0))
    unk = R.cls_idx.get("unknown")
    if unk is not None and bc[unk] >= UNKNOWN_MIN:
        return "unknown", round(min(1.0, float(bc[unk]) / 2), 3), float(bc[unk])
    rc, ro = _rel(bc, hero_mask), _rel(bo, hero_mask)
    z = np.where(np.isnan(rc), ro, np.where(np.isnan(ro), rc, (rc + ro) / 2))
    sc = np.where(hero_mask & ~np.isnan(z), 0.1 * np.nan_to_num(z, nan=0.0), -99.0)
    sc = sc + np.array([_role_bonus(c, role) for c in R.classes])
    o = np.argsort(-sc)
    top, margin = R.classes[o[0]], float(sc[o[0]] - sc[o[1]])
    top_raw = float(max(bc.max(), bo.max()))
    if margin < DEAD_UNSURE:
        return "unknown", round(min(0.5, 2.0 * margin + 0.2), 3), top_raw
    return top, round(max(0.0, min(1.0, 0.3 + 2.0 * margin)), 3), top_raw


# Sombra moved damage -> support on 2026-10-06; older boards still show the damage icon.
_ROLE_CHANGED = {"sombra"}


def _read_role(strip: np.ndarray) -> str | None:
    R = refs()
    v, frac = _strip_feat(strip)
    if frac < 0.03 or not R.role_t:
        return None
    sc = {r: float(t @ v) for r, t in R.role_t.items()}
    r = max(sc, key=sc.get)
    return r if sc[r] > 0.3 else None


def row_crops(img: np.ndarray, board: dict, top: int) -> tuple[np.ndarray, np.ndarray]:
    """(64x64 portrait, 28-wide role strip) for a row of a normalised frame."""
    x0, y0, x1, y1 = portrait_box(board, top)
    crop = cv2.resize(img[y0:y1, x0:x1], (S, S), interpolation=cv2.INTER_AREA)
    L = board["L"]
    strip = img[top:top + board["size"], L:L + 28]
    return crop, strip


def read(img_bgr: np.ndarray, _exclude_tag: str | None = None) -> dict:
    """Read the Tab scoreboard from a screenshot (BGR numpy array, any resolution).

    `_exclude_tag` is for evaluation only: it hides the reference crops cut from the image being
    tested, so accuracy is measured leave-one-image-out.
    """
    t0 = time.perf_counter()
    out = {"board_open": False, "my_team": [], "enemy_team": [], "my_hero": None, "my_role": None}
    if img_bgr is None or img_bgr.size == 0:
        out["ms"] = 0.0
        return out
    img = normalise(img_bgr)
    board = find_board(img)
    if board is not None:
        refs()
        rows_out = {}
        for key, tops in (("my_team", board["ally_tops"]), ("enemy_team", board["enemy_tops"])):
            rows = []
            for top in tops:
                crop, strip = row_crops(img, board, top)
                role = _read_role(strip)
                if role is None:
                    rows.append({"hero": "empty", "role": None, "dead": False, "conf": 0.9})
                    continue
                dead = is_dead(crop)
                hero, conf, _ = _classify(crop, dead, role, _exclude_tag)
                rows.append({"hero": hero, "role": role, "dead": dead, "conf": conf})
            rows_out[key] = rows
        # a board whose ally rows are all empty is the bugged/blank board: no reading
        if any(r["hero"] != "empty" for r in rows_out["my_team"]):
            out["board_open"] = True
            out.update(rows_out)
            out["my_row"] = _local_row(img, board)
            if out["my_row"] is not None:
                _read_my_hero(out, img, board, _exclude_tag)
    out["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return out


def _local_row(img: np.ndarray, board: dict) -> int | None:
    """The local player's row is drawn noticeably brighter than the other ally rows."""
    L, p = board["L"], int(board["pitch"])
    v = [float(img[t + 8:t + p - 8, L + 440:L + 860].mean()) for t in board["ally_tops"]]
    order = np.argsort(v)[::-1]
    if v[order[0]] - v[order[1]] >= 12:
        return int(order[0])
    return None


# ----------------------------------------------------------------------------- your own hero
_memory: dict = {}  # last confident read of your own hero: {"hero", "role", "t"}


def reset_session() -> None:
    """Forget the remembered own hero (call at the start of a new match or test image)."""
    _memory.clear()


def panel_crop(img: np.ndarray, board: dict) -> np.ndarray | None:
    """Your hero's big portrait in the hero panel, cut to the scoreboard portrait's framing.

    The panel (right of the board, see data/scoreboard_layout.md) shows the same art as the row
    portrait at 2.65x, and it is never dimmed or ringed when you are dead and never team-tinted.
    Measured by template matching on every 2026 board with a panel: the row-portrait framing sits at
    x = 1920-L-431, y = 155, 170 px square (2025 build: 1920-L-436, y 154, 182 px). None when there
    is no panel."""
    L, pitch = board["L"], board["pitch"]
    if L > 400:  # board centred alone: you have not picked a hero, no panel
        return None
    if 64.5 <= pitch <= 67.5:
        x, y, n = 1920 - L - 431, 155, 170
    elif 60.5 <= pitch <= 63.5:
        x, y, n = 1920 - L - 436, 154, 182
    else:
        return None
    if x < 0 or x + n > img.shape[1] or y + n > img.shape[0]:
        return None
    return cv2.resize(img[y:y + n, x:x + n], (S, S), interpolation=cv2.INTER_AREA)


def _read_my_hero(out: dict, img: np.ndarray, board: dict, exclude_tag: str | None) -> None:
    """my_hero from, in order: your row when alive and clear; the hero panel portrait; the last
    confident read this session (if your row's role still matches). A dead row never on its own
    drops my_hero to None."""
    heroes = data.heroes()
    i = out["my_row"]
    row = out["my_team"][i]
    hero, src = None, None
    if row["hero"] in heroes and not row["dead"] and row["conf"] >= 0.3:
        hero, src = row["hero"], "row"
    if hero is None:
        pc = panel_crop(img, board)
        if pc is not None:
            ph, pconf, praw = _classify(pc, False, row["role"], exclude_tag)
            if ph in heroes and praw >= PANEL_MIN and pconf >= 0.4:
                hero, src = ph, "panel"
                if row["hero"] != ph:  # the panel is the clean view of the same portrait
                    row["hero"], row["conf"] = ph, pconf
    if hero is None and row["hero"] in heroes and row["conf"] >= 0.3:
        hero, src = row["hero"], "row"
    now = time.monotonic()
    if hero is None and _memory and now - _memory["t"] < MEMORY_S \
            and (row["role"] is None or row["role"] == _memory["role"]):
        hero, src = _memory["hero"], "memory"
    if hero is None:
        return
    out["my_hero"] = hero
    out["my_role"] = row["role"] or data.role(hero)
    out["my_hero_src"] = src
    if src in ("row", "panel"):
        _memory.update(hero=hero, role=out["my_role"], t=now)
