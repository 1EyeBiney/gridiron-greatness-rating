# Explosive Edge: do big plays now decide games the way turnovers do?

Study folder: `studies/explosive-edge/` (name provisional - see section 1).
Publishes as a sub-site at
https://1eyebiney.github.io/gridiron-greatness-rating/explosive-edge/
following the `studies/home-field-advantage/` pattern exactly (own src/,
data/processed/, tests/, site_templates/; modules prefixed `xe_`; added to
`STUDIES` in the main `src/build_site.py`).

Status: APPROVED 2026-09-19 (Brian: "use all your recommendations") -
name Explosive Edge, play-by-play fetch OK (local, gitignored, aggregates
committed), Sonnet subagents for Phases 0-3 with Fable reviewing and
writing prose, garbage-time filter as a sensitivity check. Build started
the same day.

## 0. The question, stated precisely

Turnover differential has been the classic single-number explanation for
who won a football game: each turnover hands the opponent a possession.
Chris Simms' argument is that explosive plays now belong alongside it -
that the team with more big plays wins, and that this reflects a real
shift in how offenses attack (fewer, longer-shot possessions, because
long methodical drives give the defense more snaps to make a play).

That is three testable claims, and the study should answer each
separately:

1. **Association.** In a given game, does the explosive-play differential
   predict the winner as well as, or better than, the turnover
   differential? Has that changed from 1999 to 2025?
2. **Exchange rate.** How many explosive plays is one turnover worth, in
   points of margin? Has the rate moved?
3. **Mechanism.** Are drives getting shorter (fewer plays, less clock) and
   more explosive? Is the per-snap chance of a defensive "play" (sack,
   turnover, negative play) rising, which would justify offenses wanting
   fewer snaps?

Plus one claim Simms doesn't make but the data can, and which is the
strongest version of his case if true:

4. **Persistence.** Turnover differential is known to be largely noise
   from game to game. If explosive-play differential is more persistent
   (a team's first-half-of-season rate predicts its second half), then it
   is closer to a *skill* than turnovers are - and a better thing to
   build a team around.

A caution to state on the site from the start: explosive plays gain yards
and yards become points, so "more big plays -> more wins" is close to a
tautology. The interesting comparisons are relative (vs turnovers) and
over time (has the balance shifted), not absolute.

## 1. Name

Candidates for the rating/site name, in order of preference:

- **Explosive Edge** - the site name; the metric is the Explosive Play
  Differential (EPD). Short, says what it measures, pairs with "Home
  Field Advantage" as a sibling title.
- **Chunk Theory** - fan-vocabulary ("chunk plays"), playful, fits the
  electric-football skin.
- **Boom Rate** - the per-drive explosive rate as the headline number.
- **The Big Play Effect** - plainest; also fine.

Folder name follows the site name (`studies/explosive-edge/`).

## 2. Data

Source: nflverse play-by-play (nflfastR), 1999-2025, via the
nflverse-data GitHub releases as one parquet file per season
(`play_by_play_YYYY.parquet`, roughly 20-40 MB each, ~800 MB total).
License CC BY 4.0 - same terms already accepted for the schedule file;
attribution in SOURCE.md, README and the site footer.

Rules:
- **Raw play-by-play is NOT committed.** An ingest script downloads it to
  `data/raw/nflverse_pbp/` (gitignored), aggregates to one row per
  team-game, and commits only that table (`data/processed/team_game.csv`,
  ~14,000 rows). The site and tests build from the aggregate, so CI never
  downloads 800 MB. A `--refresh` flag re-downloads; SOURCE.md records
  fetch date and the nflverse data version.
- Needs `pyarrow` added to requirements.txt.
- Join key to the main games table: nflverse `game_id`, which the main
  repo's 1999+ rows already carry in provenance (verify in Phase 0; if
  not, join on season/date/teams through the franchise crosswalk as the
  home-field study does).
- 2026 in-progress season: excluded from all trend analysis; optional
  "so far" note like the home-field site.

Columns needed per play: game_id, season, week, posteam, defteam,
play_type, yards_gained, epa, interception, fumble_lost, sack, drive,
drive_play_count, drive_time_of_possession, qb_dropback, rush_attempt,
pass_attempt, penalty (to exclude), aborted/no-play flags, score
differential, game_seconds_remaining.

## 3. Definitions (fixed before any analysis, then tested)

Per team-game, on scrimmage plays only (no penalties-only plays, kneels,
spikes, kickoffs, punts):

- **Explosive play**, primary definition: pass play gaining >= 20 yards
  or rush gaining >= 10. Standard in coaching/analytics usage.
- Sensitivity definitions, reported alongside: (a) 25/15; (b) 20/20; (c)
  EPA-based: any scrimmage play with EPA >= +2.0, which removes the
  yardage tautology partially.
- **Turnover**: interception or fumble lost, on any play type including
  special teams (they are still a lost possession). Report the
  scrimmage-only variant too.
- **Defensive "play"**: sack, turnover, or tackle for loss (yards_gained
  < 0 on a scrimmage play). Per-snap rate is the mechanism metric.
- Drive metrics: plays per drive, seconds per drive, yards per drive,
  explosive plays per drive, points per drive.
- Differentials are team minus opponent within the game.
- Garbage time: run everything twice, all plays and excluding plays with
  win probability outside [0.05, 0.95] (nflverse `wp`), and report if it
  changes a conclusion.

## 4. Analyses

A. **Per-season logistic regression**: win ~ EPD + TOD (both
   standardized within season). Track both coefficients 1999-2025 with
   confidence intervals. Also fit each alone and report classification
   log loss / accuracy of EPD-only vs TOD-only vs both. This is the
   headline "has the balance shifted" table.
B. **Exchange rate**: OLS margin ~ EPD + TOD per season. Points per
   explosive play, points per turnover, and the ratio ("one turnover
   equals N explosive plays"). Trend with CI.
C. **Mechanism trends** by season: league explosive rate per play and
   per drive, plays per drive, seconds per drive, pass rate, defensive-
   play rate per snap. Also the offensive strategy check: do teams with
   higher explosive rates run *fewer* plays per drive, and has that
   relationship strengthened?
D. **Persistence** (split-half reliability): for each team-season,
   correlate weeks 1-9 EPD rate with weeks 10-end EPD rate, likewise
   TOD, and the same for margin as a benchmark. By era. Also
   year-to-year persistence for teams with stable QB (optional, needs QB
   ids from the schedule file).
E. **Head-to-head table**: games where one team won the explosive battle
   and the other won the turnover battle - who wins, by era. The
   bar-argument table.
F. **Team-season leaderboard**: best EPD seasons 1999-2025 with record and
   the main project's True Strength Rating merged in (the tie-back to
   Gridiron Greatness).

Validation discipline (same as the other two projects):
- Synthetic-data tests for every aggregator and model function.
- Every prose number injected from tables; qualitative claims pinned in
  `tests/test_xe_claims.py`.
- Whole-site link/alt checker.
- A review checkpoint (Fable) after Phase 2 before any prose is written,
  because the tautology risk means the framing has to be right.

## 5. Site pages

index (Findings, short version + key tables), what-it-means (prose, SI
style, no tables), the-shift (analyses A and B by season), mechanism
(C), skill-or-luck (D), head-to-head (E), leaderboard (F), methodology,
data. Same skin; graphics are placeholders from the main project until
Brian replaces them.

## 6. Phases and who runs them

Designed so each phase is a self-contained brief a subagent (Sonnet) can
execute from this document plus the home-field study as the pattern
example, with Fable reviewing at the two checkpoints.

| Phase | Work | Output | Runner |
|---|---|---|---|
| 0 | Ingest: download parquet per season, aggregate to team_game.csv, SOURCE.md, tests on a synthetic pbp fixture | `src/xe_ingest.py`, `data/processed/team_game.csv` | Sonnet subagent |
| 1 | Definitions + metrics module; sensitivity variants; drive metrics | `src/xe_metrics.py`, tests | Sonnet subagent |
| 2 | Analyses A-F to CSV tables | `src/xe_analysis.py`, `data/processed/*.csv`, tests | Sonnet subagent (A-C) and a second in parallel (D-F) |
| — | **Review checkpoint 1**: are the results framed right given the tautology? What's the headline? | notes in docs/NOTES.md | Fable |
| 3 | Site generator + templates + link checker; STUDIES hook | `src/xe_site.py`, templates | Sonnet subagent |
| 4 | Prose pages (Findings, What It Means) + claim tests | templates, `tests/test_xe_claims.py` | Fable (prose needs the judgment) |
| — | **Review checkpoint 2**: full test run, live deploy, verify | | Fable |

Estimated size: larger than the home-field study (new data source, six
analyses, more pages), smaller than the main project.

## 7. Open decisions for Brian

1. Name (section 1).
2. OK to download nflverse play-by-play, 1999-2025, ~800 MB, kept local
   and gitignored, aggregates committed.
3. Phase split above, with Sonnet subagents for Phases 0-3 and Fable for
   review and prose - or a different split.
4. Whether garbage-time filtering should be the default or the
   sensitivity check (plan says: sensitivity).
