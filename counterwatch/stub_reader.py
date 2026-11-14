"""Stand-in scoreboard reader with the same interface as counterwatch/reader.py.

Used only while the real reader is missing or broken. It follows the recipe in
data/scoreboard_layout.md (normalise to a 1920x1080 canvas, find the board's left edge from the
light header bar, fixed 2026 row tops) and matches each 64x64 portrait against the official
portraits with a small colour template match. Good enough to drive the window; not tuned.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from . import data

ALLY_TOPS = [188, 254, 320, 386, 452]
ENEMY_TOPS = [594, 660, 727, 793, 859]
_SIZE = 32
_templates: tuple[list[str], np.ndarray] | None = None


def _load_templates():
    global _templates
    if _templates is not None:
        return _templates
    ids, mats = [], []
    for hid in data.heroes():
        p = data.portrait_path(hid)
        if not p:
            continue
        img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        if img.shape[2] == 4:  # flatten alpha on mid grey
            a = img[:, :, 3:4].astype(np.float32) / 255
            img = (img[:, :, :3] * a + 110 * (1 - a)).astype(np.uint8)
        ids.append(hid)
        mats.append(_feat(img))
    _templates = (ids, np.stack(mats))
    return _templates


def _feat(bgr: np.ndarray) -> np.ndarray:
    small = cv2.resize(bgr, (_SIZE, _SIZE), interpolation=cv2.INTER_AREA).astype(np.float32)
    lab = cv2.cvtColor(small / 255.0, cv2.COLOR_BGR2Lab).reshape(-1)
    lab -= lab.mean()
    n = np.linalg.norm(lab)
    return lab / n if n else lab


def normalise(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    if abs(w / h - 16 / 9) < 0.01:
        return img if (w, h) == (1920, 1080) else cv2.resize(img, (1920, 1080), interpolation=cv2.INTER_AREA)
    if w / h > 16 / 9:
        nw = round(w * 1080 / h)
        r = cv2.resize(img, (nw, 1080), interpolation=cv2.INTER_AREA)
        x0 = (nw - 1920) // 2
        return r[:, x0:x0 + 1920]
    nh = round(h * 1920 / w)
    r = cv2.resize(img, (1920, nh), interpolation=cv2.INTER_AREA)
    y0 = (nh - 1080) // 2
    return r[y0:y0 + 1080]


def _find_left(img: np.ndarray) -> int | None:
    band = img[165:181, :1000].mean(axis=(0, 2))
    hits = np.nonzero(band > 170)[0]
    if len(hits) < 400:  # the header bar is several hundred px wide
        return None
    return int(hits[0])


def _match(crop: np.ndarray) -> tuple[str, float]:
    ids, mats = _load_templates()
    f = _feat(crop)
    scores = mats @ f
    i = int(np.argmax(scores))
    return ids[i], float(scores[i])


def read(img_bgr: np.ndarray) -> dict:
    t0 = time.perf_counter()
    out = {"board_open": False, "my_team": [], "enemy_team": [], "my_hero": None, "my_role": None}
    img = normalise(img_bgr[:, :, :3])
    L = _find_left(img)
    if L is not None:
        out["board_open"] = True
        for key, tops in (("my_team", ALLY_TOPS), ("enemy_team", ENEMY_TOPS)):
            for top in tops:
                crop = img[top:top + 64, L + 29:L + 93]
                if crop.std() < 12:
                    out[key].append({"hero": "empty", "role": "damage", "dead": False, "conf": 0.5})
                    continue
                hid, s = _match(crop)
                ok = s > 0.35
                out[key].append({
                    "hero": hid if ok else "unknown",
                    "role": data.role(hid) or "damage",
                    "dead": False,
                    "conf": round(max(0.0, s), 3),
                })
        # own hero: big portrait at the top of the hero panel on the right
        px = 1920 - L - 435
        panel = img[160:325, px + 5:px + 170]
        if panel.size and panel.std() > 20:
            hid, s = _match(panel)
            if s > 0.35:
                out["my_hero"], out["my_role"] = hid, data.role(hid)
    out["ms"] = round((time.perf_counter() - t0) * 1000, 1)
    out["source"] = "stub"
    return out
