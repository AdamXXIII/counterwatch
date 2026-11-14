"""Stand-in counter engine with the same interface as counterwatch/engine.py.

Used only while the real engine is missing or broken. Scores each hero of the player's role
against the visible enemies with the sourced matchups (data/counters.json) and the
counterwatch.gg counter ratings, and follows the swap rules: the default is to stay, and a swap
needs a clear edge against the heroes that are actually on the enemy team.
"""
from __future__ import annotations

from . import data

SWAP_MARGIN = 9.0  # rating points a swap must win by before we say swap


def _score(cand: str, enemies: list[str]) -> tuple[float, list[tuple[float, str, str]]]:
    c = data.counters()
    m = c["matchups"].get(cand, {})
    rat = c["stat_counter_ratings"].get(cand, {})
    total, notes = 0.0, []
    for e in enemies:
        s = rat.get("counters", {}).get(e, 0.0) - rat.get("countered_by", {}).get(e, 0.0)
        if e in m.get("strong_vs", {}):
            s += 6
            notes.append((s, e, m["strong_vs"][e]))
        if e in m.get("weak_vs", {}):
            s -= 6
            notes.append((s, e, m["weak_vs"][e]))
        total += s
    return total, notes


def _clean(text: str) -> str:
    # drop source tags like "(esports.gg names Ana)" and "[2026-11-03]" for the short line
    import re
    text = re.sub(r"\s*\((?:[^()]*\bnames?\b[^()]*|Mobalytics|[^()]*\.gg[^()]*)\)", "", text)
    text = re.sub(r"\s*\[\d{4}-\d{2}-\d{2}\]", "", text)
    return text.strip().rstrip(".")


def advise(state: dict, bans: list[str] | None = None) -> dict:
    bans = set(bans or [])
    me, role = state.get("my_hero"), state.get("my_role")
    enemies = [r["hero"] for r in state.get("enemy_team", []) if r["hero"] in data.heroes()]
    allies = {r["hero"] for r in state.get("my_team", []) if r["hero"] in data.heroes()}
    base = {"action": "stay", "hero_now": me, "to": None, "alternatives": [], "how_to_play": "",
            "confidence": 0.0, "source": "stub"}
    if not state.get("board_open"):
        return {**base, "headline": "Scoreboard not seen.", "reasons": []}
    if not me or not role:
        return {**base, "headline": "Couldn't tell which hero you are on.",
                "reasons": ["Pick a hero, then hold Tab again."]}
    if len(enemies) < 2:
        return {**base, "headline": f"Too few enemies read; stay on {data.name(me)}.",
                "reasons": ["The enemy portraits were hidden or unreadable."], "confidence": 0.2}

    now_score, now_notes = _score(me, enemies)
    pool = [h for h, r in data.heroes().items()
            if r["role"] == role and h != me and h not in bans and h not in allies]
    ranked = sorted(((*_score(h, enemies), h) for h in pool), key=lambda t: -t[0])
    best_score, best_notes, best = ranked[0]
    alts = [h for _, _, h in ranked[1:3]]
    names = ", ".join(data.name(e) for e in enemies[:3])

    if best_score - now_score >= SWAP_MARGIN:
        why = sorted([n for n in best_notes if n[0] > 0], key=lambda n: -n[0])[:2]
        hurt = sorted([n for n in now_notes if n[0] < 0], key=lambda n: n[0])[:1]
        reasons = [f"{_clean(t)}." for _, _, t in why]
        reasons += [f"{data.name(e)} punishes {data.name(me)}: {_clean(t)}." for _, e, t in hurt]
        if not reasons:
            reasons = [f"{data.name(best)} rates higher than {data.name(me)} into {names}."]
        target = data.name(why[0][1]) if why else names
        return {**base, "action": "swap", "to": best, "alternatives": alts,
                "headline": f"Swap to {data.name(best)} to shut down {target}.",
                "reasons": reasons[:3],
                "how_to_play": f"Play around {target}: take the fights where your kit answers theirs.",
                "confidence": round(min(0.9, 0.45 + (best_score - now_score) / 60), 2)}

    good = sorted([n for n in now_notes if n[0] > 0], key=lambda n: -n[0])[:2]
    bad = sorted([n for n in now_notes if n[0] < 0], key=lambda n: n[0])[:1]
    reasons = [f"{_clean(t)}." for _, _, t in good]
    reasons += [f"Watch {data.name(e)}: {_clean(t)}." for _, e, t in bad]
    if not reasons:
        reasons = [f"No enemy hard-counters {data.name(me)}; staying keeps your comfort and ult."]
    reasons.append("Swaps cost more than they win unless they answer what is killing you.")
    return {**base, "alternatives": [best] + alts[:1],
            "headline": f"Stay {data.name(me)}: no swap clearly beats it into {names}.",
            "reasons": reasons[:3],
            "how_to_play": "Keep doing your job; respect the threat called out below.",
            "confidence": round(max(0.3, min(0.85, 0.6 + (now_score - best_score) / 60)), 2)}
