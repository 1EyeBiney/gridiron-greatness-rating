# Phase 3 Summary: Era Normalization

Status: COMPLETE
Date: 2026-09-16

## What was built

Full detail and the sensitivity numbers are in
`docs/PHASE3_ERA_NORMALIZATION.md` (this phase's required deliverable).
In short:

- `src/standardize.py` - within-season z-scoring for every model's
  rating, plus an optional 0-100 display scale. Applied in place to
  `data/processed/team_season_ratings.csv` (8 new columns: `*_z` and
  `*_display` for each of the four models).
- `src/era.py` - identifies the 42 specific 1987 games played by
  replacement players (found by looking for the season's date gaps, then
  confirmed against the historical record: strike after week 2, week 3
  cancelled outright, weeks 4-6 played with replacements, regulars back
  for week 7), and a new `data/reference/season_metadata.csv` (team
  count, schedule length, strike flags for every season).
- `src/sensitivity.py` and `src/run_phase3.py` - the two sensitivity
  checks BUILD_PLAN section 6 calls for: 1987 with vs. without the
  replacement games, and confirming 1982 actually gets wider Bayesian
  uncertainty than its neighbors.

Of BUILD_PLAN section 6's seven era-handling rules, four turned out to
already be satisfied by how Phase 1 and Phase 2 were built (schedule
length, expansion/realignment, franchise relocations, ties/overtime/
neutral sites) - worth stating explicitly so it's clear that was verified,
not assumed.

## Key results

- 1987 replacement games: Spearman rank correlation 0.88 (Massey) and
  0.90 (Bayesian) between the ranking with and without those games - a
  handful of teams move, the broad ranking doesn't. Philadelphia is the
  single biggest mover under both models. This supports keeping the
  games in (flagged, not excluded), per BUILD_PLAN's default proposal.
- 1982: mean Bayesian posterior SE is 3.05, the widest of the 1978-1986
  window (next-widest is 2.83 in 1984) - the small-sample rule holds
  without any special-casing, since the Bayesian model's uncertainty
  already responds to games played.
- The 1987 finding is grounded in the historical record, recovered from
  our own data: Philadelphia's and the defending-champion Giants'
  replacement squads went 0-3, Washington's went 3-0 (the team the film
  The Replacements was based on). Washington barely moves in the
  with/without comparison because its regulars won that year's Super
  Bowl; Philadelphia moves most because its regular roster was far
  better than its replacement results.

## What's carried forward, not fixed here

Same two Phase 1 items as before (pre-1999 playoff round labels;
team-season conference/division table), plus one Phase 2 item
(Bradley-Terry's `REG_STRENGTH` constant, worth rechecking if Phase 4
changes the validation protocol). None of these block Phase 4.

## Recommended next step

Phase 4: validation. Out-of-sample prediction results (this time with
held-out future weeks, not Phase 2's within-season k-fold), a comparison
against historical closing point spreads (available from roughly 1979
on), and an adversarial audit of teams whose ratings conflict with
historical evidence. This is where the model family gets locked in for
good, per BUILD_PLAN section 8.
