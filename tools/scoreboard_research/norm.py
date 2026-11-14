"""Normalise a screenshot to a virtual 1920x1080 canvas (16:9 safe area).
wider than 16:9 -> scale by height, centre-crop width; narrower -> scale by width, centre-crop height."""
from PIL import Image

def to1080(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    if w / h >= 16 / 9:
        s = 1080 / h
        im = im.resize((round(w * s), 1080), Image.LANCZOS)
        off = (im.width - 1920) // 2
        return im.crop((off, 0, off + 1920, 1080)), ('h', s, off)
    s = 1920 / w
    im = im.resize((1920, round(h * s)), Image.LANCZOS)
    off = (im.height - 1080) // 2
    return im.crop((0, off, 1920, off + 1080)), ('w', s, off)
