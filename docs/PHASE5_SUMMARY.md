# Phase 5 Summary: Accomplishment, Conference Strength Index, Profiles

Status: COMPLETE (ACC formula is a recommendation for Brian to confirm or adjust, not a lock)
Date: 2026-09-16

## What was built

- **Team-season conference/division table**
  (`src/division_alignment.py` → `data/reference/team_season_conference.csv`).
  The Phase 1 carried-forward item, finally built - not from memory, but
  from division alignments verified against Wikipedia, the Pro Football
  Hall of Fame, and team history pages, covering all six realignments in
  this project's window (1970 merger, 1976 one-season-only placement,
  1977 Tampa Bay/Seattle swap, 1995 and 1999 expansions, 2002's full
  8-division realignment). Every team-season resolves (the builder raises
  if one doesn't, rather than silently dropping it), and every era's team
  count matches Phase 1's independently-audited numbers exactly - 20 new
  tests cover both the specific historical milestones and that
  cross-check.
- **Conference Strength Index** (`src/conference_strength.py` →
  `data/processed/conference_strength_index.csv`). CSI = mean(AFC rating)
  - mean(NFC rating) under the locked Bayesian model, with its
  uncertainty derived from the same posterior the ratings themselves come
  from (a linear contrast of the fitted parameter vector), not a separate
  ad hoc calculation - exactly the BUILD_PLAN language about
  interconference games being the informative edges and needing an
  uncertainty range.
- **Accomplishment score** (`src/accomplishment.py` →
  `data/processed/team_season_accomplishment.csv`). A drafted, documented
  point schedule - see that file's docstring for the full table and
  reasoning. Flat per-round-blind playoff win bonuses were chosen because
  1970-1998 games only carry a generic PLAYOFF flag, not a WC/DIV/CON
  label (the other still-open Phase 1 item); the Super Bowl itself needed
  no round label to identify reliably - it is always, with zero
  exceptions across all 56 seasons, the single game with the latest date
  that season.
- **Descriptive sub-scores** (`src/team_profile.py` →
  `data/processed/team_season_profile.csv`): Dominance, Offense, Defense,
  Schedule Difficulty, and Record vs. Elite Opponents, all computed
  purely from the game log and the locked model's own ratings, never
  feeding True Strength Rating itself. Roster Quality and Coach Strength
  Entering Season are not computed - both need external data (Approximate
  Value, head-coach records) this project hasn't acquired, and Roster
  Quality specifically has an open redistribution-rights question
  (BUILD_PLAN section 11) in the same category as the Phase 4 spread-data
  pause.
- **Full team-season table** (`src/run_phase5.py` →
  `data/processed/team_season_full_profile.csv`, 1,669 rows, 31 columns):
  True Strength Rating, Accomplishment, Conference Strength Index, and
  every descriptive sub-score in one place.

## Validation: three team-seasons that show the system working

- **2007 New England** (TSR z=2.51, the highest of any team-season in
  this dataset) scores ACC=24.0 - high, but not the ceiling, because they
  lost the Super Bowl. The undefeated regular season, division title, and
  conference's best record all still count.
- **2011 NY Giants** (TSR z=0.76, a middling 9th of 32 that season)
  scores ACC=24.6, nearly matching the greatest regular season on record,
  because they won the Super Bowl. This is exactly the gap BUILD_PLAN's
  two separate headline scores exist to show, not close.
- **2000 Baltimore** scores division_title=False despite winning the
  Super Bowl (ACC=24.5) - correctly reflecting that the Ravens were a
  wild-card team that year, not division champions (Tennessee won the
  AFC Central at 13-3). Nothing in this project hard-codes that fact; it
  falls directly out of comparing win_pct across the division table just
  built.

## The ACC point schedule is a recommendation, not a lock

Unlike the model family (BUILD_PLAN section 2, a settled decision Brian
already confirmed), the ACC formula was explicitly left open ("to be
drafted in Phase 5," section 11) with no point values specified anywhere
in the plan. What's in `accomplishment.py` now is this session's draft -
reasoned, documented, and validated against real history above - not a
final answer. Worth Brian's attention specifically:

- Whether playoff wins should eventually escalate by round once 1970-1998
  round labels are reconstructed (currently flat regardless of round).
- Whether the specific point values (base scale of 10, +2 per playoff
  win, +4/+6 for Super Bowl appearance/win, etc.) reflect the right
  relative weighting - these were chosen for a sensible-looking ordering,
  not derived from any external target.
- Whether "best record in conference" (+1) is a component worth keeping,
  since BUILD_PLAN's own list doesn't name it explicitly (it was read in
  from "regular-season record and standing").

## What's carried forward

- Roster Quality and Coach Strength Entering Season (need new,
  provenance-checked data sources - same standard as the spread
  comparison).
- Pre-1999 playoff round labels (would let playoff-win bonuses escalate
  by round instead of being flat).
- The deferred spread comparison from Phase 4.

## Recommended next step

Brian reviews the ACC formula (and can request changes with no
downstream cost - it's a pure function of data already in the repo).
Then Phase 6: outputs and the GitHub Pages website - CSV/JSON exports,
per-Super Bowl matchup pages, the query pages BUILD_PLAN section 8 lists
(greatest champions, weakest champions, best teams never to win, etc.),
and the accessibility requirements in section 10.
