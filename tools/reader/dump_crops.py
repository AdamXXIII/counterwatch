"""Dev tool: write every labelled portrait crop to a contact sheet (for eyeballing geometry)."""
import glob, json, os, sys
import cv2, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from counterwatch.geometry import normalise, find_board, portrait_box

def items():
    for n in range(1, 36):
        yield f"web{n}", os.path.join(ROOT, "testdata/web", str(n), "image.png"), os.path.join(ROOT, "testdata/web", str(n), "truth.json")
    for p in sorted(glob.glob(os.path.join(ROOT, "testdata/mine/*.png"))):
        t = p[:-4] + ".truth.json"
        yield "mine" + os.path.basename(p)[13:19], p, t

if __name__ == "__main__":
    out = sys.argv[1]
    tiles = []
    for tag, p, t in items():
        img = normalise(cv2.imread(p))
        b = find_board(img)
        row = []
        if b:
            for tops in (b["ally_tops"], b["enemy_tops"]):
                for top in tops:
                    x0, y0, x1, y1 = portrait_box(b, top)
                    c = cv2.resize(img[y0:y1, x0 - 29:x1 + 6], (99, 64))
                    row.append(c)
        else:
            row = [np.zeros((64, 99, 3), np.uint8)] * 10
        r = np.hstack(row)
        lab = np.zeros((64, 90, 3), np.uint8)
        cv2.putText(lab, tag, (2, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        tiles.append(np.hstack([lab, r]))
    cv2.imwrite(out, np.vstack(tiles))
