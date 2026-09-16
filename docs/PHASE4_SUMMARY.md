# Phase 4 Summary: Validation

Status: PARTIAL - out-of-sample validation and adversarial audit complete; spread comparison deferred by Brian's decision (see below)
Date: 2026-09-16

## What was built

- **Part 1: walk-forward validation** (`docs/PHASE4_PART1_SUMMARY.md`,
  `docs/PHASE4_WALKFORWARD_VALIDATION.md`). Replaced Phase 2's
  within-season 5-fold CV with genuine walk-forward validation - every
  model refits weekly using only that season's earlier games, zero
  future leakage. Building this surfaced and fixed three real bugs
  (floating-point-noise uncertainty, missing parameter uncertainty in
  win-probability predictions, backwards shrinkage selection on tiny
  samples) and one structural, unfixed finding (unregularized Massey is
  unreliable for the first ~10 weeks of a season because the schedule
  graph starts disconnected). Bradley-Terry's REG_STRENGTH was
  re-selected honestly and landed on exactly Phase 2's value.
- **Part 2: spread comparison - deferred.** BUILD_PLAN section 7 calls
  for historical closing point spreads (roughly 1979+) to compare model
  predictions against the market. Every free bulk dataset found traces
  back to sources with redistribution restrictions (spreadspoke.com's
  Terms of Use, which the popular Kaggle mirror is built from, prohibits
  resale/redistribution without permission) - the same kind of
  provenance gap Phase 1 hit with Pro Football Reference, which is why
  PFR was used there only as a hand-checked reference, never a bulk
  source. Given that, Brian chose to skip the spread comparison for now
  rather than pursue a hand-verified sample or a source of his own.
  Phase 4 remains open on this point; it can be picked up later without
  disturbing anything else.
- **Part 3: adversarial audit** (`docs/PHASE4_ADVERSARIAL_AUDIT.md`).
  Three checks against the Bayesian model (the leading candidate):
  rating-vs-record residuals computed entirely from the game log (a
  team rated well above or below what its win percentage alone would
  suggest, explained by margin of victory/defeat - not a defect, the
  intended behavior of a margin-based rating); cross-model disagreement
  (which team-seasons the four models least agree on - Elo is the most
  frequent outlier, expected since it never revisits an early estimate);
  and a benchmark check against ten team-seasons whose historical
  standing isn't seriously disputed. Every benchmark landed where
  expected, including the two most demanding cases: the 2000 Ravens
  (defense-carried, weak offense) still rank #1 in their season, and the
  2011 Giants (a Super Bowl champion with a merely 9-7 regular season)
  rank a believable 9th of 32 - exactly the gap BUILD_PLAN's separate
  True Strength / Accomplishment scores are designed to show, not close.

## Recommendation, not a lock

Across Phase 2's within-season CV, Phase 4's walk-forward CV, and this
audit, nothing surfaced that argues against the Bayesian hierarchical
margin model as the project's True Strength Rating, and several things
argue for it (lowest log loss almost everywhere tested, correct
behavior on every adversarial benchmark, standard errors as a byproduct
of the same regularization that keeps it stable early in a season). This
session recommends proceeding with it - but per BUILD_PLAN's decision
log, locking the model family is a decision for Brian and the
coordinating session, not something this report finalizes on its own.

## What's carried forward

- Spread comparison (deferred, see above).
- The three pre-existing small items: pre-1999 playoff round labels,
  team-season conference/division table (both Phase 5), and nothing
  further on Bradley-Terry's REG_STRENGTH, now resolved.

## Recommended next step

Confirm (or revisit) the model-family recommendation above, then start
Phase 5: Accomplishment score, Conference Strength Index, and full
team-season profiles with descriptive sub-scores, per BUILD_PLAN
sections 3 and 8.
