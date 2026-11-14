"""Dev helper: every labelled scoreboard row in testdata as (tag, crop, strip, truth)."""
from __future__ import annotations

import glob
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from counterwatch.geometry import normalise, find_board  # noqa: E402


def labelled_images():
    """(set, image tag, png path, truth dict) for every labelled test image."""
    for n in sorted(os.listdir(os.path.join(ROOT, "testdata/web")), key=lambda s: int(s) if s.isdigit() else 999):
        p = os.path.join(ROOT, "testdata/web", n, "image.png")
        t = os.path.join(ROOT, "testdata/web", n, "truth.json")
        if os.path.exists(p) and os.path.exists(t):
            yield "web", f"web/{n}", p, json.load(open(t, encoding="utf-8"))
    for p in sorted(glob.glob(os.path.join(ROOT, "testdata/mine/*.png"))):
        t = p[:-4] + ".truth.json"
        if os.path.exists(t):
            yield "mine", "mine/" + os.path.basename(p)[:-4], p, json.load(open(t, encoding="utf-8"))


def imread(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
