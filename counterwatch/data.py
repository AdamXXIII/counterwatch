"""Shared, cached access to the data files (roster, counters, portraits)."""
from __future__ import annotations

import json
import os
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PORTRAITS = os.path.join(ROOT, "assets", "heroes")


@lru_cache(maxsize=1)
def heroes() -> dict:
    """id -> hero record from data/heroes.json."""
    with open(os.path.join(DATA, "heroes.json"), encoding="utf-8") as f:
        raw = json.load(f)
    return {h["id"]: h for h in raw["heroes"]}


@lru_cache(maxsize=1)
def counters() -> dict:
    with open(os.path.join(DATA, "counters.json"), encoding="utf-8") as f:
        return json.load(f)


def name(hero_id: str | None) -> str:
    if not hero_id:
        return ""
    h = heroes().get(hero_id)
    if h:
        return h["name"]
    return {"unknown": "Unknown", "empty": "Empty"}.get(hero_id, hero_id)


def role(hero_id: str | None) -> str | None:
    h = heroes().get(hero_id or "")
    return h["role"] if h else None


def portrait_path(hero_id: str) -> str | None:
    p = os.path.join(PORTRAITS, f"{hero_id}.png")
    return p if os.path.exists(p) else None
