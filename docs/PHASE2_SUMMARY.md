# Phase 2 Summary: Baseline and Candidate Models

Status: COMPLETE
Date: 2026-09-16

## What was built

Four rating models, each fit on every game a team played per season -
regular season and postseason, unlike the Phase 1 SRS validation tool
which deliberately matched Pro Football Reference's regular-season-only
convention:

- `src/models/massey.py` - ordinary least squares on blowout-capped
  margin (28-point cap, BUILD_PLAN section 4), with a fitted shared
  home-field term. The direct generalization of Phase 1's SRS.
- `src/models/bradley_terry.py` - logistic win/loss model with a
  margin-aware extension (games are weighted by a damped function of
  their margin, not by margin itself, so the model still targets
  win/loss).
- `src/models/bayesian_margin.py` - a Gaussian-Gaussian hierarchical
  margin model (team ratings shrink toward the league mean); the
  posterior mean is exactly ridge regression and the posterior variance
  is available in closed form, so this model produces a standard error
  per team-season for free. The shrinkage strength is chosen per season
  by leave-one-out cross-validation (empirical Bayes), not fixed by hand.
- `src/models/elo.py` - season-restarted Elo (K=20, home field worth 48
  Elo points, both fixed, published constants from FiveThirtyEight's NFL
  Elo model), included only as a sanity comparator per BUILD_PLAN
  section 5, not a candidate for the headline rating.

`src/evaluate.py` runs the out-of-sample comparison: 5-fold
cross-validation within every season for the three batch models, and a
prequential (no future leakage, ever) walk-forward evaluation for Elo.
`src/run_phase2.py` fits all four models for all 56 seasons and writes
the ratings, fitted parameters, and comparison report.

## A bug the cross-validation caught

The first run of `run_phase2.py` showed Bradley-Terry with a log loss of
0.81 - worse than a coin flip (ln 2 = 0.693). Tracing the worst
cross-validation folds (`docs/PHASE2_MODEL_COMPARISON.md`'s numbers come
from the second, fixed run) showed team ratings as extreme as -34 and
+38 log-odds in a single fold: classic quasi-complete separation, where
a team that goes unbeaten or winless within a small training fold sends
plain logistic-regression MLE to infinity, producing near-0/near-1
predictions that are occasionally catastrophically wrong on held-out
games. This is a well-known failure mode of unregularized logistic
regression on small samples, not a property of Bradley-Terry itself, so
`bradley_terry.py` now adds a small, fixed L2 penalty on team ratings
(the standard fix, in the spirit of Firth's penalized likelihood) - see
that file's docstring for how the penalty strength was chosen. After the
fix, Bradley-Terry's log loss dropped to 0.627, in line with the other
three models.

## Results (full detail in PHASE2_MODEL_COMPARISON.md)

Pooled across all 13,685 games in all 56 seasons:

| Model | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|
| Bayesian hierarchical margin | 0.622 | 10.54 | 0.655 |
| Bradley-Terry | 0.627 | n/a | 0.651 |
| Massey | 0.634 | 10.78 | 0.655 |
| Elo (comparator) | 0.656 | 11.08 | 0.612 |

All three batch candidates land close together and clearly ahead of the
Elo comparator, which is the expected shape of this result: Elo commits
to a rating before seeing any of that season's games, updates once per
game with a fixed step size, and never revisits earlier estimates in
light of later results, while the batch models fit the whole season's
schedule jointly. The Bayesian model is the most accurate by a small
margin in every era slice, consistent with BUILD_PLAN section 5 naming
it the preferred candidate "if it validates" - though this is Phase 2's
first, comparatively easy, out-of-sample test (5-fold within a season),
not Phase 4's real validation (held-out future weeks, spread comparison,
adversarial audit), so no model family is locked in by this report.

Fitted home-field advantage averages 2.42 points per game (SD 0.87
across seasons) for Massey and the Bayesian model - in line with the
commonly cited NFL home-field advantage of roughly 2-3 points, and a
useful independent check that these two models are measuring something
real rather than fitting noise.

As a further sanity check (not a formal metric, since it uses no
information the model didn't already have): the ten highest-rated
team-seasons of the historical era by the Bayesian model are exactly the
teams anyone who follows NFL history would expect near the top,
including the 2007 Patriots, 1985 Bears, 1972 and 1973 Dolphins, 1991
Redskins, 1976 and 1975 Steelers, and 2013 Seahawks - full list in
`data/processed/team_season_ratings.csv`.

## What's carried forward, not fixed here

- Model family selection stays open until Phase 4, per BUILD_PLAN
  section 8.
- The two Phase 1 carry-forwards (pre-1999 playoff round labels; a
  team-season conference/division table) are still outstanding and still
  not blocking - Phase 3 (era normalization) does not need either.
- Bradley-Terry's regularization strength (`REG_STRENGTH` in
  `src/models/bradley_terry.py`) was chosen once by grid search against
  this cross-validation protocol, not re-derived per season. If Phase 4
  changes the validation protocol, it's worth rechecking whether that
  constant still sits near the log-loss minimum.

## Recommended next step

Phase 3: era normalization. Build the standardization layer (z-scores
within season, BUILD_PLAN section 5), and implement the era handling
rules in section 6 - schedule-length normalization, the 1982 and 1987
strike seasons, expansion/realignment, and neutral-site handling (already
partly done: all four models already zero out home-field for neutral
sites). Deliverable per BUILD_PLAN section 8: a sensitivity report
showing how much each rule moves rankings.
