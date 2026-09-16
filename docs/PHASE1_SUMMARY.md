# Phase 1 Summary: Data Acquisition and Audit

Status: COMPLETE
Date: 2026-09-16

## What was built

A unified Core games table covering every NFL regular-season and playoff
game from the 1970 merger through the 2025 season (the most recently
completed season as of this writing): 13,685 games, in
`data/processed/games.csv`.

It was assembled from two raw sources:

- FiveThirtyEight's `nfl_games.csv` (MIT license), used for the 1970-1998
  seasons. Its team codes already track franchise identity persistently
  through relocations (verified for the Colts, Rams, and Raiders).
- nflverse's `games.csv` (CC BY 4.0 license, attribution given in
  README.md and here), used for 1999-2025. This source also supplies
  playoff round labels (Wild Card/Divisional/Conference/Super Bowl)
  directly, which the older source does not.

A franchise crosswalk (`data/reference/franchise_crosswalk.csv`) unifies
both sources onto one stable set of 32 franchise IDs, correctly handling
every relocation in the window (Rams, Raiders, Chargers) and, importantly,
the 1996 Browns/Ravens split exactly as the NFL itself rules it: Browns
history stays in Cleveland (with a 1996-1998 gap when no team existed),
and the Ravens are a separate new franchise starting in 1996 - not a
relocated Browns.

## Data quality audit (full detail in PHASE1_DATA_QUALITY_REPORT.md)

Every one of the 56 seasons has the correct number of teams for its era
(26 in 1970, rising to 32 by 2002). Every team-season has the correct
regular-season game count for its era's schedule length (14, then 16,
then 17 games), with exactly two explainable exceptions: the 1982 and
1987 strike seasons (9 and 15 games respectively), and Buffalo/Cincinnati
in 2022, whose Week 17 game was permanently cancelled after Damar
Hamlin's on-field cardiac arrest and never made up - confirmed against
news reporting at the time, not a data error. There are no negative or
missing scores and no duplicate games. Three games carry an unusually
large margin (55+ points); all three were checked against independent
sources and are real, documented blowouts (Rams 59-0 over the Falcons in
1976, Patriots 59-0 over the Titans in 2009, Seahawks 58-0 over the
Cardinals in 2012), not data entry errors. Playoff game counts per season
match the known history of playoff-format changes (7 games/season
1970-1977, 9 from 1978-1989, 11 from 1990-2019, 13 from 2020 on, with
1982's special 16-team tournament at 15) - this particular check should
still be treated as a first pass, since the expected-count table itself
came from general knowledge rather than a season-by-season primary-source
check.

## Exit check: SRS reproduction

Pro Football Reference's Simple Rating System (SRS) was reproduced from
our own game data and our own implementation, using PFR's exact
convention for this specific check: regular-season games only, no
home-field adjustment. We compared our results against PFR's actual
published SRS values (transcribed by hand from pro-football-reference.com
on 2026-09-16) for five seasons spanning five different decades: 1975,
1985, 1995, 2005, and 2015 - 148 team-seasons in total.

Result: maximum absolute difference of 0.05 SRS points, mean absolute
difference of 0.026. A difference of 0.05 is exactly what you'd expect
from PFR rounding its own displayed values to one decimal place - in
other words, this is as close to a perfect match as the comparison can
even measure. This is strong evidence that the underlying game data is
clean and that the rating computation is implemented correctly.

Note: this SRS run is a validation tool only. The project's own True
Strength Rating (per docs/BUILD_PLAN.md) will differ from PFR's SRS in
one deliberate way - it includes playoff games - because the settled
project decision is that playoff performance is evidence of strength,
not just a bonus for winning.

## What's carried forward, not fixed here

Two gaps are noted but intentionally not solved in Phase 1, since fixing
them well deserves dedicated attention rather than a rushed pass:

1. Playoff round labels for 1970-1998 (currently a generic "PLAYOFF" flag
   rather than Wild Card/Divisional/Conference/Super Bowl). No ready-made
   dataset was found; the likely path is reconstructing rounds from each
   season's known bracket size plus game dates, cross-checked against
   Wikipedia's per-season NFL playoffs articles.
2. A team-season conference/division table. Needed for Phase 5's
   Conference Strength Index and would let us re-run the div_game check
   for seasons before 1999 (nflverse has it built in from 1999 on).

## Repository status

The project lives in a git repository with a full commit history of every
step above. It has not yet been pushed to GitHub: this session has no
GitHub credentials and no shell access to Brian's computer, so either
Brian pushes the working copy himself, or a future session connects a
GitHub integration to do it directly. All files are also mirrored into
Brian's local `gridiron-greatness-rating` folder.

## Recommended next step

Phase 2: implement and compare the candidate True Strength models (Massey
least squares, Bradley-Terry, Bayesian hierarchical margin model) on the
full Core table, including playoff games this time. Selection is by
out-of-sample predictive accuracy, per docs/BUILD_PLAN.md section 5.
