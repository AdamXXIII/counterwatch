"""Counter advice engine.

advise(state, bans=None) -> dict
    state is the reader dict (see counterwatch/reader.py):
      {"board_open", "my_team": [{"hero", "role", "dead", "conf"}...],
       "enemy_team": [...], "my_hero": id|None, "my_role": role|None, "ms"}
    Optional extra keys the engine understands when present:
      "killed_by": hero id that just killed the player,
      "ult_charge": 0-100 (player's ultimate charge),
      "pool": [hero ids the player is comfortable on],
      "prev_enemy_team": the enemy team at the previous read (ids or reader rows).

Returns {"action": "stay"|"swap", "hero_now", "to", "alternatives",
         "headline", "reasons", "how_to_play", "confidence"}.

How it thinks (data/counters.json, swap_rules):
  * Every candidate in the player's role is scored against EVERY visible enemy,
    not just their tank: stat counter ratings (counterwatch.gg) plus sourced
    mechanic matchups (pairs the sources disagree on count half), averaged with
    the enemy tank weighted up, plus an extra penalty for the single worst
    threat so one hard counter anywhere in their comp sinks a candidate.
  * Comp-level punishers (PUNISHERS) set a floor on how badly a matchup goes:
    Ana anti-nade/sleep on sustain tanks (Mauga, Roadhog, JQ, Ramattra),
    Bastion/Sojourn/Widowmaker/Symmetra/Sierra/Torbjorn on big hitboxes,
    divers on immobile off-angle heroes, and dive on a backline whose damage
    player is off flanking.
  * Team fit: listed synergies with the player's teammates and how well the
    candidate's archetype (dive / brawl / poke) matches what the team runs.
  * Default is to stay. A swap must beat the current hero by a clear margin
    AND turn a key matchup by a hard-counter margin (or escape a hard counter);
    soft edges never swap. The margin grows with ult nearly up, when a tank
    already wins the tank duel, and when an enemy change (optional
    state["prev_enemy_team"]) plays into the current hero. Being hard-countered
    by two enemies at once forces a swap.
  * Banned heroes and heroes already on the player's team are never offered.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = ("tank", "damage", "support")
ROLE_SLOTS = {"tank": 1, "damage": 2, "support": 2}

# --- tuning -----------------------------------------------------------------
MECH_VALUE = 5.0          # edge credited for a sourced mechanic with no stat
BOTH_BONUS = 1.5          # stat and mechanic agree
TOP_ANSWER_BONUS = 4.0    # counters.json top_answers: the first answer a table names
HARD_EDGE = 7.0           # a single matchup edge this big is a real (not soft) counter
HARD_COUNTER = 9.0        # being on the wrong end of this many points twice forces a swap
# The enemy tank matters most in 5v5, but the other four still decide fights:
# with these weights the tank is a third of the score for a tank, a fifth otherwise.
ENEMY_TANK_W = {"tank": 2.0, "damage": 1.0, "support": 1.0}
WORST_W = 0.35            # extra penalty per point the single worst threat exceeds SOFT
SOFT = 5.0

KILLER_W = 1.6            # extra weight on the hero that just killed you
SYNERGY_VALUE = 0.8
ARCHETYPE_VALUE = 1.2
POOL_BONUS = 2.0          # comfort beats paper counters
# Duel scores are a weighted AVERAGE edge over the visible enemies, so a swap
# margin is "rating points per enemy". Counter-swapping matters most on tank.
SWAP_MARGIN = {"tank": 3.0, "damage": 3.5, "support": 3.5}
HELPS_ME_MARGIN = 3.0     # an enemy swap that suits my hero: stay unless it is much worse
WIN_TANK_MARGIN = 2.5     # a tank already winning the tank duel keeps it
# Season 5 win-rate context from counterwatch.gg tier list (counters_notes.md):
# a nudge only, never enough on its own to swap.
META = {"reinhardt": 0.6, "domina": 0.6, "torbjorn": 0.6,
        "sojourn": -0.6, "mauga": -0.6, "baptiste": -0.6}
ULT_HIGH = 70             # ult at or above this: spend it before swapping

# --- punishers --------------------------------------------------------------
# Comp-level threats the pairwise tables under-count. Each rule says: when this
# enemy is visible, a candidate of this kind loses that matchup by at least
# floor * factor points (unless the tables already say the candidate wins it).
# Mechanics are from counters.json reasons (Ana > Mauga/Roadhog/JQ/Ramattra;
# Bastion/Sojourn/Symmetra/Sierra > big tanks; divers > immobile backliners).
PUNISHERS = [
    {   # anti-heal and sleep against tanks that live on self-sustain
        "enemies": {"ana": 8.0},
        "victims": {"mauga": 1.0, "roadhog": 1.0, "junkerqueen": 0.75, "ramattra": 0.6},
        "say": "{e}'s Biotic Grenade and Sleep Dart shut off {c}'s self-sustain",
    },
    {   # high sustained or burst DPS into a big hitbox
        "enemies": {"bastion": 8.0, "sojourn": 6.0, "widowmaker": 6.0, "symmetra": 5.5,
                    "sierra": 5.5, "torbjorn": 5.0, "zenyatta": 4.0},
        "victims": {"roadhog": 1.0, "mauga": 1.0, "wreckingball": 0.9, "winston": 0.8,
                    "junkerqueen": 0.8, "reinhardt": 0.7, "hazard": 0.7, "dmon": 0.7,
                    "ramattra": 0.6, "orisa": 0.6, "domina": 0.6, "sigma": 0.5},
        # hitscan picks are blocked by a barrier; Bastion shreds one
        "barrier_blocks": {"sojourn", "widowmaker"},
        "barrier": {"reinhardt", "sigma", "domina", "winston"},
        "say": "{e} melts {c}'s big hitbox",
    },
    {   # divers reaching a hero who plays alone on an off-angle or cannot escape
        "enemies": {"winston": 5.0, "dva": 4.0, "wreckingball": 4.0, "doomfist": 4.5,
                    "genji": 5.0, "tracer": 5.0, "anran": 5.0, "venture": 4.0,
                    "vendetta": 4.5, "shion": 4.0, "sombra": 4.5, "echo": 3.5},
        "victims": {"widowmaker": 1.0, "bastion": 1.0, "ashe": 0.8, "hanzo": 0.8,
                    "junkrat": 0.6, "torbjorn": 0.5, "emre": 0.5, "freja": 0.4,
                    "ana": 1.0, "zenyatta": 1.0, "illari": 0.7, "baptiste": 0.5,
                    "mercy": 0.5, "lifeweaver": 0.5},
        "say": "{e} dives {c} on an off-angle with no escape",
    },
    {   # flankers leave their own backline alone against a dive comp
        "enemies": {"winston": 3.0, "genji": 3.0, "tracer": 3.0, "anran": 3.0,
                    "doomfist": 2.5, "wreckingball": 2.5, "dva": 2.0, "venture": 2.5},
        "victims": {"tracer": 1.0, "genji": 1.0, "venture": 1.0, "anran": 0.8,
                    "shion": 1.0, "vendetta": 1.0, "reaper": 0.6, "echo": 0.6},
        "say": "{e} is on your backline while {c} is off flanking",
    },
]


@lru_cache(maxsize=1)
def _data():
    with open(os.path.join(ROOT, "data", "counters.json"), encoding="utf-8") as f:
        counters = json.load(f)
    with open(os.path.join(ROOT, "data", "heroes.json"), encoding="utf-8") as f:
        heroes = json.load(f)
    roster = {h["id"]: h for h in heroes["heroes"]}
    arche = {}
    for a, ids in counters.get("archetypes", {}).items():
        for i in ids:
            arche.setdefault(i, set()).add(a)
    return counters, roster, arche


def name(h):
    if not h:
        return "?"
    _, roster, _ = _data()
    return roster.get(h, {}).get("name", h)


def role_of(h):
    _, roster, _ = _data()
    return roster.get(h, {}).get("role")


# --- matchup maths ----------------------------------------------------------
def _stat(a, b):
    """How much a counters b, from both pages' top-5 lists (0 if unlisted)."""
    c, _, _ = _data()
    S = c["stat_counter_ratings"]
    return max(S.get(a, {}).get("counters", {}).get(b, 0.0),
               S.get(b, {}).get("countered_by", {}).get(a, 0.0))


def _mech(a, b):
    """Sourced reason why a beats b, or None."""
    c, _, _ = _data()
    M = c["matchups"]
    return (M.get(a, {}).get("strong_vs", {}).get(b)
            or M.get(b, {}).get("weak_vs", {}).get(a))


def _top_answer(a, b):
    c, _, _ = _data()
    return (c.get("top_answers", {}).get(b) or {}).get(a)


def _side(a, b):
    s = _stat(a, b)
    m = _mech(a, b)
    v = max(s, MECH_VALUE if m else 0.0)
    if s and m:
        v += BOTH_BONUS
    if _top_answer(a, b):
        v += TOP_ANSWER_BONUS
    return v


@lru_cache(maxsize=1)
def _low_conf():
    c, _, _ = _data()
    return {frozenset(p) for p in c.get("low_confidence_pairs", {}).get("pairs", [])}


@lru_cache(maxsize=None)
def edge(a, b):
    """Positive: a wins the matchup against b (pairwise tables only).
    Pairs where the sources disagree (low_confidence_pairs) count half."""
    v = _side(a, b) - _side(b, a)
    if frozenset((a, b)) in _low_conf():
        v *= 0.5
    return v


def punisher(c, e):
    """(floor, reason) when enemy e is known to punish candidate c, else (0, None)."""
    best = (0.0, None)
    for r in PUNISHERS:
        base = r["enemies"].get(e)
        f = r["victims"].get(c)
        if not base or not f:
            continue
        if c in r.get("barrier", ()) and e in r.get("barrier_blocks", ()):
            f *= 0.4
        v = base * f
        if v > best[0]:
            best = (v, r["say"].format(e=name(e), c=name(c)))
    return best


def comp_edge(c, e):
    """edge() plus comp-level punishers: what the matchup is worth in a real fight."""
    v = edge(c, e)
    if v >= SOFT:       # the tables say c wins it outright: trust them
        return v
    floor, _ = punisher(c, e)
    return min(v, -floor) if floor else v


def _enemy_weights(enemies, killed_by, role):
    w = {}
    for e in enemies:
        x = ENEMY_TANK_W.get(role, 1.0) if role_of(e) == "tank" else 1.0
        if killed_by and e == killed_by:
            x *= KILLER_W
        w[e] = w.get(e, 0.0) + x
    return w


def _team_fit(c, mates):
    counters, _, arche = _data()
    syn = counters.get("synergies", {})
    s = 0.0
    partners = []
    for m in mates:
        if m in syn.get(c, []) or c in syn.get(m, []):
            s += SYNERGY_VALUE
            partners.append(m)
    if mates:
        counts = {}
        for m in mates:
            for a in arche.get(m, ()):
                counts[a] = counts.get(a, 0) + 1
        mine = arche.get(c, set())
        if mine and counts:
            share = max(counts.get(a, 0) for a in mine) / len(mates)
            s += ARCHETYPE_VALUE * share
    return s, partners


def _score(c, weights, mates, pool):
    """Score candidate c against EVERY visible enemy, not just their tank."""
    tw = sum(weights.values())
    per = {e: comp_edge(c, e) for e in weights}
    duel = sum(w * per[e] for e, w in weights.items()) / tw if tw else 0.0
    worst = max([-v for v in per.values()] + [0.0])
    duel -= WORST_W * max(0.0, worst - SOFT)
    best_win = max([v for v in per.values()] + [0.0])
    fit, partners = _team_fit(c, mates)
    comfort = POOL_BONUS if pool and c in pool else 0.0
    return {"hero": c, "duel": duel, "fit": fit, "partners": partners, "per": per,
            "worst": worst, "best_win": best_win,
            "total": duel + fit + comfort + META.get(c, 0.0)}


# --- state helpers ----------------------------------------------------------
def _ids(team):
    return [p.get("hero") for p in team or []
            if p.get("hero") and p.get("hero") not in ("unknown", "empty")
            and role_of(p.get("hero"))]


def _infer_role(state):
    if state.get("my_role") in ROLES:
        return state["my_role"]
    if state.get("my_hero") and role_of(state["my_hero"]):
        return role_of(state["my_hero"])
    # the role with a free slot on my team
    counts = {r: 0 for r in ROLES}
    for h in _ids(state.get("my_team")):
        counts[role_of(h)] += 1
    for r in ("tank", "support", "damage"):
        if counts[r] < ROLE_SLOTS[r]:
            return r
    return "damage"


def _teammates(state, me):
    mates = list(_ids(state.get("my_team")))
    if me in mates:
        mates.remove(me)
    return mates


# --- words ------------------------------------------------------------------
def _clause(text, limit=80):
    t = re.sub(r"\s*\[\d{4}(?:-\d{2}){0,2}\]", "", text)
    t = t.split(";")[0].split(" (")[0].strip().rstrip(".")
    if len(t) > limit:
        cut = t[:limit].rsplit(" ", 1)[0]
        t = cut.rstrip(",:")
    return t


def _best_target(c, weights):
    """Enemy hero c beats hardest that has a reason we can say."""
    best = None
    for e, w in weights.items():
        m = _mech(c, e)
        if not m:
            continue
        v = w * comp_edge(c, e)
        if v > 0 and (best is None or v > best[0]):
            best = (v, e, m)
    return best


def _threats(c, weights):
    """Enemies that beat c in a real fight, worst first: (weighted, enemy, reason)."""
    out = []
    for e, w in weights.items():
        v = comp_edge(c, e)
        if v < 0:
            floor, why = punisher(c, e)
            m = _mech(e, c)
            # say the comp-level reason when it is what makes this matchup bad
            reason = why if why and (not m or floor > -edge(c, e)) else m
            out.append((w * v, e, reason))
    out.sort(key=lambda t: t[0])
    return out


TIPS = {
    "ana": "Hold high ground behind your tank; save Sleep for divers and nade their tank's sustain.",
    "anran": "Flank wide, Inferno Rush onto isolated backliners, keep Dancing Blaze to escape.",
    "ashe": "Hold a long sightline with cover, Coach Gun away from divers, keep B.O.B. for a fight swing.",
    "baptiste": "Stay at mid range, pre-place Immortality Field for their burst and poke their tank.",
    "bastion": "Set up behind your tank's cover and turret only when the divers are on cooldown.",
    "brigitte": "Stick to your backline, whip divers off your supports and keep Inspire rolling.",
    "cassidy": "Hold an off-angle at mid range and save Flashbang for whoever dives you.",
    "dmon": "Walk in behind Power Barrier, close with Propulsors and saber their squishies.",
    "doctrine": "Fight with your brawlers at mid range and drop Deliverance on their tank push.",
    "domina": "Hold the choke, poke from behind Barrier Array and Repulse divers off you.",
    "doomfist": "Punch in on isolated backliners, block poke with Power Block and get out on Slam.",
    "dva": "Matrix their key projectiles, boost onto their backline and peel your supports.",
    "echo": "Fly off-angles, Sticky Bomb low targets and finish them with Focusing Beam.",
    "emre": "Take a mid-range angle with your tank and burst whoever steps out of cover.",
    "freja": "Poke from range, Updraft to high ground and finish low targets with Take Aim.",
    "genji": "Wait for cooldowns, dash in on a low backliner and Deflect only key shots.",
    "hanzo": "Hold an angle off your tank, Sonic their flankers and one-shot whoever peeks.",
    "hazard": "Leap in with your team, Spike Guard their poke and wall off their backline.",
    "illari": "Pylon behind cover, poke from range and Outburst away from divers.",
    "jetpackcat": "Fly with your divers, Lifeline your tank out of trouble, stay off their hitscan.",
    "junkerqueen": "Brawl close with your team, wound their tank and Shout before you go in.",
    "junkrat": "Spam the choke from cover, trap the flank route and mine away from divers.",
    "juno": "Glide with your team, torpedo the fight on engage and stay out of hitscan lines.",
    "kiriko": "Stay near your tank, Suzu the key cleanse and teleport out when dove.",
    "lifeweaver": "Play safe angles, Life Grip whoever is caught and Platform your team to high ground.",
    "lucio": "Speed your team in together, boop their frontline and keep wall-riding.",
    "mauga": "Push into their frontline, keep both guns on them and Overdrive in the brawl.",
    "mei": "Hold the corner with your tank, wall off their backline and Cryo when focused.",
    "mercy": "Pocket your best damage player behind cover and Guardian Angel out of danger.",
    "mizuki": "Stay with your brawlers, Kasa the frontline and chain whoever dives in.",
    "moira": "Fight with your team at close range, drain divers and Fade out when focused.",
    "orisa": "Hold the frontline, Fortify through their burst and Javelin anyone who commits.",
    "pharah": "Rocket from cover above, stay out of hitscan sightlines and pair with your pocket.",
    "ramattra": "Poke in Omnic form, then go Nemesis when they commit and punch through shields.",
    "reaper": "Take close corners, Shadow Step behind their tank and shotgun the frontline.",
    "reinhardt": "Walk them back with Barrier up, swing when they close and save Charge for a pin.",
    "roadhog": "Take cover angles, hook whoever is isolated and Compactor their burst.",
    "shion": "Ride Joyride onto flanks, burst a backliner and get out before they turn.",
    "sierra": "Mark targets from mid range, drop the Anchor Drone on cover and finish the tagged.",
    "sigma": "Barrier their poke, Grasp their key projectile and Accretion the peekers.",
    "sojourn": "Slide to off-angles, farm charge on their tank and railgun the squishies.",
    "soldier76": "Hold mid range with your team, Biotic Field in cover and sprint to off-angles.",
    "sombra": "Stay stealthed on flanks, Cyberspace their tank in the brawl and EMP on engage.",
    "symmetra": "Turret the flank route, beam into shields and teleport your team in.",
    "torbjorn": "Set the turret behind cover near the point and Overload when they dive.",
    "tracer": "Harass their backline from flanks, Recall out and pulse on the engage.",
    "vendetta": "Wait for their cooldowns, slice in on a low backliner and block the counter-burst.",
    "venture": "Burrow under their frontline, surface on a backliner and drill out.",
    "widowmaker": "Take a covered perch, reposition after each pick and grapple away from divers.",
    "winston": "Jump their backline with your divers, bubble to split them and leave on cooldown.",
    "wreckingball": "Roll in on isolated backliners, Piledriver groups and grapple out early.",
    "wuyang": "Heal from behind your tank and bend orbs onto whoever pokes from cover.",
    "zarya": "Bubble your tank or yourself on their burst and charge up before you fight.",
    "zenyatta": "Discord their tank from long range, kick off divers and save Trans for their ult.",
}


def _how(hero, focus):
    tip = TIPS.get(hero, "Play with your team and take good cover.")
    if focus:
        return f"{tip} Main target: their {name(focus)}."
    return tip


def _swap_headline(to, weights, fresh):
    verb = "Go" if fresh else "Swap to"
    beats = [e for e, w in sorted(weights.items(), key=lambda kv: -kv[1] * comp_edge(to, kv[0]))
             if comp_edge(to, e) > 0][:2]
    if not beats:
        return f"{verb} {name(to)}: best overall fit into this comp."
    m = _mech(to, beats[0])
    cl = _clause(m, 999) if m else ""
    if cl and len(cl) <= 58:
        return f"{verb} {name(to)} into their {name(beats[0])}: {cl}."
    return f"{verb} {name(to)}; it beats their {' and '.join(name(e) for e in beats)}."


# --- main -------------------------------------------------------------------
SAFE_SAY = [
    "{c} has no self-sustain for {e}'s anti-nade to shut off",
    "{c} gives their {e} a smaller or shielded target",
    "{c} can fight back when {e} dives",
    "{c} stays with your backline against their {e}",
]


def _safe_reason(c, enemies):
    """A visible punisher that would hurt other picks in the role but not c."""
    _, roster, _ = _data()
    role = role_of(c)
    for i, r in enumerate(PUNISHERS):
        for e in enemies:
            if e not in r["enemies"] or c in r["victims"]:
                continue
            if any(roster.get(v, {}).get("role") == role for v in r["victims"]):
                return SAFE_SAY[i].format(c=name(c), e=name(e)) + "."
    return None


def _arrivals(state, enemies):
    """Enemy heroes new since the last board read (state["prev_enemy_team"], optional)."""
    prev = state.get("prev_enemy_team")
    if not prev:
        return []
    prev_ids = {p.get("hero") if isinstance(p, dict) else p for p in prev}
    return [e for e in enemies if e not in prev_ids]


def advise(state, bans=None):
    counters, roster, _ = _data()
    bans = {b for b in (bans or []) if b}
    role = _infer_role(state)
    me = state.get("my_hero")
    if me in ("unknown", "empty") or (me and role_of(me) is None):
        me = None
    mates = _teammates(state, me)
    enemies = _ids(state.get("enemy_team"))
    killed_by = state.get("killed_by")
    pool = set(state.get("pool") or [])
    ult = state.get("ult_charge")
    weights = _enemy_weights(enemies, killed_by, role)

    cands = [h for h, r in roster.items()
             if r["role"] == role and h not in bans and (h not in mates or h == me)]
    scored = sorted((_score(c, weights, mates, pool) for c in cands),
                    key=lambda s: -s["total"])
    by = {s["hero"]: s for s in scored}
    alt_pool = [s for s in scored if s["hero"] != me]
    best = alt_pool[0] if alt_pool else None

    info = len(enemies)
    helps = []          # enemy arrivals that suit my current hero
    soft_only = False
    # --- decide ---
    if me is None and info == 0:
        action, to, gain, margin = "stay", None, 0.0, 0.0
    elif me is None:
        action = "swap"
        to = best["hero"] if best else None
        gain = best["total"] if best else 0.0
        margin = 0.0
    else:
        cur = by.get(me) or _score(me, weights, mates, pool)
        by.setdefault(me, cur)
        gain = (best["total"] - cur["total"]) if best else 0.0
        margin = SWAP_MARGIN.get(role, 4.0)
        if ult is not None and ult >= ULT_HIGH:
            margin += 3.0
        if role == "tank" and any(role_of(e) == "tank" and cur["per"][e] >= SOFT
                                  for e in weights):
            margin += WIN_TANK_MARGIN
        arr = _arrivals(state, enemies)
        if arr and all(cur["per"][e] >= 0 for e in arr):
            helps = [e for e in arr if cur["per"][e] > 0]
            if helps:
                margin += HELPS_ME_MARGIN
        # A swap needs a real (not soft) reason: it turns a key matchup (their
        # tank for a tank, the hero killing you, anyone for damage/support)
        # by a hard-counter margin, or it escapes a hero hard-countering you.
        key = [e for e in weights
               if role != "tank" or role_of(e) == "tank" or e == killed_by]
        def lift(e):
            return best["per"][e] - cur["per"][e] if best else 0.0
        real = bool(best) and (
            any(lift(e) >= HARD_EDGE for e in key)
            or any(cur["per"][e] <= -HARD_COUNTER and lift(e) >= HARD_EDGE for e in weights))
        hard = [e for e in weights if cur["per"][e] <= -HARD_COUNTER]
        forced = len(hard) >= 2 and gain > 0 and not helps
        if me in bans:
            action = "swap"
        elif info == 0:
            action = "stay"
        elif forced or (gain >= margin and real):
            action = "swap"
        else:
            action = "stay"
            soft_only = gain >= margin and not real
        to = best["hero"] if action == "swap" and best else None

    alts = [s["hero"] for s in alt_pool if s["hero"] != to][:3]
    if action == "stay" and me:
        # alternatives = the heroes to go to if it keeps going wrong
        alts = [s["hero"] for s in alt_pool if s["total"] > by[me]["total"]][:3] or alts

    pick = to if action == "swap" else me
    tgt = _best_target(pick, weights) if pick else None
    threats = _threats(pick, weights) if pick else []

    # --- words ---
    reasons = []
    if action == "swap" and to:
        sc = by[to]
        wins = []
        for e, w in sorted(weights.items(), key=lambda kv: -kv[1] * comp_edge(to, kv[0])):
            m = _mech(to, e)
            if m and comp_edge(to, e) > 0:
                wins.append(f"{name(to)} into {name(e)}: {_clause(m, 110)}.")
        reasons.extend(wins[:2])
        if me:
            bad = _threats(me, weights)
            if bad and bad[0][2] and len(reasons) < 3:
                reasons.insert(min(1, len(reasons)),
                               f"{name(me)} loses to {name(bad[0][1])}: {_clause(bad[0][2], 100)}.")
        safe = _safe_reason(to, enemies)
        if safe and len(reasons) < 3:
            reasons.append(safe)
        if len(reasons) < 3 and sc["partners"]:
            reasons.append(f"Fits your team: pairs with {', '.join(name(p) for p in sc['partners'][:2])}.")
        if len(reasons) < 2 and sc["worst"] < HARD_EDGE:
            reasons.append(f"Nothing else they have hard-counters {name(to)}."
                           if wins and len(enemies) > 1
                           else f"No visible enemy hard-counters {name(to)}.")
        if len(reasons) < 2:
            reasons.append(f"{name(to)} has the best overall matchup into {', '.join(name(e) for e in enemies) or 'their comp'}.")
        head = _swap_headline(to, weights, fresh=me is None)
        me_dead = any(p.get("dead") for p in state.get("my_team") or []
                      if me and p.get("hero") == me)
        if me and not me_dead:
            how = "On your next death. " + _how(to, tgt[1] if tgt else None)
        else:
            how = _how(to, tgt[1] if tgt else None)
    else:
        if me is None:
            head = "Can't read the board yet; hold Tab again."
            reasons = ["Neither your hero nor the enemy comp was read from the scoreboard."]
            how = "Hold Tab for a moment so the board is fully visible."
        elif info == 0:
            head = f"Stay {name(me)}; their comp isn't visible yet."
            reasons = ["No enemy heroes read yet, and an early counter gives them a free re-pick.",
                       "Check Tab again once their whole team is on the board."]
            how = _how(me, None)
        else:
            if helps:
                h = helps[0]
                m = _mech(me, h)
                reasons.append(f"Their swap to {name(h)} suits you"
                               + (f": {_clause(m, 100)}." if m else "."))
            if tgt and not (helps and tgt[1] == helps[0]):
                reasons.append(f"{name(me)} into {name(tgt[1])}: {_clause(tgt[2], 110)}.")
            if best and gain > 0:
                why = "only a soft counter" if soft_only or gain < margin else "a small edge"
                reasons.append(f"{name(best['hero'])} is {why} here; not worth losing ult charge on a swap.")
            else:
                reasons.append(f"Nothing in your role beats this comp better than {name(me)}.")
            if threats and threats[0][2]:
                reasons.append(f"Watch the {name(threats[0][1])}: {_clause(threats[0][2], 100)}.")
            elif threats:
                reasons.append(f"Their {name(threats[0][1])} wins that matchup on the stats; fight from cover away from them.")
            elif not tgt:
                et = [e for e in enemies if role_of(e) == "tank"]
                vs = f"their {name(et[0])}" if et else "their comp"
                reasons.append(f"{name(me)} is even into {vs}, and nobody on their team hard-counters you.")
            if helps:
                head = f"Stay {name(me)}: their {name(helps[0])} swap plays into you."
            elif tgt and (not threats or -threats[0][0] < tgt[0]):
                head = f"Stay {name(me)}: you win the {name(tgt[1])} matchup."
            elif threats:
                head = f"Stay {name(me)}; nothing beats their {name(threats[0][1])} by enough to swap."
            else:
                head = f"Stay {name(me)}; no matchup here is worth a swap."
            how = _how(me, tgt[1] if tgt else (threats[0][1] if threats else None))

    # --- confidence ---
    if action == "swap" and me is not None:
        conf = 0.45 + 0.35 * min(1.0, max(0.0, gain - margin) / 12.0 + 0.3)
    elif action == "swap":
        second = alt_pool[1]["total"] if len(alt_pool) > 1 else 0.0
        conf = 0.4 + 0.4 * min(1.0, max(0.0, best["total"] - second) / 6.0) if best else 0.2
    else:
        conf = 0.5 + 0.35 * min(1.0, max(0.0, margin - gain) / max(margin, 1.0))
    conf *= 0.6 + 0.4 * min(1.0, info / 3.0) if info else 0.5
    conf = round(max(0.05, min(0.95, conf)), 2)

    return {
        "action": action,
        "hero_now": me,
        "to": to,
        "alternatives": alts,
        "headline": head,
        "reasons": reasons[:3],
        "how_to_play": how,
        "confidence": conf,
    }
