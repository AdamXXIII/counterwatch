"""Evaluate counterwatch.reader on the labelled captures.

    python bench/eval_reader.py                     # HEADLINE: leave-one-match-out, session
    python bench/eval_reader.py --stateless         # reset the reader before every image
    python bench/eval_reader.py --leave-image-out   # only hide the tested image's own crops
    python bench/eval_reader.py --full              # use every reference crop (what ships)

Leave-one-match-out is the headline because testdata/mine holds several near-identical boards per
match: with only the tested image hidden, its siblings still supply crops of the same players,
which flatters the score. Every web image is a different match, so for web the modes agree.
Matches: A and B are listed below; newer captures carry "match" in their truth.json.

Session mode (default): testdata/mine captures are fed to the reader in time order within each
match, without resetting it, as the app sees them, so a dead row can fall back on the last live
read of that row. The session is reset when the match changes and before every web image. The
default run also prints the stateless mine score so per-frame accuracy stays visible.

Prints per-image and overall slot accuracy for testdata/mine and testdata/web (web split into
mid-match and end-of-match boards), board_open, my_hero and dead-flag accuracy, and the median
and max read() time in ms (warm, after the reference set has loaded).
"""
import argparse
import os
import statistics
import sys
import time

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "reader"))
from dataset import imread, labelled_images  # noqa: E402
from counterwatch import reader  # noqa: E402

# leave-one-match-out hides a whole match. A mine capture with no match counts as its own.
MATCH_OF = {"mine/tab-20261114-225509": "A", "mine/tab-20261114-225616": "A", "mine/tab-20261114-225812": "A",
            "mine/tab-20261114-230038": "A", "mine/tab-20261114-230053": "A", "mine/tab-20261114-230213": "A",
            "mine/tab-20261114-230347": "A", "mine/tab-20261114-230858": "B"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--leave-image-out", action="store_true")
    ap.add_argument("--leave-match-out", action="store_true", help="the default; kept for old scripts")
    ap.add_argument("--stateless", action="store_true", help="reset the reader before every image")
    ap.add_argument("--rescale", help="WxH: resize each 1920x1080 capture to this 16:9 size first "
                    "(robustness check for other monitor resolutions)")
    args = ap.parse_args()
    reader.refs()  # load references before timing
    images = list(labelled_images())
    for st, tag, path, truth in images:
        if st == "mine" and truth.get("match"):
            MATCH_OF.setdefault(tag, truth["match"])
    res = evaluate(args, images, stateless=args.stateless, verbose=True)
    mode = "full reference set" if args.full else (
        "leave-one-image-out" if args.leave_image_out else "leave-one-match-out (headline)")
    mode += ", stateless" if args.stateless else ", session (mine fed in time order per match)"
    print(f"\n== {mode} ==")
    report(res)
    if not args.stateless:
        r2 = evaluate(args, [x for x in images if x[0] == "mine"], stateless=True, verbose=False)
        ok, n, iok, ni = r2["groups"]["mine"]
        print(f"mine stateless (reset before every image): slots {ok}/{n} = {100 * ok / n:.1f}%   "
              f"images fully right {iok}/{ni}   {'; '.join(r2['errs']) or 'no errors'}")


def evaluate(args, images, stateless: bool, verbose: bool) -> dict:
    R = reader.refs()
    tags_backup = R.tags.copy()
    groups = {}
    unver = []
    all_errs = []
    times = []
    times_1080 = []
    my_ok = my_n = dead_ok = dead_n = 0
    prev_match = None
    for st, tag, path, truth in images:
        img = imread(path)
        if args.rescale and img.shape[:2] == (1080, 1920):
            w, h = map(int, args.rescale.lower().split("x"))
            img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA if w < 1920 else cv2.INTER_CUBIC)
        excl = None if args.full else tag
        if not args.full and not args.leave_image_out and tag in MATCH_OF:
            m = MATCH_OF[tag]
            R.tags = tags_backup.copy()
            for t, mm in MATCH_OF.items():
                if mm == m:
                    R.tags[R.tags == t] = tag
        match = MATCH_OF.get(tag, tag)
        if stateless or st != "mine" or match != prev_match:
            reader.reset_session()
        prev_match = match
        t0 = time.perf_counter()
        out = reader.read(img, _exclude_tag=excl)
        ms = (time.perf_counter() - t0) * 1000
        R.tags = tags_backup
        times.append(ms)
        if img.shape[1] == 1920 and img.shape[0] == 1080:
            times_1080.append(ms)
        phase = "mid" if (st == "mine" or truth.get("phase") == "mid_match") else "end"
        g = f"{st}/{phase}" if st == "web" else st
        ok = n = 0
        errs = []
        want_open = bool(truth.get("my_team"))
        if out["board_open"] != want_open:
            errs.append(f"board_open={out['board_open']} want {want_open}")
            n += 1
        elif not want_open:
            ok += 1
            n += 1
        for key in ("my_team", "enemy_team"):
            for i, t in enumerate(truth.get(key, [])):
                got = out[key][i] if i < len(out[key]) else {"hero": "-", "dead": False}
                if t["hero"] == "unknown" and got.get("dead"):
                    # labelled "unknown" because a respawn ring hides the face: the labeller could
                    # not tell. Left out of the main score; the strict score wants "unknown" back.
                    unver.append((g, tag, f"{key[:2]}{i + 1}", got["hero"]))
                    continue
                n += 1
                if got["hero"] == t["hero"]:
                    ok += 1
                    if got.get("src") == "memory":
                        errs.append(f"({key[:2]}{i + 1} {got['hero']} from row memory)")
                else:
                    errs.append(f"{key[:2]}{i + 1} {t['hero']}->{got['hero']} ({got.get('conf', 0)})")
                if st == "mine" and "dead" in t and got["hero"] != "-":
                    dead_n += 1
                    dead_ok += got["dead"] == t["dead"]
                    if got["dead"] != t["dead"]:
                        errs.append(f"{key[:2]}{i + 1} dead={got['dead']}")
        if truth.get("my_hero") is not None or (st == "mine" and want_open):
            my_n += 1
            my_ok += out["my_hero"] == truth.get("my_hero")
            if out["my_hero"] != truth.get("my_hero"):
                errs.append(f"my_hero {truth.get('my_hero')}->{out['my_hero']}")
            elif out.get("my_hero_src") not in (None, "row"):
                errs.append(f"(my_hero {out['my_hero']} from {out['my_hero_src']})")
        groups.setdefault(g, [0, 0, 0, 0])
        groups[g][0] += ok
        groups[g][1] += n
        groups[g][2] += ok == n
        groups[g][3] += 1
        all_errs += [f"{tag} {e}" for e in errs if not e.startswith("(")]
        if verbose:
            print(f"{tag:32s} {g:8s} {ok:2d}/{n:2d} {ms:6.1f} ms  {'; '.join(errs)}")
    return dict(groups=groups, unver=unver, errs=all_errs, times=times, times_1080=times_1080,
                my=(my_ok, my_n), dead=(dead_ok, dead_n))


def report(res: dict) -> None:
    groups, unver = res["groups"], res["unver"]
    for g in ("mine", "web/mid", "web/end"):
        if g in groups:
            ok, n, iok, ni = groups[g]
            print(f"{g:8s} slots {ok}/{n} = {100 * ok / n:.1f}%   images fully right {iok}/{ni}")
    wok = sum(groups[g][0] for g in groups if g.startswith("web"))
    wn = sum(groups[g][1] for g in groups if g.startswith("web"))
    if wn:
        print(f"web all  slots {wok}/{wn} = {100 * wok / wn:.1f}%")
    if unver:
        print(f"unverifiable slots (truth 'unknown' under a respawn ring, left out above): {len(unver)}")
        for g, tag, slot, got in unver:
            print(f"    {tag} {slot} read as {got}")
    if "web/mid" in groups:
        um = [u for u in unver if u[0] == "web/mid"]
        sok = groups["web/mid"][0] + sum(u[3] == "unknown" for u in um)
        sn = groups["web/mid"][1] + len(um)
        print(f"web/mid strict (those slots right only when read as unknown): {sok}/{sn} = {100 * sok / sn:.1f}%")
    my_ok, my_n = res["my"]
    dead_ok, dead_n = res["dead"]
    if my_n:
        print(f"my_hero  {my_ok}/{my_n}")
    if dead_n:
        print(f"dead flag (mine) {dead_ok}/{dead_n}")
    times, times_1080 = res["times"], res["times_1080"]
    print(f"read() ms: median {statistics.median(times):.1f}, max {max(times):.1f} (all {len(times)} images)")
    if times_1080:
        print(f"read() ms at 1920x1080: median {statistics.median(times_1080):.1f}, max {max(times_1080):.1f}")


if __name__ == "__main__":
    main()
