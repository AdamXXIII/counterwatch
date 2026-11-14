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
   the respawn ring is drawn) is blanked on both sides before comparing.
4. The local player's row is the ally row drawn brighter than the rest; my_hero is that row's hero.

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
DEAD_UNSURE = 0.06      # dead portrait whose best two heroes are this close -> "unknown"


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
def _classify(crop: np.ndarray, dead: bool, role: str | None, exclude_tag: str | None):
    R = refs()
    f = _feat(crop, masked=dead)
    sims = (R.Fm if dead else R.F) @ f
    sims = sims * R.weight
    if exclude_tag is not None:
        sims = np.where(R.tags == exclude_tag, -9.0, sims)
    best = np.full(len(R.classes), -9.0, np.float32)
    np.maximum.at(best, R.lab_idx, sims)
    scores = {}
    heroes = data.heroes()
    for c, s in zip(R.classes, best):
        if s <= -9:
            continue
        if c in heroes and role:
            hr = heroes[c]["role"]
            ok = hr == role or c in _ROLE_CHANGED
            s = s + (0.03 if ok else -0.25)
        scores[c] = float(s)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    hero_ranked = [kv for kv in ranked if kv[0] in heroes]
    top, top_s = ranked[0]
    if top == "unknown" and top_s < UNKNOWN_MIN:
        top, top_s = hero_ranked[0]
    if top == "empty":
        top, top_s = hero_ranked[0]  # empty rows are decided from the role strip, not here
    if top in heroes:
        second = next((s for c, s in hero_ranked if c != top), 0.0)
        margin = top_s - second
        if dead and margin < DEAD_UNSURE:
            return "unknown", round(max(0.0, top_s / 2), 3)
        conf = max(0.0, min(1.0, 0.5 * top_s / 2 + 2.0 * margin))
        return top, round(conf, 3)
    return top, round(min(1.0, top_s / 2), 3)


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
                hero, conf = _classify(crop, dead, role, _exclude_tag)
                rows.append({"hero": hero, "role": role, "dead": dead, "conf": conf})
            rows_out[key] = rows
        # a board whose ally rows are all empty is the bugged/blank board: no reading
        if any(r["hero"] != "empty" for r in rows_out["my_team"]):
            out["board_open"] = True
            out.update(rows_out)
            out["my_row"] = _local_row(img, board)
            if out["my_row"] is not None:
                r = out["my_team"][out["my_row"]]
                if r["hero"] in data.heroes():
                    out["my_hero"] = r["hero"]
                    out["my_role"] = r["role"] or data.role(r["hero"])
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
