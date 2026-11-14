"""Build assets/scoreboard_refs.npz: per-hero portrait crops + role-icon strips from the labelled
test captures (testdata/web, testdata/mine). Each entry is one 64x64 portrait crop keyed by the
truth label of its row, plus the tag of the image it came from (used by bench/eval_reader.py to
hide an image's own crops when that image is tested). No whole screenshots are stored.

Run: python tools/reader/build_refs.py
"""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dataset import ROOT, imread, labelled_images  # noqa: E402
from counterwatch import data  # noqa: E402
from counterwatch.geometry import find_board, normalise  # noqa: E402
from counterwatch.reader import REFS, _ring_score, is_dead, row_crops  # noqa: E402


def main():
    crops, labels, tags, strips, sroles, deads = [], [], [], [], [], []
    for _set, tag, path, truth in labelled_images():
        img = normalise(imread(path))
        b = find_board(img)
        if not b:
            continue
        for key, tops in (("my_team", b["ally_tops"]), ("enemy_team", b["enemy_tops"])):
            for i, top in enumerate(tops):
                if i >= len(truth.get(key, [])):
                    continue
                t = truth[key][i]
                crop, strip = row_crops(img, b, top)
                hero, role = t["hero"], t.get("role")
                if role in ("tank", "damage", "support"):
                    strips.append(cv2.resize(strip, (28, 64), interpolation=cv2.INTER_AREA))
                    sroles.append(role)
                if hero == "empty":
                    continue
                if hero == "unknown" and _ring_score(crop) >= 0.95:
                    continue  # dead and unreadable: not a picture of anything
                if hero != "unknown" and hero not in data.heroes():
                    print("skip unknown label", tag, hero)
                    continue
                crops.append(crop)
                deads.append(bool(is_dead(crop)))
                labels.append(hero)
                tags.append(tag)
    np.savez_compressed(REFS, crops=np.stack(crops), labels=np.array(labels), tags=np.array(tags), dead=np.array(deads),
                        strips=np.stack(strips), strip_roles=np.array(sroles))
    print(f"{len(crops)} portrait crops ({len(set(labels))} classes), {len(strips)} role strips -> {REFS}")
    missing = sorted(set(data.heroes()) - set(labels))
    print(f"heroes with no scoreboard crop yet ({len(missing)}): {', '.join(missing)}")


if __name__ == "__main__":
    main()
