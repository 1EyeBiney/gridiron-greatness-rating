# Response to the outside review of v1.0

Date: 2026-09-21. The review is archived verbatim in
[REVIEW_GPT_2026-09-21.md](REVIEW_GPT_2026-09-21.md). Every point below was
checked against the code and data before anything was changed. Where the
reviewer was right, the fix is described and the page it landed on is named.
Where a point was deferred, the reason is given.

## Verdicts in one table

| # | Reviewer's point | Verdict | Action |
|---|---|---|---|
| 1 | QB leaderboard "explosive-pass rate per dropback" actually divided the **team's** explosive plays (rushes included) in games the starter started by the team's dropbacks | **Correct.** Reproduced: Purdy 349 / 1,501 = 23.25% | Rebuilt from play-by-play; see below. Correction note printed on the leaderboard page |
| 2 | 894 team-games dropped from the QB join; all Rams / Chargers / Raiders; team-code mismatch, not thin QB ids | **Correct.** Reproduced: 894 unmatched, all LV / LAC / LAR | Join on franchise via the crosswalk. Coverage 13,928 of 13,928, written to `qb_join_coverage.csv` and tested |
| 3 | "Explosive plays travel with the quarterback" not established; continuity is confounded | **Correct** | Re-run on the corrected measure and join. Prose reduced to "persists more when the same starter returns", stated as an association; the two intervals overlap and the site says so |
| 4 | Stadium and fan-base effects are different questions; the swing is not a venue estimate | **Correct** | New "What the swing is not" section on the franchise page; Denver example; recipe for a venue study; fan-vs-venue distinction |
| 5 | 2020 crowd claim too strong; 2019 was already near zero; other things changed in 2020 | **Correct.** 2019: -0.07 ± 0.74; 2020: +0.10 ± 0.72 | Rewritten on venues, story and front pages as consistent with a crowd effect, not proof; the missing within-2020 test is named |
| 6a | Explaining a completed game vs predicting the next one | **Correct** | Methodology limitation added; the playoff regression is labelled as the one forecast |
| 6b | "More repeatable" vs "more skillful" needs a quantified noise model | **Correct** | New reliability decomposition (below) |
| 6c | "No detectable effect" vs "no effect" | **Correct** | Ranges reported where coefficients are near zero; "shows up" became "shows up detectably" |
| 6d | Playoff elimination labels are approximate | **Correct** | Methodology and both pages that lean on the label now say so |
| 6e | Cross-era z-scores measure dominance relative to one's league, not who would win | **Correct** | Main-site methodology and story page reworded |
| 6f | Uncertainty in ranks and comparisons | **Partly addressed** | TSR standard errors were already shown; rank ranges are deferred |
| 7 | EPA described as win probability | **Correct** | Fixed; EPA is expected points added, WPA is a different field |

## What changed in Explosive Edge

### The quarterback measure

Three measures are now reported and kept apart, as the reviewer proposed:

- **Passing explosiveness**: the quarterback's own completions of 20 or more
  yards divided by his own dropbacks (attempts, sacks taken, scrambles),
  credited play by play from `passer_player_id` (attempts and sacks) and
  `rusher_player_id` on `qb_scramble` plays. A companion column gives the
  share of those completions that travelled 20 or more yards in the air
  (`air_yards`, available from 2006).
- **Quarterback rushing explosiveness**: scrambles and designed runs by the
  same player, 10 or more yards per rush.
- **Team offensive explosiveness**: the existing leaderboard of all
  explosive plays over all scrimmage plays.

Corrected results (regular season 1999-2025, min 1,500 dropbacks):

| Rank | Quarterback | Dropbacks | Explosive completions | Rate |
|---|---|---|---|---|
| 1 | Brock Purdy | 1,515 | 181 | 11.9% |
| 2 | Jimmy Garoppolo | 2,124 | 209 | 9.8% |
| 3 | Jared Goff | 5,622 | 546 | 9.7% |
| 4 | Kurt Warner | 4,280 | 414 | 9.7% |
| 5 | Jordan Love | 1,663 | 160 | 9.6% |

Purdy's 2023 (72 of 486, 14.8%) is the best single season on the corrected
measure, ahead of Nick Foles 2013 and Kurt Warner 2001. The reviewer's
"Purdy might still rank highly" is borne out: on the measure the label
described, he ranks first. Where the yards come from is now a column, not a
guess: about 40% of his explosive completions travelled 20+ yards in the
air, against roughly 45-55% for Rivers, Manning, Romo and Wilson.

The old measure ranked Lamar Jackson first because it counted his team's
explosive rushes. On the pass-only measure the top of the list is no longer
"quarterbacks who threaten with their legs first", and that sentence is gone.

### The join

`build_qb_team_game` maps both files' team codes to franchise ids through the
same crosswalk the rest of the study uses and joins on `(game_id, franchise)`.
A synthetic test now uses `STL` in the schedule and the Rams' franchise id in
the aggregate; a real-data test asserts zero unmatched team-games.

### Continuity

On the corrected measure and full join, the year-to-year correlation of team
explosive-pass rate is 0.24 (95% interval 0.15 to 0.32, n = 514) when the
primary starter returns and 0.13 (0.02 to 0.24, n = 315) when he changes.
The intervals overlap. The site says: persists more with the same starter;
consistent with the passer carrying some of it and with the scheme,
receivers and coordinator he keeps carrying it; not randomly assigned; the
four-way design (departing and receiving team, before and after each move)
has not been built. A site fact, `qb_continuity_ci_overlap`, gates the
overlap sentence so it disappears if the data ever separate.

### Rarity versus skill, quantified

`reliability_decomposition.csv`: for each era and metric, the between-team
variance of half-season per-game differentials, the variance Poisson
counting noise would produce around fixed rates, and the remainder. The
remainder's share is the split-half correlation a noise-only world would
show.

| Era 2017-2025 | Noise-only reliability | Observed split-half r |
|---|---|---|
| Explosive differential | 0.45 | 0.42 |
| Turnover differential | 0.33 | 0.18 |

Explosive differential sits at its noise-only ceiling. Turnover differential
sits well below its own, which means its between-team spread within a
season is inflated by something beyond counting noise that does not carry
over: luck, in the ordinary sense. Rarity explains about 46% of the gap
between the two metrics' persistence; the rest is that. Interceptions,
fumbles and recoveries are pooled; splitting them is future work.

### Words

- "predicts nothing" became "no detectable effect", with the ±2 SE range
  (turnover coefficient -0.02 ± 0.12, range -0.26 to +0.21).
- Methodology now separates in-sample description from the one forecast.
- EPA is expected points added; the EPA variant softens the yardage tautology
  rather than removing it.

## What changed in Home Field Advantage

- **2020.** The venues page, the story page and the front page now report
  2020 (+0.10 ± 0.72) beside 2019 (-0.07 ± 0.74), note the cancelled preseason,
  restricted practice and city-by-city attendance limits, and call the
  empty season consistent with a crowd effect rather than proof. The section
  title "The season that proved the crowd matters" is now "The season with no
  fans". The missing test (games under different attendance limits within
  2020, allowing for venue and team) is named as not done.
- **Swing versus venue.** New section on the franchise page. Denver's
  6.5-point swing is home minus road across two stadiums and 55 seasons, not
  a Mile High estimate. A venue study would need stadium-by-era effects with
  shrinkage, travel/rest/altitude/roof controls, out-of-sample persistence
  and a joint test before ranking; even then it would answer "which venues"
  and not "which fans".
- **Detectability.** Each swing is measured to about ±0.82 points (median
  standard error), so a road effect of roughly a point per game would hide
  inside the noise for most franchises. "No fan base shows up" is now
  "nothing detectable shows up".
- **Labels.** "Eliminated" is a conference-wide, tiebreaker-free
  approximation; said so on the methodology page and where the label is used.

## What changed on the main site

- Methodology: a within-season z-score compares a team with its own league;
  equal z-scores in 1985 and 2019 mean equal dominance relative to
  contemporaries, not a prediction of a neutral-field result, and the model
  cannot see league depth.
- The story page's introduction says the same in one sentence.
- How It Was Made gained a section on this review.

## Deferred, with reasons

| Item | Why not now |
|---|---|
| Four-way QB-move study (departing and receiving team, before and after; relaxed starts rule; leave-one-out) | A new analysis with its own design choices; the corrected measure and the exploration's 56-move sketch are the starting point. Should be planned with Brian rather than bolted on |
| Within-2020 attendance test | Needs per-game attendance-limit data by venue and date, which the project does not have |
| Stadium-by-era venue model | A separate study; the recipe is on the franchise page |
| Rank uncertainty ranges on the main site | Worth doing; needs posterior draws rather than standard errors alone. Not a correction, so deferred |
| The reviewer's headline question: does explosiveness add forward predictive value beyond team strength, opponents and ordinary efficiency? | The right next study for Explosive Edge. Natural design: walk-forward prediction of second-half or next-season results with and without explosive rates, given TSR-style strength. Logged in the study's notes |
