"""Collect real Tab scoreboard screenshots while you play.

Run it, play normally, and hold Tab now and then. Each time Tab has been held
for a moment while Overwatch is the front window, the main screen is saved to
testdata/mine/. At most one shot every 15 seconds. Ctrl+C to stop.

It only reads whether the Tab key is down (GetAsyncKeyState) and copies the
screen, the same way a screenshot tool does. It never touches the game.
"""
import ctypes
import time
from datetime import datetime
from pathlib import Path

import mss
import mss.tools

OUT = Path(__file__).resolve().parent.parent / "testdata" / "mine"
OUT.mkdir(parents=True, exist_ok=True)

user32 = ctypes.windll.user32
VK_TAB = 0x09
HOLD_S = 0.35
GAP_S = 15


def overwatch_in_front() -> bool:
    hwnd = user32.GetForegroundWindow()
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    return "overwatch" in buf.value.lower()


def tab_down() -> bool:
    return bool(user32.GetAsyncKeyState(VK_TAB) & 0x8000)


def main() -> None:
    print(f"Saving Tab screens to {OUT}. Hold Tab in a match. Ctrl+C to stop.")
    held_since = None
    last = 0.0
    with mss.mss() as sct:
        mon = sct.monitors[1]
        while True:
            if tab_down() and overwatch_in_front():
                held_since = held_since or time.monotonic()
                if time.monotonic() - held_since >= HOLD_S and time.monotonic() - last >= GAP_S:
                    shot = sct.grab(mon)
                    name = OUT / f"tab-{datetime.now():%Y%m%d-%H%M%S}.png"
                    mss.tools.to_png(shot.rgb, shot.size, output=str(name))
                    last = time.monotonic()
                    print("saved", name.name, f"({len(list(OUT.glob('*.png')))} so far)")
            else:
                held_since = None
            time.sleep(0.02)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
