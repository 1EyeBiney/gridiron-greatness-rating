# Phase 2: Candidate Model Comparison

Status: COMPLETE
Seasons covered: 1970-2025 (56 seasons, every game - regular season and
postseason, per BUILD_PLAN section 2).

## Method

Massey (ordinary least squares on blowout-capped margin), Bradley-Terry
(margin-weighted logistic win/loss), and the Bayesian hierarchical margin
model (ridge regression with an empirical-Bayes shrinkage prior) are each
evaluated by 5-fold cross-validation within every season: fit on 4/5 of that
season's games, predict the held-out 1/5, repeat for all 5 folds, and
pool the results. Elo is evaluated prequentially instead (see src/evaluate.py
and src/models/elo.py for why its evaluation is not k-fold), so its numbers
are informative but not from an identical protocol.

Metrics: log loss on the win/loss outcome (ties count as a 0.5 outcome),
mean absolute error on the point margin (undefined for Bradley-Terry, which
only ever targets win/loss), and plain win/decided-game accuracy.

This is Phase 2's first predictive-accuracy look, run to see whether one
model family is obviously and consistently ahead of the others. It is not
Phase 4's validation: no held-out future weeks, no spread comparison, no
adversarial audit, and no model family is locked in by this report.

## Aggregate results (all seasons pooled, game-count weighted)

| Model | Games scored | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|---:|
| bayesian_margin | 13685 | 0.6223 | 10.54 | 0.656 |
| bradley_terry | 13685 | 0.6274 | n/a | 0.651 |
| massey | 13685 | 0.6341 | 10.78 | 0.655 |
| elo | 13685 | 0.6564 | 11.08 | 0.612 |

Lower log loss and margin MAE are better; higher accuracy is better.

## By era (log loss, game-count weighted)

| Era | bayesian_margin | bradley_terry | elo | massey |
|---|---:|---:|---:|---:|
| 1970-1977 (14-game) | 0.5959 | 0.6043 | 0.6482 | 0.6099 |
| 1978-1994 | 0.6328 | 0.6342 | 0.6583 | 0.6430 |
| 1995-2010 | 0.6178 | 0.6248 | 0.6547 | 0.6296 |
| 2011-2025 | 0.6269 | 0.6323 | 0.6596 | 0.6396 |

## Fitted home-field advantage (mean across seasons)

| Model | Mean home_adv | SD across seasons |
|---|---:|---:|
| bayesian_margin | 2.437 points | 0.869 |
| bradley_terry | 0.373 log-odds | 0.148 |
| massey | 2.416 points | 0.866 |

Massey and the Bayesian model fit home-field advantage directly in points; Bradley-Terry fits it in log-odds, so its number is not on the same scale.

## Reading these results

See docs/PHASE2_SUMMARY.md for the interpretation and the recommendation carried into Phase 3.

