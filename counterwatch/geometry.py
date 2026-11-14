"""Find the open Tab scoreboard and its rows in a normalised 1920x1080 frame.

Recipe from data/scoreboard_layout.md: normalise to a 1920x1080 canvas, find the board's left
edge L from the light header bar (2026 band first, then the Stadium / 2025 band), then find the
two row blocks from the saturated role strip (x L+1..L+4, left of the role icon): the ally block
runs from just under the header to the dark "VS" gap, the enemy block starts after it. Row pitch is
block height / 5, so the 2026 (65.75 px), 2025 (62 px) and Stadium (71.5 px) builds all work.
"""
from __future__ import annotations

import cv2
import numpy as np

W, H = 1920, 1080


def normalise(img: np.ndarray) -> np.ndarray:
    """Scale/crop any screenshot to the virtual 1920x1080 canvas (16:9 safe area)."""
    img = img[:, :, :3]
    h, w = img.shape[:2]
    if (w, h) == (W, H):
        return img
    interp = cv2.INTER_AREA if w > W else cv2.INTER_LINEAR
    if abs(w / h - 16 / 9) < 0.01:
        return cv2.resize(img, (W, H), interpolation=interp)
    if w / h > 16 / 9:
        nw = round(w * H / h)
        r = cv2.resize(img, (nw, H), interpolation=interp)
        x0 = (nw - W) // 2
        return r[:, x0:x0 + W]
    nh = round(h * W / w)
    r = cv2.resize(img, (W, nh), interpolation=interp)
    y0 = (nh - H) // 2
    return r[y0:y0 + H]


def find_left(gray: np.ndarray) -> int | None:
    for y0, y1 in ((165, 181), (185, 206)):
        band = gray[y0:y1, :1000].mean(axis=0)
        hits = np.nonzero(band > 170)[0]
        if len(hits) >= 300:  # the header bar is several hundred px wide
            # the header must be a solid run, not scattered bright pixels
            x = int(hits[0])
            if (band[x:x + 300] > 150).mean() > 0.9:
                return x
    return None


def find_board(img: np.ndarray) -> dict | None:
    """Return {"L", "ally_tops", "enemy_tops", "pitch", "size"} or None when no board."""
    gray = img.mean(axis=2)
    L = find_left(gray)
    if L is None or L > 700:
        return None
    col = gray[120:260, L + 200:L + 400].mean(axis=1)
    ys = np.nonzero(col > 170)[0]
    if len(ys) == 0:
        return None
    head_top = int(ys[0]) + 120
    strip = cv2.cvtColor(np.ascontiguousarray(img[:, L + 1:L + 5]), cv2.COLOR_BGR2HSV)
    ok = ((strip[:, :, 1] > 90) & (strip[:, :, 2] > 80)).mean(axis=1) > 0.7
    if head_top in range(155, 161):  # 2026 layout, measured on 30+ images
        a0, gap, e0, e1 = 188, 517, 594, 923
        if not ok[a0 + 5:a0 + 60].mean() > 0.5:
            return None
    else:
        a0 = next((y for y in range(head_top + 25, head_top + 70) if ok[y:y + 12].all()), None)
        if a0 is None:
            return None
        gap = next((y for y in range(a0 + 250, 1000) if not ok[y:y + 6].any()), None)
        if gap is None:
            return None
        e0 = next((y for y in range(gap, 1060) if ok[y:y + 12].all()), None)
        if e0 is None:
            return None
        e1 = next((y for y in range(e0 + 250, 1075) if not ok[y:y + 6].any()), None)
        if e1 is None:
            e1 = e0 + (gap - a0)
    pitch = (gap - a0) / 5.0
    if not 55 <= pitch <= 80:
        return None
    size = int(round(pitch)) - 2
    return {
        "L": L,
        "pitch": pitch,
        "size": size,
        "ally_tops": [int(round(a0 + i * pitch)) for i in range(5)],
        "enemy_tops": [int(round(e0 + i * (e1 - e0) / 5.0)) for i in range(5)],
    }


def portrait_box(board: dict, top: int) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) of a row's hero portrait."""
    x0 = board["L"] + 29
    s = board["size"]
    return x0, top, x0 + s, top + s
