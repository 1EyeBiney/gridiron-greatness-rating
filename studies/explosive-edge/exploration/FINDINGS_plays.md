# Explosive Edge -- Play-Level Exploration Findings

Regular season only, 1999-2025 (where data present). Runtime: 4.1s.

## Q1. Pass vs run explosives

**The 2018-2025 decline in explosive plays is mostly a passing-game decline, not a rushing decline or a mix (falling pass rate) effect** -- the per-dropback explosive-pass rate fell from 0.0832 to 0.0785 (-5.7%) while the per-attempt explosive-rush rate barely moved (0.1268 -> 0.1120, -11.7%).

- Explosive passes/team-game: 3.21 (2018) -> 2.86 (2025); explosive rushes/team-game: 3.20 -> 2.92.
- Rush share of all explosive plays (20/10 def): 49.9% (2018) -> 50.5% (2025); stricter 25/15 def: 44.1% -> 42.6%.
- Decomposition of the change in league-wide explosive-plays-per-scrimmage-play, 2018->2025: total 0.1029 -> 0.0955 (-0.0074). Mix effect (falling pass rate, 59.5% -> 56.9%): +0.0009. Within-type rate effect (passes and rushes each getting less explosive per attempt): -0.0083. The rate effect is the larger of the two (~90% of the combined magnitude), so **falling pass rate explains only a minority of the decline** -- it is mostly that pass plays (and to a lesser extent rushes) are individually less likely to go for 20+/10+ than they were in 2018, not that the league is running the ball more.

- Caveat: this decomposition uses a simple two-term (midpoint-weighted) mix/rate split on a single before/after pair (2018, 2025); it is not a full trend regression and a different endpoint pair could shift the split modestly. Both explosive-play definitions (20/10 primary, 25/15 strict) agree on direction. See `q1_pass_run_explosives_by_season.csv` for the full 1999-2025 series and `q1_decomposition_2018_2025.csv` for the decomposition.

## Q2. Situational

**Explosive rate rises with down (3rd+ is highest) and with distance-to-goal getting shorter (red zone lowest), and the 'more early-drive shot-taking now' prediction is not borne out** -- play-1-of-drive explosive rate is 0.104 (2010-2017) vs 0.110 (2018-2025), a small change and not obviously larger than the change on later-drive plays.

- By down, 2018-2025: 1st 0.104, 2nd 0.094, 3rd+ 0.094 (full down x distance x zone x score x quarter breakdown, both eras, in `q2_situational_explosive_rate.csv`).
- By play-in-drive, explosive rate: 1st 0.104->0.110, 2nd 0.100->0.102, 3rd 0.106->0.109, 4th+ 0.089->0.090.
- Garbage time (wp outside [0.05,0.95]) explosive rate vs competitive time: 2010-2017 0.091 vs 0.097; 2018-2025 0.092 vs 0.099 -- garbage time is consistently more explosive (trailing teams throw downfield), in both eras.
- Share of all explosive plays occurring in garbage time ranges 12.4%-18.1% across 2010-2025 (season series in `q2_garbage_share_of_explosives_by_season.csv`); no strong trend, see CSV for year-by-year.

- Caveat: score-state buckets are 5-way (trailing >7 / trailing 1-7 / tied / leading 1-7 / leading >7), a finer split than the brief's literal 3-way wording, kept because it is more informative and the 3-way collapse is a simple re-group of the CSV. Field zones use yardline_100 (distance to opponent's end zone): own 1-20 = 80-99, own 21-50 = 50-79, opp 49-21 = 21-49, red zone = 0-20.

## Q3. Where they come from, offense vs defense

**The league is homogenizing on offense (between-team spread in explosives generated is shrinking) but the top-5-offense share of league explosive plays has not shrunk to match** -- std of explosives-generated/game: 0.974 (1999-2007) -> 0.967 (2008-2016) -> 0.988 (2017-2025); CV (std/mean): 0.171 -> 0.160 -> 0.162.

- Explosives-allowed spread by era: std 0.892 -> 0.936 -> 0.882; CV 0.157 -> 0.155 -> 0.145.
- Top-5-offense share of all league explosive plays, season average by era: 19.9% (1999-2007) / 19.4% (2008-2016) / 19.4% (2017-2025); full season series in `q3_top5_offense_concentration_by_season.csv`.
- Top 10 / bottom 10 team-seasons 2019-2025 by explosives generated per game and allowed per game are in `q3_top10_generated_2019_2025.csv`, `q3_bottom10_generated_2019_2025.csv`, `q3_top10_allowed_2019_2025.csv`, `q3_bottom10_allowed_2019_2025.csv`.

- Caveat: 'homogenizing' here is about the spread in team RATES, which can fall even while the absolute count of explosive plays a top offense produces stays high if the league mean also moved -- read the CV columns (scale-free) alongside the raw std.

## Q4. The defensive mechanism

**The defensive-play-probability curve rises only over the first 2-3 plays of a drive, then goes flat (plays 3 through 8+ sit in the same ~0.095-0.11 band, no further climb) -- so Simms' mechanism has a grain of truth at the very start of a drive but does not describe accumulating danger for a drive that keeps going, in any era.** Play-1 -> play-3 -> play-8+ def-play rate, 1999-2007: 0.093 -> 0.111 -> 0.107; 2008-2016: 0.087 -> 0.106 -> 0.099; 2017-2025: 0.081 -> 0.103 -> 0.099. The shape (rise-then-plateau) is the same in every era; only the level has drifted down slightly, consistent with NOTES.md's per-snap def-play-rate decline.

- Drive-ends-in-turnover probability by drive length (plays, capped at 8+): 1999-2007 0.469 (1 play) / 0.102 (3 plays) / 0.096 (8+ plays); 2017-2025 0.464 / 0.082 / 0.070. This is NOT a clean length-vs-risk read: 1- and 2-play drives are ~47-49% turnovers in every era because a turnover truncates the drive right there (a pick-six or fumble on the opening snap IS a 1-play drive by construction), a selection effect, not rising early danger. Past that artifact the rate is lowest at 3 plays and drifts down further by 8+ in every era -- if anything drives that survive past the first couple of snaps get SAFER for the offense the longer they run, the opposite of Simms' claim. Full table in `q4_turnover_rate_by_drive_length.csv`.

- Per-drive P(>=1 defensive play): 0.459 (1999-2007) -> 0.448 (2008-2016) -> 0.453 (2017-2025). Points per drive (TD=6.95, FG=3, safety=-2, all else 0 -- approximate, no 2pt/XP-miss detail): 1.656 -> 1.836 -> 2.043. Points per drive has risen while P(>=1 def play) per drive has been flat-to-down, so on the whole-drive view too, 'long/more-productive drives score' is better supported than 'long drives are dangerous for offenses.'

- Caveat: the points-per-drive figure is a rough estimate (fixed_drive_result category -> assumed point value), not actual scoreboard deltas; it is directionally fine for this comparison but should not be quoted as an exact PPD number on the site without redoing it from real point deltas. n per drive-length cell shrinks at 8+ (long drives are rarer) but is still in the thousands per era -- see the `drives`/`plays` count columns in the CSVs. The turnover-by-length table in particular should be presented with the selection-effect caveat above if it goes on the site at all.

## Consistency with docs/NOTES.md

- Confirms NOTES.md's mechanism finding and sharpens it: defensive-play rate per snap is flat/falling with drive position within every era (Q4), and long drives score more than they turn the ball over, which is the opposite of what would justify Simms' 'defenses want long drives' claim.
- Adds nuance NOTES.md didn't have: the 2018->2025 explosive-play decline is a *passing* efficiency decline (fewer explosive plays per dropback), not primarily a rushing decline or a pass-rate mix effect (Q1) -- worth stating precisely on the site rather than leaving 'pass rate is falling' to imply the mix change is the main driver.
- Nothing here contradicts NOTES.md; the situational (Q2) and offense/defense-spread (Q3) results are new detail, not previously stated in NOTES.md, so there's nothing to reconcile there.
