# The Playcallers — plan

Fourth study in the Gridiron Greatness family. Folder `studies/playcallers/`,
modules prefixed `pc_`, published at `/playcallers/` through the main
build's STUDIES list (not added until Phase 5).

Approved by Brian 2026-09-27: name, living in this repo, and fetching
Wikipedia staff pages for the Phase 0 test. Sonnet subagents do the
sub-tasks; Fable writes the plan, reviews every hand-off, and writes prose.

## The question

Can we rate the people who call plays, by following them from team to team?
Brian's examples: Ben Johnson (Detroit offensive coordinator 2022-2024,
Chicago head coach 2025) and Mike Macdonald (Baltimore defensive
coordinator 2022-2023, Seattle head coach 2024-).

## What is being rated

The **play caller** for a unit in a game: by default the coordinator,
overridden where a head coach is known to call his own plays. Offense and
defense are rated separately. A person can appear on both lists.

## Data

| Piece | Source | Status |
|---|---|---|
| Play-by-play 1999-2025 | nflverse (CC BY 4.0), already local in explosive-edge | have |
| Head coach and starting QB per game | nflverse schedule file, already in home-field-advantage | have |
| Coordinators per team-season | Wikipedia team-season pages (CC BY-SA 4.0) | Phase 0 tests this |
| Play-caller overrides | Hand-built table, each row with source and confidence | Phase 1 |
| Mid-season changes | Same pages plus manual checks | Phase 1 |

Rules carried over: no scraping of Pro-Football-Reference (manual spot
checks only); raw fetched pages are cached locally and gitignored; derived
tables are committed with a SOURCE.md; ask Brian before any new source.

## Phases

| Phase | Work | Gate |
|---|---|---|
| 0 | Extract head coach, offensive coordinator, defensive coordinator for all 32 teams, 2022-2024, from Wikipedia. Measure coverage and accuracy. | Fable review, report to Brian |
| 1 | Full table 1999-2025; play-caller overrides; mid-season changes at game level | Brian reviews the override list |
| 2 | Opponent-adjusted unit ratings per game (efficiency, success rate, explosive rate) | Fable review |
| 3 | Play-caller ratings: quarterback controls, shrinkage, four-way mover comparison | Fable review |
| 4 | Coaching trees from the staff table | — |
| 5 | Site pages and publication | Brian approves before publishing |

## Phase 0 acceptance

- Coverage: a named offensive and defensive coordinator for at least 90 of
  96 team-seasons, or an explicit "none / vacant / head coach" reason.
- Accuracy: agreement with a hand-checked answer key of at least 20
  team-seasons, including the hard ones (mid-season firings, teams with no
  titled coordinator, interim head coaches).
- Head-coach cross-check: the extracted head coach matches the schedule
  file's coach for that team-season, which validates the parsing.
- Known anchors must come out right: Ben Johnson DET OC 2022-2024;
  Mike Macdonald BAL DC 2022-2023 and SEA HC 2024.

## Limits to state on the site from the start

- Play calling cannot be separated from players by scores alone. The study
  reports association around moves, not proof of cause.
- Defensive results are noisier than offensive ones, so defensive ratings
  carry wider ranges.
- Most coordinators have two to five seasons in a role. Small samples are
  pulled toward average and shown with their uncertainty.
- Who calls plays is sometimes disputed or changes mid-season. Every
  override is sourced and graded for confidence.
