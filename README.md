# Counterwatch

Hold Tab in Overwatch 2 and Counterwatch tells you, on your second screen, whether to swap and what to swap to.

It reads the Tab scoreboard, works out both team comps, and gives one call for your role: **SWAP** to a named hero, **STAY**, or, when it isn't sure, **MAYBE / LOOK AGAIN** with the reason. The aim is advice as good as a top coach's, within two seconds of holding Tab. In practice it takes about 0.3 s.

## Safe by design

Counterwatch only looks at the screen, the same way a screenshot would.

- No Overwolf, no overlay drawn over the game, nothing injected into it
- No memory reading, no packet reading
- Tab is read passively; it never sends keys to the game

The advice shows in its own window, which you can leave on a second monitor.

## How it works

1. **Reader.** When you hold Tab, it grabs the screen, finds the scoreboard and matches each row's portrait against a bank of hero portraits. It handles dead players, hidden enemy picks at the start of a match, and different screen sizes. On a held-back set of real matches it read every hero correctly (251 out of 251 slots), at about 70 ms a read.
2. **Engine.** It scores every hero for your role against the whole enemy comp, not just one matchup. It weighs hard and soft counters, checks the tank duel first, and counts the cost of swapping, so it only says swap when the gain is worth losing ult charge. The counter data in `data/counters.json` is sourced from patch notes, hero pages, published win rates and coach guides; `data/counters_notes.md` lists every source and the open disagreements between them.
3. **Window.** One decision word, the hero, and a one-line reason. Unsure calls say so instead of guessing.

The bar it is tested against is in `bench/coach_cases.md`: 36 real swap calls from coaches' VOD reviews and guides, each linked to the moment in the video, with 18 kept back for blind judging.

## Status

Early and in testing. The reader passes its test; the engine still makes some wrong picks (for example Mauga into Wrecking Ball), and the wording for unsure calls is still being tuned.

## Run it

Windows 10 or 11 and Python 3.14 (what it is built and tested on).

```bash
pip install -r requirements.txt
python -m counterwatch
```

Or double-click `run.bat`. Then drag the Counterwatch window onto your second screen and hold Tab in a match.

Test mode runs the whole pipeline on a screenshot, no game needed, and saves a picture of the window:

```bash
python -m counterwatch --image my-scoreboard.png --bans ana,sojourn
```

## Layout

| Path | What it is |
|---|---|
| `counterwatch/` | The app: screen reader, counter engine, advice window |
| `data/` | Hero roster, counter matchups and their sources, scoreboard layout notes |
| `assets/heroes/` | Hero portraits the reader matches against |
| `bench/` | Coach cases and the scripts that score the engine against them |
| `testdata/` | Answer files for the reader tests (bring your own screenshots: see below) |
| `tools/` | Scripts that rebuild the roster, the counters and the portrait bank |

The reader tests use scoreboard screenshots, which show other players' BattleTags, so the screenshots themselves are not in this repository. Save your own with `tools/capture_tab.py` into `testdata/mine/`.

## Not affiliated

Counterwatch is a fan-made tool, not affiliated with or endorsed by Blizzard Entertainment. Overwatch and the hero portraits are trademarks and artwork of Blizzard Entertainment.
