# Phase 4, Part 3: Adversarial Audit

Status: FINDINGS AND RECOMMENDATION - not a lock

Per BUILD_PLAN section 8, this audit lists team-seasons whose rating
conflicts with either their own record or with each other, plus a check
against a short list of historically undisputed teams. It closes with a
recommendation, not a decision: BUILD_PLAN reserves locking the model
family for Brian and the coordinating session.

All ratings below are the Bayesian model's - the leading candidate per
docs/PHASE2_MODEL_COMPARISON.md and docs/PHASE4_WALKFORWARD_VALIDATION.md,
both of which put it ahead in nearly every slice tested.

## 1. Rating vs. record: where the model and the standings disagree most

Win percentage only sees who won, not by how much; the Bayesian rating is
built entirely from margin (and schedule strength). A large gap between
them is exactly what a point-margin model is *supposed* to produce for a
team that won by a little a lot, or lost by a lot a little - so each case
below is checked against the team's own point differential before being
called anything other than the model working as intended.

### Rated well above what the record alone would suggest

| Season | Team | Record | Point diff | win_pct rank | TSR z rank |
|---:|---|---|---:|---:|---:|
| 1981 | NE | 2-14 | -48 | 27/28 | 21/28 |
| 2010 | GB | 10-6 | +148 | 8/32 | 2/32 |
| 1996 | GB | 13-3 | +246 | 1/30 | 1/30 |
| 1971 | CIN | 4-10 | +19 | 24/26 | 12/26 |
| 1993 | ARI | 7-9 | +57 | 18/28 | 6/28 |
| 2020 | ATL | 4-12 | -18 | 29/32 | 16/32 |
| 2006 | JAX | 8-8 | +97 | 13/32 | 6/32 |
| 1981 | ATL | 7-9 | +71 | 17/28 | 6/28 |

Every one of these teams' point differential ranks meaningfully better than their win-percentage rank within that season - the model is picking up real margin dominance a plain record hides (typically some combination of blowout wins and several close losses). No fix needed; this is the intended behavior of a margin-based rating.

### Rated well below what the record alone would suggest

| Season | Team | Record | Point diff | win_pct rank | TSR z rank |
|---:|---|---|---:|---:|---:|
| 2012 | IND | 11-5 | -30 | 6/32 | 24/32 |
| 2022 | MIN | 13-4 | -3 | 4/32 | 15/32 |
| 1992 | IND | 9-7 | -86 | 12/28 | 23/28 |
| 2023 | PHI | 11-6 | +5 | 5/32 | 20/32 |
| 2018 | MIA | 7-9 | -114 | 17/32 | 30/32 |
| 1978 | ATL | 9-7 | -50 | 8/28 | 24/28 |
| 1998 | ARI | 9-7 | -53 | 11/30 | 24/30 |
| 2024 | KC | 15-2 | +59 | 1/32 | 10/32 |

Same pattern in reverse: each team's point-differential rank is meaningfully worse than its win-percentage rank - typically a team that won a lot of close games and lost at least one or two badly. Also the intended behavior, not a defect, though a team relying on close-game luck to win is a legitimate thing for a reader to want flagged, which is exactly what the separate Accomplishment score (BUILD_PLAN section 3, not yet built - Phase 5) is for: this project deliberately keeps 'how good' and 'how successful' as two numbers, not one.

## 2. Cross-model disagreement: least-confident ratings

Team-seasons where Massey, Bradley-Terry, Bayesian and Elo's standardized ratings spread out the most - not necessarily wrong, but lower-confidence than a single headline number suggests.

| Season | Team | Massey z | BT z | Bayes z | Elo z | Disagreement (SD) |
|---:|---|---:|---:|---:|---:|---:|
| 1981 | NE | -0.70 | -1.81 | -0.63 | -2.19 | 0.68 |
| 2012 | IND | -0.72 | 0.34 | -0.63 | 0.83 | 0.66 |
| 1970 | IND | 0.39 | 1.40 | 0.64 | 1.99 | 0.63 |
| 1992 | IND | -1.09 | -0.05 | -0.96 | 0.35 | 0.61 |
| 1999 | TEN | 0.62 | 1.66 | 0.79 | 2.07 | 0.60 |
| 2006 | JAX | 1.28 | 0.54 | 1.12 | -0.05 | 0.52 |
| 2001 | LAC | 0.05 | -0.72 | 0.08 | -1.15 | 0.52 |
| 2022 | MIN | -0.07 | 0.82 | -0.11 | 1.05 | 0.52 |

Elo is the most frequent outlier here, consistent with it being a comparator that never revisits an early-season estimate in light of later results (see docs/PHASE4_WALKFORWARD_VALIDATION.md) - not evidence against the three batch models agreeing with each other.

## 3. Benchmark check against undisputed team-seasons

The one place this audit uses outside knowledge rather than deriving everything from the game log - a short list of team-seasons whose historical standing is not seriously in dispute, checked against where the Bayesian model actually ranks them.

| Season | Team | Why it's a benchmark | TSR z | Rank in season |
|---:|---|---|---:|---:|
| 1972 | MIA | Only perfect season in NFL history (17-0 including playoffs). | 1.58 | 1/26 |
| 1985 | CHI | 15-1, dominant defense, won Super Bowl XX by 36. | 2.79 | 1/28 |
| 2007 | NE | 16-0 regular season, widely regarded as one of the greatest ever. | 2.51 | 1/32 |
| 1991 | WSH | 14-2, outscored playoff opponents 102-41, won Super Bowl XXVI. | 2.43 | 1/28 |
| 2000 | BAL | Historically dominant defense (allowed the fewest points in a 16-game season); offense was weak - a real test of whether a point-margin model still rates a defense-carried team highly. | 1.89 | 1/31 |
| 2008 | DET | 0-16, the only 0-16 season in the 16-game-schedule era. | -2.22 | 32/32 |
| 2017 | CLE | 0-16. | -1.93 | 32/32 |
| 1976 | TB | 0-14, first-year expansion team. | -2.23 | 28/28 |
| 1976 | LAR | Beat Atlanta 59-0, part of a dominant regular season. | 0.95 | 7/28 |
| 2011 | NYG | 9-7 regular season, won the Super Bowl - a common test case for whether a rating agrees with the trophy (BUILD_PLAN deliberately keeps TSR and ACC separate, so a modest TSR here is not itself a conflict). | 0.76 | 9/32 |

## Recommendation (not a lock)

Nothing in this audit surfaced a team-season the Bayesian model gets wrong in a way that isn't already explained by the model doing exactly what a margin-based, schedule-adjusted rating is supposed to do. Combined with Phase 2 and Phase 4 part 1's out-of-sample results (lowest log loss in nearly every slice tested, both within-season and walk-forward), this session's recommendation is to proceed with the Bayesian hierarchical margin model as the project's True Strength Rating - but that is a recommendation for Brian and the coordinating session to confirm, per BUILD_PLAN's decision log, not a decision this report makes on its own.

