"""Crop the 10 scoreboard rows (role strip + portrait) of each image into one sheet.
Board left edge L is found from the light header bar (y 160-185); rows at fixed y."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw
from norm import to1080
B = r'D:\counterwatch\testdata\web'
out = sys.argv[1]
ns = sys.argv[2].split(',')
ROWY = [188 + 66 * i for i in range(5)] + [594 + 66 * i for i in range(5)]
Z = 2
cw, ch = 100 * Z, 64 * Z
sheet = Image.new('RGB', (len(ns) * (cw + 10), 30 + 10 * (ch + 4)), 'black')
d = ImageDraw.Draw(sheet)
for k, n in enumerate(ns):
    im, info = to1080(os.path.join(B, n, 'image.png'))
    a = np.asarray(im).astype(int)
    hdr = a[165:180, :].mean(0).mean(1)
    L = next((x for x in range(100, 600) if hdr[x] > 170 and hdr[x + 5] > 170), None)
    if len(sys.argv) > 3:
        L = int(sys.argv[3].split(',')[k]) if sys.argv[3].split(',')[k] != '-' else L
    x0 = k * (cw + 10)
    d.text((x0 + 4, 4), '#%s L=%s' % (n, L), fill='yellow')
    if L is None:
        continue
    for r, y in enumerate(ROWY):
        c = im.crop((L, y, L + 100, y + 64)).resize((cw, ch), Image.LANCZOS)
        sheet.paste(c, (x0, 30 + r * (ch + 4)))
        d.text((x0 + cw - 18, 30 + r * (ch + 4) + 2), str(r + 1), fill='yellow')
sheet.save(out)
