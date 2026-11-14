# Overwatch Tab scoreboard layout (1920x1080)

Measured on 2026-11-14 from the real screenshots in `testdata/web/1` to `testdata/web/35`
(all user uploads from the Overwatch Steam community screenshot pages; each folder's `source.txt`
has the image URL, the page and the date). All pixel numbers below are in a **virtual 1920x1080
canvas**: an image wider than 16:9 is scaled to 1080 high and the middle 1920 columns kept; an
image narrower than 16:9 (16:10, windowed 2560x1494) is scaled to 1920 wide and the middle 1080
rows kept. With that rule every 2026 screenshot (1440x900, 1920x1080, 2434x1369, 2560x1440,
2560x1494, 3269x1401, 3440x1440, 3840x2160) puts the rows at the same y, so the reader should
do the same normalisation before anything else. Measuring code: python + PIL + numpy on the PNGs.

## 0. Match phase of the test images (fact-check, 2026-11-14)

The screenshots are not all mid-match. 25 of 35 were taken with Tab held at the END of a match
(VICTORY/DEFEAT/FINAL SCORE watermark behind the board, ENDORSE PLAYERS / STAY AS TEAM buttons, or
an Athena "Victory"/"Defeat" chat line): #2-#12, 14, 15, 16 (faint DEFEAT, lower confidence), 18, 19, 21, 24, 27, 28, 30, 31, 33, 34, 35.
Only 10 are mid-match: #1, #13, #17, #20, #22, #23, #25, #26, #29, #32. Each truth.json now has
`phase` and `phase_evidence`. The board geometry is the same in both phases, but end-of-match
boards never show dead players, respawn rings or hidden "?" enemies, and a watermark can sit
behind the rows, so accuracy must be reported separately on the mid-match subset; the 50-image
target needs more mid-match captures.

## 1. What is on screen

```
y 0-80     top bar: left = tabs (only in some variants) and/or competitive hero bans;
           right = "MODE | MAP" text and "TIME: mm:ss" (x ~1430-1880, y ~30-60)
y 157-187  light grey header bar (RGB ~215,218,223) with column titles E A D DMG H MIT
y 188-517  YOUR TEAM, 5 rows               x from L to ~1920-L-465 (board)
y 539-570  "VS" text, centred on the board (x 715-747 when L=268) with thin lines either side
y 594-923  ENEMY TEAM, 5 rows
x 1920-L-435 .. 1920-L, y 157-922: hero panel for YOUR OWN hero only (big portrait, hero name,
           hero-specific stats). Absent when you have not picked a hero yet (see #26).
y ~1030-1080 centre: "INTERACT" button (or "CLOSE" when the board is in interact mode)
```

* **Your team is always the upper block, the enemy always the lower block.** Colour does not tell
  you which is which: colours are player options (seen: ally blue 9,182,241 / enemy red 226,58,89 by
  default; ally cyan 11,241,241 + enemy orange 203,95,20 in #29-31; ally pink + enemy yellow in #4,
  #5; ally yellow in #27; enemy pink in #10; enemy magenta in Stadium #35). Use position.
* The whole thing (board + gap + hero panel) is **centred on x=960**, so the board's left edge
  L moves with the board width: hero panel right edge = 1920 - L (checked on #8, #17, #29, #34).
* A **green role strip** on an ally row means that player is in your group (#2, #3, #11, #18, #21).
* Your own row is drawn brighter than the others (#13 row 4, #29 row 4, #26 row 4).

## 2. Rows (2026 layout)

| | row 1 | row 2 | row 3 | row 4 | row 5 |
|---|---|---|---|---|---|
| your team, top y | 188 | 254 | 320 | 386 | 452 |
| enemy, top y | 594 | 660 | 727 | 793 | 859 |

Row height 64-65 px, pitch 66 px (65.75), 1-2 px dark separator. Measured from the role strip
colour runs on #29 (ally 188-252, 254-318, 320-384, 386-451, 452-517; enemy 594-659, 661-725,
727-791, 793-857, 859-923). Checked on every 2026 non-Stadium image (#3-#21, #23-#33, 30
images, all board-width variants and all source resolutions): after normalisation the ally block
runs y 187/188 to 516/517 and the enemy block y 594 to 922/923 in all of them (#21 enemy block
confirmed, ally block split by its green group strip but at the same rows).

Inside each row, left to right (offsets from L):

| piece | x | notes |
|---|---|---|
| role strip | L .. L+28 | team colour; white role icon centred ~ (L+14, top+32), about 16x19 px (shield = tank, three bullets = damage, cross = support) |
| **hero portrait** | **L+29 .. L+92 (64x64 px), y = top .. top+63** | square crop of the hero's face, painted art, with the row colour behind it |
| ult ring / perk-level circle | ~L+97 .. L+137 | "0" circle in most 2026 shots; in the tabbed variant, ally rows show ultimate charge % here (#13, #17, #23) |
| player name | ~L+147 | BattleTag in the OW display font, title / badge under it. This is the PLAYER name, not the hero name |
| perk icons | two white circles, centres ~L+355 and ~L+413 (y top+12 .. top+51) | the minor/major perks the player has taken; 0, 1 or 2 shown; both teams |
| stats E A D DMG H MIT | centres ~L+469, +520, +570, +650, +742, +834 | localised headers (DAN, C, M, DAÑO, S...) |
| voice / mute | ~L+882 .. L+919 | |

### Board width variants (left edge L in the 1080p canvas)

| L | seen in | what is different |
|---|---|---|
| 268 | most 2026 shots (#3-#7, #9-#12, #14, #18-#21, #24, #27-#33) | two perk slots, no extra columns |
| 230 | #8 | interact mode ("CLOSE" button): chat, mute and report button columns added on the right |
| 291 | #13, #16 | tabbed variant ("HERO INFO / SCOREBOARD" tabs top-left), one perk slot, ult % on ally rows |
| 297-298 | #15, #23, #25, #32 | one perk slot |
| 318 | #17 | no perk column |
| 551 | #26 | no hero panel (local player has not picked), board centred alone |
| 282 | #1, #2 (2025) | old 2025 build, see section 6 |
| 140 | #34 (Stadium) | wider board, see section 5 |

Find L at run time instead of hard-coding it: scan y 165-180 from the left for the first column
whose mean brightness is > 170 (the header bar). Then portrait = (L+29, top, L+93, top+64).
**Fact-check correction (2026-11-14):** the y 165-180 scan only works for the 2026 non-Stadium
board (and #1). It returns nothing on the Stadium boards (#34, #35; header bar y ~178-210) and on
the 2025 board #2 (header y ~172-205). Scanning y 185-205 instead finds L = 140 (#34), 182 (#35),
282 (#1, #2). The reader must try both bands (2026 band first) before deciding the board is shut.
The rows' y positions did not move between these variants (except Stadium and the 2025 build).

## 3. What the enemy side shows

* Same row structure as yours: role icon, hero portrait, player name, perks, all six stats.
* No ultimate-charge % on enemy rows (only ally rows show it, tabbed variant).
* **Enemy portraits can be hidden.** In #25 and #32 (mid-match, enemy stats non-zero) and #26
  (TIME 0:00) every enemy portrait is a grey "?" head silhouette; the enemy role icons are still
  shown. All three come from the same player, so the cause is not confirmed. Separately, the
  official 2024-10-15 patch notes say "Swapping your hero hides your selection on the enemy
  scoreboard for 15 seconds."
  (https://overwatch.blizzard.com/en-us/news/patch-notes/live/2024/10/). A "?" portrait must be
  read as `unknown`, never matched to a hero.
* The same hero can be on both teams (mirror picks: shion in #8, roadhog in #12, doomfist in #31).

## 4. Row order, dead players, leavers, swaps

* Role queue: rows are tank, damage, damage, support, support on both teams; the role icon on the
  row is the authority (Sombra shows the damage icon on 13 Sep 2026 (#13) and the support icon from
  late Oct (#20, #27), matching the 2026-10-06 role change recorded in `data/heroes.json`). Doctrine appears in #13
  (13 Sep 2026) before his 6 Oct launch because of the 12-14 Sep 2026 Hero Trial
  (https://beebom.com/overwatch-announces-new-hero-doctrine-coming-to-season-5/).
* Open queue / arcade: rows follow players, not roles. #1 (Push - Random Heroes, 2025) has
  tank, support, tank, damage, support. Stadium rows are not in role order either (#34: damage,
  damage, tank, support, support).
* **Dead players**: the portrait is darkened and a red-and-white ring with the respawn seconds
  ("4", "8") is drawn over its centre (#13 rows 3-4, #23 rows 1 and 5). The hero is often not
  recognisable; the chat line "[PLAYER (HERO)]" or the kill feed may name it.
* **Leavers**: the row reads "WAITING FOR PLAYER" (localised: "AGUARDANDO JOGADOR") with a
  three-dot placeholder where the portrait goes and all stats 0, and the remaining players move
  UP, so the first enemy row can be a damage hero (#17, #34) and empty rows sit at the bottom (#35).
* **Not picked yet**: "?" silhouette in the player's own team colour (#26 row 4).
* **Swaps**: the portrait simply changes to the new hero; there is no marker on the board. A chat
  line may say so ("SleepyBear switched to Shion (was Genji)" in #32, and row 3 already shows Shion).
* Status effects: red fire icons can appear just left of an enemy row's role strip (#13, #23).
* Bugged / empty board: #22 shows the header, VS and hero panel with no rows at all. The
  2026-11-05 patch notes list "Fixed an issue where the Scoreboard and related screens would not
  display properly." (https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/11/).
  Treat a board with no portraits as "no reading", not as an empty team.

## 5. Stadium

Seen in #34 (Payload Race, late Oct-Nov 2026 by file-ID order), #22 (Control Samoa, empty-board bug) and
#35 (older build; its date is only bounded Aug 2025-Jun 2026, "2025" is inferred from the 62 px pitch).
#34 and #35 are both end-of-match boards.

* Top-left tabs "TEAM BUILDS | SCOREBOARD | ENEMY BUILDS" (#34) or "HERO INFO | TEAM BUILDS |
  SCOREBOARD" (#22); top centre: team cash totals and round score boxes ("0 | ROUND 3 | 3").
* Header row starts with "VIEW: TOTAL STATS" and adds a Stadium cash column and BTY (bounty).
* Rows are taller: #34 header y 178-210, ally rows y 211-569 (tops ~211, 283, 354, 426, 497,
  pitch ~71.5), VS ~y 610, enemy rows y 654-1012 (tops ~654, 726, 797, 869, 940). L = 140, portrait
  ~70x70 at x ~170-240. Stadium rank badges (roman numerals) sit next to player names (#35).
* Rows are not in role order; use each row's role icon.
* The Team Builds / Enemy Builds tabs are different screens (item cards, no rows); the reader must
  only read the SCOREBOARD tab.

## 6. Older 2025 build (for reference only)

#1 (Jul 2025) and #2 (Aug 2025): L = 282, header y ~172-205, rows ~62 px pitch, ally rows
y ~206-514, enemy y ~599-907 (#2), portraits ~60 px at x ~312-372, no perk icons. #35 (Stadium,
2025) uses the same 62 px pitch with L = 182. A reader tuned on the 2026 numbers will miss these by
15-20 px; locating rows from the role strip runs makes it robust to both.

## 7. Text on the board

* Hero names do **not** appear as text in the rows. Rows show player names (BattleTags in many
  scripts: Latin, Japanese, Chinese) and a title. The only hero-name text is the hero panel title
  for your own hero ("MOIRA", "RAMATTRA", "BASTION"), starting about 28 px inside the hero panel's
left edge (x ~1245 when L=268) at y ~370-405, and chat
  lines of the form "[PLAYER (HERO)]".
* The UI is localised (Italian #29-31, Portuguese #17, Spanish #23, Polish, Russian ...), so any
  OCR anchor must not rely on English words. The header bar, the "VS" mark and the row geometry
  are language-independent.

## 8. Recommended reader recipe

1. Grab the screen, normalise to 1920x1080 as above.
2. Check the board is open: light header bar at y 157-187 (2026), or y ~172-210 (Stadium, 2025
   build), and a "VS" mark between the two blocks.
3. Find L from the header bar; find row bands from the saturated role strip at x L..L+28.
4. For each band: portrait = (L+29, top, L+93, top+64); role = role icon; flag "?" silhouettes,
   three-dot leaver rows and red respawn rings as unknown.
5. Upper 5 bands = your team, lower 5 = enemy.

## Sources

* Screenshots: Steam Community, Overwatch (app 2357570) screenshot pages, one page per image,
  listed in each `testdata/web/<n>/source.txt`. Fact-check 2026-11-14: every image_url was
  re-downloaded; all 35 are JPEG originals that decode pixel-identical to the saved image.png. Dates confirmed on the Steam page for #1-#19 and
  #29; the rest are bounded by Steam file-ID order (noted in each source.txt) because the Steam
  detail pages returned HTTP 429 while this was collected.
* https://overwatch.fandom.com/wiki/Scoreboard (opened 2026-11-14): Tab opens it; six stats
  E/A/D/DMG/H/MIT; right panel with hero-specific stats only for the player on that hero;
  interactive scoreboard (Mouse3) for social features.
* https://overwatch.blizzard.com/en-us/news/patch-notes/live/2024/10/ (interactive scoreboard,
  15-second hide after a swap).
* https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/11/ (2026-11-05 scoreboard
  display fix).
* https://beebom.com/overwatch-announces-new-hero-doctrine-coming-to-season-5/ (Doctrine Hero Trial
  12-14 Sep 2026, launch 6 Oct 2026).
