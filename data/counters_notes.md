# Counter data: sources and confidence

`data/counters.json` is built by `tools/build_counters.py` (matchups and stat ratings) and `tools/counters_meta.py` (synergies, archetypes, swap rules, patch flags). Run `python -I tools/build_counters.py` to rebuild. As of 2026-11-14: Season 5 "A Grim Doctrine", after the 2026-11-03 midseason patch and the 2026-11-05 hotfix, 5v5 role queue.

## Roster
54 heroes, taken from the official hero page (https://overwatch.blizzard.com/en-us/heroes/). New since 2025: Domina, Emre, Mizuki, Anran and Jetpack Cat (Season 1 2026), Sierra (Season 2), Shion (Season 3), D.Mon, and Doctrine (hero 54, Season 5, 2026-10-06). Freja, Hazard, Juno, Wuyang and Vendetta are also in the roster. Sombra is now a **Support** (Tactician). Hero 55 (Hudson, an omnic detective) is announced for Season 6 (around 2026-12-08, per esports.gg and Dexerto) but has not been released, so it is not covered. Roles and sub-roles come from the official Season 1 2026 spotlight (https://overwatch.blizzard.com/en-us/news/24246206) and the hero pages. IDs match `tools/roster/build_heroes_json.py`.

## Sources used
| Source | What it gave | Weight |
|---|---|---|
| Blizzard hero pages, `/heroes/<slug>/` | Current kits (D.Mon, Doctrine, Sierra, Shion, Vendetta, Wuyang, Hazard, Freja, reworked Sombra and Roadhog, D.Va, Cassidy) | Authoritative for mechanics |
| Patch notes 2026/02, 2026/10, 2026/11 (overwatch.blizzard.com/en-us/news/patch-notes/live/...) | Sub-role passives, Sombra and Roadhog reworks, all Season 5 balance numbers | Authoritative |
| counterwatch.gg hero pages, `/stats/overwatch/heroes/<slug>` | Top-5 "counters" and "strong against" counter ratings for all 54 heroes (all ranks; the pages say ratings pool all game types, so they are not 5v5-only; updated 2026-11-14) | Main stat source. Stored as `stat_counter_ratings` |
| counterwatch.gg tier list and Season 5 meta blog | Win rates per hero (Torbjörn 56.5%, Reinhardt and Domina the top tanks, Sojourn, Mauga and Baptiste the lowest) | Context |
| counterwatch.gg blog: swap after death, counter-picking, one-tricks | Measured cost of swapping and counter thresholds | Basis for most of `swap_rules` |
| esports.gg 2026 counter table (https://esports.gg/news/overwatch/overwatch-2-hero-counters/) | Named counters for every hero, including Doctrine | Editorial cross-check |
| Mobalytics hero guides (`mobalytics.gg/overwatch/heroes/<slug>-guide`) | How-to-counter and synergy text for Domina, Doctrine, Vendetta, Sierra, Shion, Wuyang, Jetpack Cat, Mizuki, Anran, Emre, Freja, Hazard, Juno, Sombra and Roadhog | Mechanics-level reasons for the new heroes |
| Official rates page (https://overwatch.blizzard.com/en-us/rates/) | Win and pick rates | Read but not used: the fetched table appears to have its columns swapped (the "pick" column holds about 45-57%) |
| Overbuff | Shut down. The page points to Blizzard's official rates | None |

## Not done here: coach VODs
I did not watch any named coach's YouTube VOD in this pass. The search turned up no coach-attributed swap calls for Season 5. `swap_rules` are therefore based on measured data (counterwatch.gg, millions of swaps) plus editorial guides, not on named coaches. The coach freeze-frame comparison belongs to the separate benchmark piece. When that piece finds coach calls, they should be added as sourced rules.

## How matchups were built
- Each pair `(A strong_vs B, reason)` is written once and mirrored, so B's `weak_vs` A carries the same reason.
- Every pair needs a mechanism I could state from current kits. Stat pairs with no plausible mechanism were left out of `matchups`, though they stay in `stat_counter_ratings`. Most of these are support-vs-support artifacts, such as Mercy "countering" Torbjörn (+7.7) or Zenyatta. Treat these as team-composition effects, not duel counters.
- About 440 pairs in total. Every hero has both sides except Mercy: she has no `strong_vs`, because nothing she does counters a specific hero. Wuyang, Shion and Mizuki have the thinnest lists.
- Two conflicts were resolved in favour of the stats plus the mechanism: Baptiste beats Sombra (+9.8; esports.gg says the reverse), and Moira beats D.Va (her beam ignores Defense Matrix, +5.2).
- Tags like `[2026-10-06]` inside a reason mean the matchup depends on a 2025-2026 change. `patch_flags` lists the change per hero.

## Changes that break old counter knowledge
- **Sombra Hack is gone** (2026-10-06). Only EMP hacks now. "Sombra hacks Ball out of his grapple" now needs her ult. Her new counter tool is Cyberspace Weaken: it halves damage and healing, cut to 40% on 2026-11-03. Per counterwatch.gg it is strong against brawl tanks: Mauga +11.2, Junker Queen +9.4.
- **Roadhog reworked** (2026-10-06): Trash Compactor absorbs projectiles, the Hook stun is shorter and the pull ends 4.5 m away. Anti-heal still beats Take a Breather (Ana +9.2), and Doctrine's Deliverance max-health cut is his worst matchup (+11.4).
- **Reaper Shadow Step and Anran Dancing Blaze no longer cleanse** (2026-02).
- **Ana Biotic Grenade** damage is cut from 90 to 60 (2026-11-03). The anti-heal is kept, so her counter value against sustain tanks stands.
- **Genji Deflect** is cut from 2 s to 1.5 s (2026-11-03), so it reflects less.
- **Cassidy Flashbang** now hinders (it locks movement abilities, per the perk text on the official page) rather than stunning. The reasons say "hinder".
- **Sub-role passives** (2026-02): Stalwart tanks (Rein, JQ, Sigma, Ram, Domina, D.Mon, Hazard) resist knockback and slows by 40%, so boop counters such as Lúcio and Domina's Repulsors hit them less hard.
- **Ult charge kept on a swap** is a maximum of 25% (Season 3 2023 patch note). I found no 2026 change. This could not be checked against a 2026 Blizzard source.

## Confidence
- **High:** kit facts, patch numbers, the roster, and the stat ratings as copied.
- **Medium:** the mechanism behind each stat pair. Most come from guides, a few are my own reading of the kits. Counter ratings pool all ranks, and counterwatch.gg itself warns that the Bronze meta is not the GM meta.
- **Low:** synergies for older heroes (classic pairings, not freshly sourced) and the archetype buckets (my classification, with overlaps on purpose).
- Win-rate edges are small: counterwatch.gg calls 53-55% a strong counter. The advice engine should present counters as nudges and respect the swap cost, especially for heroes the player has little time on.

## Fact-check pass (2026-11-14)
These sources were checked a second time: patch notes 2026/02, 2026/10 and 2026/11; the Sombra, Cassidy, D.Mon and Doctrine hero pages; the counterwatch.gg Sombra, Roadhog and Cassidy pages; the counterwatch.gg swap-after-death blog; the esports.gg counter table; and the Mobalytics Vendetta, Sierra and Sombra guides.
- Confirmed: the patch numbers listed above; the four counterwatch.gg rating sets checked, copied exactly; the swap blog figures (3,459,694 swaps, -2.5, 3.1%, -1.80 vs -3.89, -0.48 vs -3.94, -5.10 vs -1.80); the sub-role passive numbers; D.Mon is Stalwart and Doctrine is Survivor (hero pages); Deliverance lowers enemy maximum health; Mobalytics names Flashbang against Vendetta and says to break Sierra's Anchor Drone.
- Fixed: 14 reasons said Cyberspace Weaken "halves" damage and healing. Since 2026-11-03 it reduces them by 40%. The Wrecking Ball reason gave EMP "20% of his current health", but the official page gives no percentage, so the number was removed. "Roadhog one-combos Tracer" did not account for the 2026-10-06 hook nerf and has been reworded. Mauga > D.Va was removed: neither stats nor a guide backed it, and esports.gg says the reverse. Winston > Sombra and Echo > Sombra were added (Mobalytics Sombra guide). The counterwatch.gg ratings were labelled 5v5. Their own pages say all game types.
- Open conflicts where JSON follows counterwatch.gg stats against the esports.gg table: Cassidy > Tracer (esports.gg says Tracer counters Cassidy), Orisa > Winston, Torbjorn > Winston, Symmetra > Zarya, Ramattra > Hazard, Venture > Sombra, Baptiste > Sombra, Moira > D.Va. Lucio > Sombra follows Mobalytics, though esports.gg says the reverse. esports.gg gives no reasons, so treat these as low confidence.
- esports.gg lists 38 counter pairs that are not in `matchups` (for example D.Va > Winston, Sombra > Orisa, Widowmaker > Mercy). They were not added, because no mechanism was checked for them.
- Unverified: Cassidy's Flashbang. The official Cassidy page does not list it as a base ability, and "hinder" comes only from Stadium/perk text. The 25% swap ult retention also remains unverified for 2026.

## Round 2 data fixes (2026-11-14)
- Removed "Reinhardt beats Zarya: hammer swings into bubbles gain her little". It is false: hammer swings and Fire Strike into her bubbles are exactly what build Zarya's charge. No source backed it, so the pair is now neutral.
- Added D.Va > Mauga (esports.gg names D.Va against Mauga; Defense Matrix eats his chaingun fire) and a new `top_answers` key that makes D.Va the first tank answer to Mauga, ahead of Sigma's Kinetic Grasp.
