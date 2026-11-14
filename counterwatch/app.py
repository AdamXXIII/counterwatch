"""Counterwatch app: hold Tab in Overwatch, get the counter call on your second screen.

    python -m counterwatch                 run the overlay-free advice window
    python -m counterwatch --image x.png   run the whole pipeline on a screenshot and save a PNG
                                           of the window to bench/app_shots/ (no game needed)

Match state comes only from a screen capture (mss). Tab is read passively with
GetAsyncKeyState; nothing is injected into or drawn over the game.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import logging
import os
import queue
import re
import sys
import threading
import time
from datetime import datetime

import numpy as np

from . import data, pipeline, view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SETTINGS = os.path.join(HERE, "settings.json")
LOGS = os.path.join(ROOT, "logs")
SHOTS = os.path.join(ROOT, "bench", "app_shots")
LAST = os.path.join(ROOT, "captures", "last.png")

HOLD_S = 0.15        # Tab must be held this long before we grab the screen
POLL_S = 0.012
VK_TAB = 0x09
GAME_TITLE = "Overwatch"

log = logging.getLogger("counterwatch")


# ---------------------------------------------------------------- setup helpers
def setup_logging():
    os.makedirs(LOGS, exist_ok=True)
    log.setLevel(logging.INFO)
    if not log.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh = logging.FileHandler(os.path.join(LOGS, "counterwatch.log"), encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        log.addHandler(fh)
        log.addHandler(sh)


def dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def load_settings() -> dict:
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(s: dict):
    try:
        tmp = SETTINGS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=1)
        os.replace(tmp, SETTINGS)
    except Exception as e:
        log.warning("could not save settings: %s", e)


def parse_bans(text: str) -> list[str]:
    """'widow, Ana; hog' -> ['widowmaker', 'ana', 'roadhog'] (best effort, unknown words dropped)."""
    def key(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())
    alias = {"widow": "widowmaker", "hog": "roadhog", "ball": "wreckingball", "soldier": "soldier76",
             "jq": "junkerqueen", "torb": "torbjorn", "rein": "reinhardt", "lw": "lifeweaver",
             "bap": "baptiste", "zen": "zenyatta", "sym": "symmetra", "brig": "brigitte",
             "mccree": "cassidy", "dva": "dva"}
    table = {}
    for hid, h in data.heroes().items():
        table[key(hid)] = hid
        table[key(h["name"])] = hid
    out = []
    for word in re.split(r"[,;/\n]+", text):
        k = key(word)
        if not k:
            continue
        hid = table.get(k) or alias.get(k)
        if not hid:
            hid = next((v for kk, v in table.items() if kk.startswith(k) and len(k) >= 3), None)
        if hid and hid not in out:
            out.append(hid)
    return out


def imread(path: str) -> np.ndarray:
    import cv2
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"Could not read image: {path}")
    return img


def log_timing(kind: str, result: dict):
    t = result.get("timing", {})
    adv = result.get("advice") or {}
    call = f"swap->{adv.get('to')}" if adv.get("action") == "swap" else adv.get("action", "-")
    log.info("%s total=%.0fms hold=%s capture=%s read=%.0f advise=%.0f draw=%.0f | %s | reader=%s engine=%s",
             kind, t.get("total_ms", 0), _f(t.get("hold_ms")), _f(t.get("capture_ms")),
             t.get("read_ms", 0), t.get("advise_ms", 0), t.get("draw_ms", 0), call,
             result.get("sources", {}).get("reader"), result.get("sources", {}).get("engine"))


def _f(v):
    return "-" if v is None else f"{v:.0f}"


# ---------------------------------------------------------------- Win32 polling (passive)
class Win32:
    def __init__(self):
        self.u32 = ctypes.windll.user32
        self.buf = ctypes.create_unicode_buffer(256)

    def game_in_front(self) -> bool:
        hwnd = self.u32.GetForegroundWindow()
        if not hwnd:
            return False
        self.u32.GetWindowTextW(hwnd, self.buf, 256)
        return self.buf.value.strip() == GAME_TITLE

    def tab_down(self) -> bool:
        return bool(self.u32.GetAsyncKeyState(VK_TAB) & 0x8000)


class Watcher(threading.Thread):
    """Polls Tab + foreground window; after HOLD_S of holding, grabs the primary screen and runs
    the pipeline. Results go to `out` for the tk thread."""

    def __init__(self, out: queue.Queue, get_bans):
        super().__init__(daemon=True)
        self.out, self.get_bans = out, get_bans
        self.stop = threading.Event()
        self.game_front = False

    def run(self):
        import mss
        w32 = Win32()
        sct = mss.mss()
        mon = next((m for m in sct.monitors[1:] if m["left"] == 0 and m["top"] == 0), sct.monitors[1])
        down_at, fired = None, False
        last_front_check = 0.0
        while not self.stop.is_set():
            now = time.perf_counter()
            if now - last_front_check > 0.25 or down_at is not None:
                front = w32.game_in_front()
                if front != self.game_front:
                    self.game_front = front
                    self.out.put(("front", front))
                last_front_check = now
            if self.game_front and w32.tab_down():
                if down_at is None:
                    down_at, fired = now, False
                elif not fired and now - down_at >= HOLD_S:
                    fired = True
                    self._capture(sct, mon, down_at)
            else:
                down_at = None
            time.sleep(POLL_S)

    def _capture(self, sct, mon, down_at):
        t0 = time.perf_counter()
        try:
            shot = sct.grab(mon)
            frame = np.ascontiguousarray(np.asarray(shot)[:, :, :3])
        except Exception as e:
            log.error("capture failed: %s", e)
            self.out.put(("result", {"error": f"Screen capture failed: {e}", "timing": {}}, None))
            return
        t1 = time.perf_counter()
        result = pipeline.run(frame, self.get_bans())
        result["timing"]["hold_ms"] = (t0 - down_at) * 1000
        result["timing"]["capture_ms"] = (t1 - t0) * 1000
        result["t_down"] = down_at
        result["when"] = datetime.now().strftime("%H:%M:%S")
        self.out.put(("result", result, frame))


# ---------------------------------------------------------------- the window
class App:
    FOOT = 52

    def __init__(self, settings: dict):
        import tkinter as tk
        from PIL import ImageTk
        self.tk, self.ImageTk = tk, ImageTk
        self.settings = settings
        self.q: queue.Queue = queue.Queue()
        self.last_frame = None
        self.last_result = None
        self.mode = "idle"

        root = self.root = tk.Tk()
        root.title("Counterwatch")
        root.configure(bg=_hex(view.BG))
        root.resizable(False, False)
        root.geometry(self._initial_geometry())
        root.attributes("-topmost", bool(settings.get("topmost", False)))
        self._icon()
        self._dark_title_bar()

        self.canvas = tk.Label(root, bd=0, bg=_hex(view.BG))
        self.canvas.pack(side="top")
        self._footer()
        self.show(None)

        root.bind("<Configure>", self._moved)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<F5>", lambda e: self.replay())

        self.watcher = Watcher(self.q, lambda: list(self.bans))
        self.watcher.start()
        threading.Thread(target=self._warm, daemon=True).start()
        self._load_last()
        root.after(30, self._pump)

    # -- layout pieces
    def _initial_geometry(self) -> str:
        w, h = view.W, view.H + self.FOOT
        x, y = self.settings.get("x"), self.settings.get("y")
        mons = _monitors()
        if x is not None and y is not None and any(
                m["left"] <= x + 40 < m["left"] + m["width"] and m["top"] <= y + 20 < m["top"] + m["height"]
                for m in mons):
            return f"{w}x{h}+{x}+{y}"
        # default: centre-right of a second monitor if there is one, else top-left of the primary
        second = next((m for m in mons if not (m["left"] == 0 and m["top"] == 0)), None)
        if second:
            x = second["left"] + (second["width"] - w) // 2
            y = second["top"] + max(0, (second["height"] - h) // 2 - 20)
        else:
            x, y = 40, 40
        return f"{w}x{h}+{x}+{y}"

    def _icon(self):
        try:
            from PIL import Image, ImageDraw
            ic = Image.new("RGBA", (32, 32), view.BG + (255,))
            ImageDraw.Draw(ic).polygon([(10, 8), (30, 8), (22, 24), (2, 24)], fill=view.AMBER)
            self._ic = self.ImageTk.PhotoImage(ic)
            self.root.iconphoto(True, self._ic)
        except Exception:
            pass

    def _dark_title_bar(self):
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            on = ctypes.c_int(1)
            for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new id, then pre-20H1 id)
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), 4) == 0:
                    break
        except Exception:
            pass

    def _footer(self):
        tk = self.tk
        bar = tk.Frame(self.root, bg=_hex(view.PANEL), height=self.FOOT)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)
        btn = dict(bg=_hex(view.PANEL_HI), fg=_hex(view.INK), activebackground=_hex(view.LINE),
                   activeforeground=_hex(view.INK), relief="flat", bd=0, padx=14, pady=6,
                   font=("Bahnschrift SemiBold SemiCondensed", 12), cursor="hand2")
        tk.Button(bar, text="↻  Replay last capture", command=self.replay, **btn).pack(
            side="left", padx=(view.PAD, 8), pady=10)
        self.pin = tk.BooleanVar(value=bool(self.settings.get("topmost", False)))
        tk.Checkbutton(bar, text="Keep on top", variable=self.pin, command=self._pin,
                       bg=_hex(view.PANEL), fg=_hex(view.SOFT), selectcolor=_hex(view.BG),
                       activebackground=_hex(view.PANEL), activeforeground=_hex(view.INK),
                       font=("Segoe UI", 10), bd=0, highlightthickness=0).pack(side="right", padx=(8, view.PAD))
        self.ban_var = tk.StringVar(value=self.settings.get("bans_text", ""))
        ent = tk.Entry(bar, textvariable=self.ban_var, width=24, bg=_hex(view.BG), fg=_hex(view.INK),
                       insertbackground=_hex(view.INK), relief="flat", font=("Segoe UI", 11),
                       highlightthickness=1, highlightbackground=_hex(view.LINE),
                       highlightcolor=_hex(view.AMBER))
        ent.pack(side="right", ipady=4, pady=10)
        tk.Label(bar, text="BANS", bg=_hex(view.PANEL), fg=_hex(view.MUTE),
                 font=("Bahnschrift SemiBold SemiCondensed", 11)).pack(side="right", padx=(8, 8))
        ent.bind("<Return>", lambda e: self._bans_changed())
        ent.bind("<FocusOut>", lambda e: self._bans_changed())
        self.bans = parse_bans(self.ban_var.get())

    # -- events
    def _bans_changed(self):
        new = parse_bans(self.ban_var.get())
        self.settings["bans_text"] = self.ban_var.get()
        save_settings(self.settings)
        if new != self.bans:
            self.bans = new
            log.info("bans now %s", new)
            if self.last_frame is not None:
                self.replay()

    def _pin(self):
        self.settings["topmost"] = bool(self.pin.get())
        self.root.attributes("-topmost", self.settings["topmost"])
        save_settings(self.settings)

    def _moved(self, event):
        if event.widget is not self.root:
            return
        x, y = self.root.winfo_x(), self.root.winfo_y()
        if (x, y) != (self.settings.get("x"), self.settings.get("y")):
            self.settings["x"], self.settings["y"] = x, y
            if getattr(self, "_save_job", None):
                self.root.after_cancel(self._save_job)
            self._save_job = self.root.after(600, lambda: save_settings(self.settings))

    def close(self):
        self.settings["x"], self.settings["y"] = self.root.winfo_x(), self.root.winfo_y()
        save_settings(self.settings)
        self.watcher.stop.set()
        self.root.destroy()

    def _warm(self):
        """Import modules and load templates before the first Tab press."""
        t = time.perf_counter()
        try:
            from . import stub_reader
            stub_reader._load_templates()
            frame = imread(LAST) if os.path.exists(LAST) else np.zeros((1080, 1920, 3), np.uint8)
            pipeline.run(frame, [])
            view.render({"state": {"board_open": False}, "timing": {}})
        except Exception as e:
            log.warning("warm-up failed: %s", e)
        log.info("warm-up %.0f ms", (time.perf_counter() - t) * 1000)

    def _load_last(self):
        if os.path.exists(LAST):
            try:
                self.last_frame = imread(LAST)
            except BaseException:
                self.last_frame = None

    def replay(self):
        if self.last_frame is None:
            log.info("replay: no capture yet")
            return
        frame = self.last_frame

        def work():
            t0 = time.perf_counter()
            r = pipeline.run(frame, list(self.bans))
            r["when"] = "replay " + datetime.now().strftime("%H:%M:%S")
            r["t_down"] = t0
            self.q.put(("replay", r, None))
        threading.Thread(target=work, daemon=True).start()

    def _pump(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "front":
                    if self.mode in ("idle", "live"):
                        self.mode = "live" if msg[1] else "idle"
                        self.show(self.last_result)
                elif msg[0] in ("result", "replay"):
                    _, result, frame = msg
                    self.mode = "live" if msg[0] == "result" else "replay"
                    self.show(result)
                    t = result.setdefault("timing", {})
                    if result.get("t_down") is not None:
                        t["total_ms"] = (time.perf_counter() - result["t_down"]) * 1000
                        self.show(result)  # repaint the footer with the final total (cheap)
                    log_timing(msg[0], result)
                    if result.get("state", {}) and result["state"].get("board_open"):
                        self.last_result = result
                    if frame is not None:
                        self.last_frame = frame
                        threading.Thread(target=_save_png, args=(frame,), daemon=True).start()
                    if msg[0] == "replay":
                        self.mode = "live" if self.watcher.game_front else "idle"
        except queue.Empty:
            pass
        self.root.after(15, self._pump)

    def show(self, result):
        note = None
        if result is None:
            note = ("Overwatch is in front: hold Tab." if self.mode == "live"
                    else "Waiting for the Overwatch window to be in front.")
        img = view.render(result, {"mode": self.mode, "note": note})
        self._photo = self.ImageTk.PhotoImage(img)
        self.canvas.configure(image=self._photo)
        self.root.update_idletasks()

    def run(self):
        self.root.mainloop()


def _save_png(frame):
    try:
        import cv2
        os.makedirs(os.path.dirname(LAST), exist_ok=True)
        ok, buf = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, 1])
        if ok:
            buf.tofile(LAST + ".tmp")
            os.replace(LAST + ".tmp", LAST)
    except Exception as e:
        log.warning("could not save last capture: %s", e)


def _monitors() -> list[dict]:
    try:
        import mss
        with mss.mss() as s:
            return s.monitors[1:]
    except Exception:
        return [{"left": 0, "top": 0, "width": 1920, "height": 1080}]


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(rgb[:3])


# ---------------------------------------------------------------- test mode
def test_image(path: str, bans: list[str], out_dir: str = SHOTS) -> str:
    frame = imread(path)
    t0 = time.perf_counter()
    result = pipeline.run(frame, bans)
    result["when"] = os.path.basename(path)
    img = view.render(result, {"mode": "test"})
    result["timing"]["total_ms"] = (time.perf_counter() - t0) * 1000
    img = view.render(result, {"mode": "test"})  # with the final total in the footer
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
    name = f"{parent}-{stem}.png" if stem in ("image",) else f"{stem}.png"
    out = os.path.join(out_dir, name)
    img.save(out)
    log_timing("test", result)
    adv = result.get("advice") or {}
    print(json.dumps({"image": path, "saved": out, "action": adv.get("action"), "to": adv.get("to"),
                      "headline": adv.get("headline"), "sources": result["sources"],
                      "timing_ms": {k: round(v, 1) for k, v in result["timing"].items()}}, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="counterwatch", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", nargs="+", help="screenshot(s) to run through the pipeline (test mode)")
    ap.add_argument("--bans", default="", help="banned heroes, comma separated (test mode)")
    ap.add_argument("--out", default=SHOTS, help="where test mode saves the window PNG")
    args = ap.parse_args(argv)
    setup_logging()
    if args.image:
        for p in args.image:
            test_image(p, parse_bans(args.bans), args.out)
        return
    if sys.platform != "win32":
        raise SystemExit("Counterwatch's live mode runs on Windows.")
    dpi_aware()
    log.info("Counterwatch starting")
    App(load_settings()).run()
