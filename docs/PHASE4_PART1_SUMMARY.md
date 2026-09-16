# Phase 4, Part 1 Summary: Walk-Forward Validation

Status: COMPLETE (Phase 4 overall is not - see "What's left" below)
Date: 2026-09-16

## What was built

- `src/schedule_weeks.py` - a continuous week index per season, spanning
  regular season and postseason, needed so every model can be fit on
  "this season's games so far" with zero future leakage. Uses nflverse's
  own week numbers for 1999-2025; infers week boundaries from date gaps
  for 1970-1998 (no week column in that source).
- `src/walkforward.py` - the core validation harness: for every season,
  for every week from the second onward, each batch model (Massey,
  Bradley-Terry, Bayesian) refits on only that season's earlier weeks and
  predicts the next one. Elo needs no special handling - it was already
  leakage-free per game. This replaces Phase 2's within-season 5-fold CV,
  which let later weeks inform predictions for earlier ones in the same
  fit.
- `src/run_phase4_validation.py` - re-selects Bradley-Terry's REG_STRENGTH
  honestly (on 1970-1998 only, before ever touching 1999-2025 - the
  constant landed on exactly Phase 2's value, 3.0, which is reassuring
  rather than suspicious), then runs the full 56-season walk-forward and
  writes `docs/PHASE4_WALKFORWARD_VALIDATION.md`.

## Three real bugs, found by this validation and fixed, not papered over

Fable's pre-Phase-4 review (see BUILD_PLAN.md's decision log) flagged one
open item - the Bradley-Terry tuning leak - and recommended the general
practice of a second pass before an irreversible step. That practice paid
for itself again here: the first full run of this exact validation showed
Massey and the Bayesian model with log loss above 1.0, worse than a coin
flip. Chasing that down surfaced three distinct, real problems, not one:

1. **Floating-point noise, not a real uncertainty estimate.** A model fit
   on very few games can have near-zero residual sigma from pure
   floating-point roundoff (~1e-15), and dividing a rating gap by that
   turns noise into an arbitrary, unstable win probability. Fixed with a
   documented floor (`models/common.py:MIN_SIGMA`) far below any real
   value (full-season sigmas run 10-13).
2. **Missing parameter uncertainty.** The bigger issue: using a model's
   flat in-sample sigma ignores uncertainty in the fitted ratings
   themselves, which is large early in a season and shrinks as games
   accumulate. Fixed properly, not by raising the floor further: added
   `models/common.py:predictive_sigma`, the standard OLS/ridge
   prediction-interval formula (residual variance plus `x'Cov(beta)x`),
   using each model's actual posterior/parameter covariance. Both
   `evaluate.py` (Phase 2) and `walkforward.py` (Phase 4) now use it.
3. **LOO-selected shrinkage backwards on tiny samples.** Fit on a single
   week's ~13-16 games, the Bayesian model's leave-one-out alpha
   selection picked alpha=0.012 - essentially no shrinkage - versus
   2.4-16.7 for every full-season fit. That's backwards: less data should
   mean more trust in the prior, not less; LOO on that few games isn't a
   reliable guide. Fixed with `models/bayesian_margin.py:MIN_ALPHA`,
   floored just below the smallest alpha any real full-season fit has
   ever needed.

## A fourth finding that was reported, not fixed

Even after all three fixes, Massey's early-week log loss remained high
(week 2-5: 2.786 vs. ~0.68-0.69 for the other three). This is not a bug:
the first league-wide week of every season is a set of isolated
head-to-head pairs (no team has played a second opponent yet), so the
schedule graph is disconnected, and two teams' relative rating gap isn't
just uncertain - the data says literally nothing about it. Unregularized
least squares (`lstsq`/`pinv`) resolves that the way it always resolves a
rank-deficient system: the minimum-norm solution, which reports *zero*
uncertainty in exactly the direction with no information, producing
confident, frequently-wrong predictions. Regularized models don't have
this failure mode - it's a structural property of plain OLS, not
something to patch, and it's genuine evidence for the plan's stated
preference for the Bayesian model. `models/common.py:is_schedule_connected`
now measures this directly, and `docs/PHASE4_WALKFORWARD_VALIDATION.md`
breaks results down by week range to show Massey converging to match the
other models only around week 11.

## Headline result

The Bayesian model has the lowest log loss in every slice of both Phase
2's report and this one - the full history, both source-boundary halves,
the connected-only subset, and every week-range bucket but one (a
statistically meaningless 0.002 tie with Massey at week 11+). That
result surviving a considerably stricter, structurally different test is
much stronger evidence than either report alone. Elo and Bradley-Terry
swap second/third place depending on the slice - not a stable enough
ordering to read anything into.

Full numbers in `docs/PHASE4_WALKFORWARD_VALIDATION.md`.

## What's left before Phase 4 is done

Per BUILD_PLAN section 8, Phase 4's full deliverable is out-of-sample
results (done, this document) *plus* a spread comparison *plus* an
adversarial audit, with the model family locked at the end. Two pieces
remain:

1. **Spread comparison** - needs acquiring historical closing point
   spreads (roughly 1979+, per BUILD_PLAN section 7). This needs a
   source and license check before anything is ingested into a public
   repo, the same standard Phase 1 applied to FiveThirtyEight and
   nflverse - paused for Brian's input before proceeding.
2. **Adversarial audit and the model-family lock** - BUILD_PLAN reserves
   this decision for Brian and the coordinating session, not an
   automated report (see the decision log entry on 2026-09-16 about
   model-selection decisions). This session can produce the audit and a
   recommendation, not a final lock.
