"""Run counterwatch.engine.advise() on every case in a cases file and write the answers.

    python bench/run_engine.py [cases.json] [-o answers.json]

Default input is bench/dev_cases.json; default output is bench/out/<input name>.answers.json.
Each case gives role, current_hero, my_team (teammates) and enemy_team; optional "bans".
Only those inputs are passed to the engine: the coach call, reason and notes are never read.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from counterwatch import engine  # noqa: E402


def case_to_state(case: dict) -> dict:
    role = case.get("role")
    me = case.get("current_hero")
    mine = [{"hero": me or "unknown", "role": role, "dead": False, "conf": 1.0}]
    for h in case.get("my_team") or []:
        mine.append({"hero": h, "role": engine.role_of(h) or "damage", "dead": False, "conf": 1.0})
    enemy = [{"hero": h, "role": engine.role_of(h) or "damage", "dead": False, "conf": 1.0}
             for h in case.get("enemy_team") or []]
    return {"board_open": True, "my_team": mine, "enemy_team": enemy,
            "my_hero": me, "my_role": role, "ms": 0.0}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="?", default=os.path.join(ROOT, "bench", "dev_cases.json"))
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    with open(a.cases, encoding="utf-8") as f:
        raw = json.load(f)
    cases = raw["cases"] if isinstance(raw, dict) else raw
    out = a.out or os.path.join(ROOT, "bench", "out",
                                os.path.splitext(os.path.basename(a.cases))[0] + ".answers.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    answers = []
    for c in cases:
        t = time.perf_counter()
        ans = engine.advise(case_to_state(c), bans=c.get("bans") or [])
        ans["ms"] = round((time.perf_counter() - t) * 1000, 2)
        answers.append({"id": c.get("id"), "role": c.get("role"),
                        "current_hero": c.get("current_hero"), "answer": ans})
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"cases_file": os.path.relpath(a.cases, ROOT), "answers": answers}, f, indent=1)
    print(f"wrote {len(answers)} answers to {out}")


if __name__ == "__main__":
    main()
