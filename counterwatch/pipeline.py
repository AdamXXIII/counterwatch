"""Reader + engine wiring. Uses counterwatch/reader.py and counterwatch/engine.py when they
exist and import cleanly; otherwise the stubs with the same interface. Re-checks on every run,
so the real modules are picked up as soon as they land (no restart needed)."""
from __future__ import annotations

import importlib
import logging
import os
import time
import traceback

from . import stub_engine, stub_reader

log = logging.getLogger("counterwatch")
HERE = os.path.dirname(os.path.abspath(__file__))

_cache: dict[str, tuple[float, object]] = {}


def _module(name: str, attr: str, stub):
    """Return (callable, 'real'|'stub'). Reloads the real module when its file changes."""
    path = os.path.join(HERE, f"{name}.py")
    if not os.path.exists(path):
        return getattr(stub, attr), "stub"
    mtime = os.path.getmtime(path)
    cached = _cache.get(name)
    if cached and cached[0] == mtime:
        mod = cached[1]
    else:
        try:
            mod = importlib.import_module(f"counterwatch.{name}")
            if cached:
                mod = importlib.reload(mod)
            _cache[name] = (mtime, mod)
            log.info("loaded real %s.py", name)
        except Exception:
            log.error("could not import %s.py, using stub:\n%s", name, traceback.format_exc())
            _cache[name] = (mtime, None)
            mod = None
    fn = getattr(mod, attr, None) if mod else None
    return (fn, "real") if callable(fn) else (getattr(stub, attr), "stub")


def run(img_bgr, bans: list[str] | None = None) -> dict:
    """Full pipeline on one BGR frame. Returns {"state", "advice", "timing", "sources", "error"}."""
    read, rsrc = _module("reader", "read", stub_reader)
    advise, esrc = _module("engine", "advise", stub_engine)
    out = {"state": None, "advice": None, "error": None,
           "sources": {"reader": rsrc, "engine": esrc}, "timing": {}, "bans": list(bans or [])}
    t0 = time.perf_counter()
    try:
        out["state"] = read(img_bgr)
    except Exception as e:
        log.error("reader failed:\n%s", traceback.format_exc())
        out["error"] = f"Reader error: {e}"
        return out
    t1 = time.perf_counter()
    try:
        out["advice"] = advise(out["state"], bans=bans or [])
    except Exception as e:
        log.error("engine failed:\n%s", traceback.format_exc())
        out["error"] = f"Engine error: {e}"
    t2 = time.perf_counter()
    out["timing"] = {"read_ms": (t1 - t0) * 1000, "advise_ms": (t2 - t1) * 1000}
    return out
