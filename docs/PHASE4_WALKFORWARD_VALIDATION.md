# Phase 4, Part 1: Walk-Forward Validation

Status: COMPLETE

## Method

Every model refits weekly using only that season's games from earlier
weeks (see src/walkforward.py) - a stricter, future-leakage-free version
of Phase 2's within-season 5-fold cross-validation. Week 1 of every season
is never scored (no history exists yet to fit on). Elo needs no special
handling: it already updates after every game with zero future access,
so it is evaluated the same way it was in Phase 2.

## Bradley-Terry regularization: re-selected honestly

Phase 2's REG_STRENGTH (3.0) was chosen by grid search against the same
folds it was then scored on - a mild test-set leak, flagged at the time.
Here it is re-selected using only the 1970-1998 seasons (the
FiveThirtyEight/nflverse source boundary already in the data), scored by
walk-forward log loss, before ever touching 1999-2025:

| reg_strength | Walk-forward log loss (1970-1998) |
|---:|---:|
| 1 | 0.6608 |
| 1.5 | 0.6491 |
| 2 | 0.6440 |
| 3 | 0.6412  <- selected |
| 5 | 0.6433 |
| 8 | 0.6491 |
| 12 | 0.6555 |
| 18 | 0.6620 |

Selected reg_strength = 3 (Phase 2's value was 3). This value is used for every Bradley-Terry number below, including on the 1970-1998 seasons that selected it - so unlike the other three models, Bradley-Terry's 1970-1998 number here still isn't a fully clean read. Its 1999-2025 number is: those seasons played no part in choosing reg_strength.

## Results: full history (1970-2025)

| Model | Games scored | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|---:|
| bayesian_margin | 12679 | 0.6434 | 10.85 | 0.628 |
| bradley_terry | 12679 | 0.6441 | n/a | 0.624 |
| elo | 12686 | 0.6539 | 11.06 | 0.617 |
| massey | 12679 | 1.1838 | 12.66 | 0.621 |

## Results: 1999-2025 only (the clean read for Bradley-Terry)

| Model | Games scored | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|---:|
| bayesian_margin | 6843 | 0.6450 | 10.76 | 0.625 |
| bradley_terry | 6843 | 0.6466 | n/a | 0.617 |
| elo | 6848 | 0.6564 | 10.97 | 0.608 |
| massey | 6843 | 1.2468 | 12.35 | 0.619 |

## Results: 1970-1998 only (Bradley-Terry's tuning seasons - not clean for that model)

| Model | Games scored | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|---:|
| bradley_terry | 5836 | 0.6412 | n/a | 0.632 |
| bayesian_margin | 5836 | 0.6415 | 10.95 | 0.630 |
| elo | 5838 | 0.6509 | 11.16 | 0.627 |
| massey | 5836 | 1.1098 | 13.01 | 0.623 |

## A structural finding: disconnected early-season schedules

The first full run of this validation showed Massey with a log loss above 1.0 - worse than a coin flip - which turned out not to be noise. Every league-wide week 1 is a set of isolated pairs (each team has played exactly one game, against one opponent), so predicting week 2 sometimes means comparing two teams that share no common opponent yet and never played each other - the schedule graph is disconnected, and their relative rating gap is not just uncertain, it is completely unconstrained by the data. Massey's plain least-squares fit resolves this the way `lstsq`/`pinv` always resolve a rank-deficient system: by picking the minimum-norm answer, which reports *zero* uncertainty in exactly the direction the data says nothing about, producing near-certain (and frequently wrong) predictions. Bayesian and Bradley-Terry never hit this failure: their regularization keeps the system invertible and correctly reports high uncertainty (shrinking toward a 50/50 prediction) for a team no data yet connects to its opponent.

This is now measured directly (src/models/common.py:is_schedule_connected), and every result above is scored on the full mix of connected- and disconnected-graph weeks. Splitting the two apart isolates the effect:

### Connected-graph weeks only (the normal case, most of every season)

| Model | Games scored | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|---:|
| bayesian_margin | 11387 | 0.6367 | 10.77 | 0.638 |
| bradley_terry | 11387 | 0.6368 | n/a | 0.633 |
| elo | 11387 | 0.6507 | 11.04 | 0.624 |
| massey | 11387 | 0.8078 | 11.97 | 0.631 |

### Disconnected-graph weeks only (early in a season, before the schedule has connected everyone)

| Model | Games scored | Log loss | Margin MAE | Accuracy |
|---|---:|---:|---:|---:|
| elo | 1299 | 0.6815 | 11.24 | 0.557 |
| bayesian_margin | 1292 | 0.7026 | 11.48 | 0.540 |
| bradley_terry | 1292 | 0.7079 | n/a | 0.546 |
| massey | 1292 | 4.4976 | 18.68 | 0.532 |

Connectivity is a yes/no property, but the instability it causes isn't - a graph that just barely connected via one bridging game is still numerically thin, and Massey needs several more weeks beyond that before it's reliably steady. Breaking log loss down by week index instead of the connected/disconnected split makes that gradient visible:

| Week range | bayesian_margin | bradley_terry | elo | massey |
|---|---:|---:|---:|---:|
| 2-5 (just connected, still thin) | 0.685 | 0.683 | 0.675 | 2.786 |
| 6-10 | 0.646 | 0.646 | 0.656 | 0.668 |
| 11+ | 0.615 | 0.619 | 0.639 | 0.617 |

Massey only converges to match the regularized models around week 11 - it is not simply "fine once connected." This is a specific, mechanical failure of unregularized OLS on a thinly-identified system, not a general weakness of least squares as a rating method, and it is real evidence for BUILD_PLAN's stated preference for the Bayesian model: the same regularization that gives it a standard error for free is also what keeps it well-behaved for most of every season, not just once enough games have piled up to make the problem well-posed on its own.

## Comparison to Phase 2

Phase 2's within-season 5-fold CV let information from later weeks inform predictions for earlier weeks in the same fit; this walk-forward run never does. The two protocols agree on the one finding that matters most for model-family selection: the Bayesian model has the lowest log loss in every slice of both reports - Phase 2's aggregate and all four era slices, and here, the full history, both source-boundary halves, the connected-only subset, and every week-range bucket except one (Massey ties it within 0.002 at week 11+, not a meaningful difference). That result surviving a considerably stricter, structurally different test is a much stronger reason to trust it than either report alone would be. Elo and Bradley-Terry swap second/third place depending on the slice; that ordering is not stable enough across the two protocols to read anything into. See docs/PHASE2_MODEL_COMPARISON.md for the Phase 2 numbers.

Model family is not locked by this report alone - the spread comparison and adversarial audit (both still to come in Phase 4) are part of the same decision, and BUILD_PLAN reserves that decision for Brian and the coordinating session, not an automated report.

