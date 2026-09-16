# Gridiron Greatness Rating — Build Plan and Research Specification

Status: Proposal approved for planning. No code written yet.
Owner: Brian (1EyeBiney). Methodology is owned by the project lead and the coordinating Claude session; research agents supply evidence, never weights.
Last updated: 2026-09-16

## 1. Purpose

Build a rating system that measures how strong every NFL team actually was in each season, accounting for the true strength of its opponents and the competitive environment of its conference and era, and then use that database to evaluate Super Bowl participants against historical rankings.

The system answers: "How strong was this team really, given what it did, who it did it against, and how strong its competitive environment was?"

## 2. Decisions already made

These are settled. Do not reopen them without Brian's approval.

1. Scope begins with the 1970 season (post-merger). Super Bowls I through IV (1966–1969 seasons) are excluded from the core model because the AFL and NFL did not play each other, so the opponent network is disconnected. They may appear later as a separately labeled appendix.
2. Playoff games count toward True Strength. The rating uses every game a team played that season, regular season and postseason. The Super Bowl result itself is one more game, not a trophy bonus.
3. True Strength is a single schedule-adjusted network rating, not a weighted average of hand-picked components. The components from the original brainstorm (dominance, quality of competition, offense/defense balance, postseason, personnel) become descriptive sub-scores shown in each team's profile. They do not feed the headline number. This avoids triple-counting point margin.
4. Two headline scores per team-season: True Strength (how good) and Accomplishment (how successful). They are reported side by side and never blended.
5. Final home is a public GitHub repository under github.com/1eyebiney with a static website (GitHub Pages) for the results.
6. All outputs must be usable non-visually first: data tables, CSV, and plain-text narrative. Charts are optional extras and must never be the only way to get a number.
7. Everything normalized within its own season. Cross-era comparison uses standardized values (standard deviations from the league mean that year), never raw totals.
8. Only contemporaneous information may influence any score. No Hall of Fame status, no later coaching legacy, no "future" knowledge. Such facts may be displayed as descriptive context only.

## 3. Definitions

True Strength Rating (TSR). A team's estimated point-margin advantage over an average team from the same season on a neutral field, derived from a network model fit on all games that season, then expressed on a standardized scale so seasons can be compared. Higher is better. An average team is zero on the raw scale.

Accomplishment Rating (ACC). A score for how successful the season was: regular-season record and standing, division title, playoff wins, conference championship, Super Bowl result, undefeated season, and postseason dominance. This is where the trophy is rewarded.

Conference Strength Index (CSI). The estimated difference in average team strength between the two conferences in a given season, derived from the network model (interconference games are the informative edges). Reported with an uncertainty range because each team plays only a few interconference games.

Descriptive sub-scores (profile only, not in TSR): Schedule Difficulty, Dominance, Record vs Elite Opponents, Offense (standardized), Defense (standardized), Postseason Evidence, Roster Quality (contemporaneous), Coach Strength Entering Season.

## 4. Anti-bias rules

Hindsight rule: no variable may use information that did not exist by the end of that season.

Circularity rule: personnel honors (Pro Bowl, All-Pro) are partly a function of team success. They stay descriptive.

Double-count rule: any candidate variable must be checked for overlap with point margin and schedule strength before being reported alongside TSR.

Blowout rule: individual game margins are capped or dampened (candidate: cap at 28 points, or use a diminishing transform) so one 55–10 game does not dominate a season.

Tier rule: the all-time ranking uses only the Core model (variables available for every season since 1970). Modern-only data (play-by-play, EPA, explosive-play rate, from about 1999) lives in an Enhanced supplement and never changes the core ranking.

Small-sample rule: any conference-level or era-level statement carries an uncertainty range.

## 5. Model approach

Baseline (must reproduce first): Simple Rating System as published by Pro Football Reference. Reproducing their SRS numbers for several seasons proves our game data is clean. This is a validation step, not the final model.

Candidate core models, to be compared:

- Massey-style least squares on margin with home-field term and margin damping.
- Bradley-Terry / logistic model on win-loss with a margin-aware extension.
- Bayesian hierarchical margin model with shrinkage toward the league mean (preferred if it validates; gives uncertainty for free).
- Elo (season-restarted) as a sanity comparator, not a candidate for the headline.

Selection criterion: out-of-sample predictive accuracy on held-out games (log loss on winner, mean absolute error on margin), plus agreement with closing point spreads for seasons where spreads exist (roughly 1979 onward). The rating itself is retrodictive (fit on the full season), but the model family is chosen by predictive validation.

Standardization: convert each season's raw ratings to z-scores using that season's mean and standard deviation across all teams, then optionally map to a 0–100 display scale. Keep the z-score as the canonical value.

## 6. Era handling rules (to be finalized in Phase 3)

- Schedule length: 14 games (1970–1977), 16 games (1978–2020), 17 games (2021–). Standardization within season handles most of this; per-game rates used everywhere.
- 1982 strike: 9-game season, 16-team tournament. Include, flag, and report with wider uncertainty.
- 1987 strike: three replacement-player weeks. Decision needed: include, exclude, or down-weight those games. Default proposal: include but flag; test sensitivity.
- Expansion and realignment: 26 teams (1970), 28 (1976), 30 (1995), 31 (1999), 32 (2002). Conference and division membership tables by year are required inputs. 2002 realignment changes division structure.
- Franchise relocations and renames: a franchise ID table mapping every team-season to a stable franchise key.
- Ties: allowed; treat as half-win where record matters, and as zero margin in the network.
- Overtime and rule changes: noted for context, not modeled in Core.
- Neutral-site games (Super Bowls, international games): home-field term set to zero.

## 7. Data plan

Required for Core (1970–present):
- Every game: season, week, date, home team, away team, scores, neutral flag, playoff round flag, overtime flag.
- Team-season table: franchise key, conference, division, final record, division finish, playoff seed and results.
- Team-season totals: points for/against (derivable from games), and where available yards, turnovers.

Required for descriptive sub-scores:
- Pro Bowl, first- and second-team All-Pro, MVP/OPOY/DPOY by season.
- Approximate Value by roster (Pro Football Reference origin; licensing to be reviewed before redistribution).
- Head coach by team-season with prior career record.

Required for validation:
- Historical point spreads, roughly 1979 onward.
- Pro Football Reference published SRS, SOS, and margin for reproduction checks.

Required for Enhanced tier (1999–present):
- nflverse play-by-play (for EPA, explosive-play rate, turnover detail). Tests the idea2 hypothesis: explosive plays versus turnovers as a game-deciding trend.

Candidate sources (to be verified in Phase 1): nflverse schedule and play-by-play data; public historical score archives covering 1970 onward; Pro Football Reference used as a manual validation reference rather than a scraped pipeline because of terms of service and rate limits; publicly posted spread datasets. Every source gets a provenance note and license check before use. Raw downloads are stored under data/raw and never edited by hand; all cleaning is scripted.

## 8. Phases

Phase 0 — Specification (this document). Done when Brian approves it and it is committed to the repo.

Phase 1 — Data acquisition and audit. Deliverable: a verified games table for 1970 through the most recent completed season, with a data-quality report (team counts per season, games per team, score sanity checks, playoff bracket reconciliation). Exit check: SRS reproduced for at least five seasons across different decades within rounding.

Phase 2 — Baseline and candidate models. Deliverable: SRS reproduction, then Massey, Bradley-Terry, and Bayesian implementations producing per-season ratings; a comparison report.

Phase 3 — Era normalization. Deliverable: standardization layer, strike and expansion rules implemented, sensitivity report showing how much each rule moves rankings.

Phase 4 — Validation. Deliverable: out-of-sample prediction results; spread comparison; adversarial audit listing teams whose ratings conflict with historical evidence and an explanation or fix for each. Model family locked at the end of this phase.

Phase 5 — Accomplishment, Conference Strength Index, profiles. Deliverable: ACC formula documented and computed; CSI per season with uncertainty; full team-season profile table including descriptive sub-scores.

Phase 6 — Outputs and website. Deliverable: CSV and JSON exports; per-Super Bowl matchup pages; query pages (greatest champions, weakest champions, greatest losers, best teams never to win, largest mismatches, greatest conference imbalance, best decade, records that most overstated strength); accessible static site on GitHub Pages with proper headings, data tables with header cells, and text alternatives for any chart.

## 9. Tooling (confirmed 2026-09-16)

Brian has delegated the language choice. Decision: Python 3 with pandas and numpy for data work; scipy or a lightweight Bayesian library for models; pytest for tests; data stored as CSV/Parquet in the repo; a static site generator or plain HTML templates for GitHub Pages. Repo layout proposal:

    data/raw/          untouched downloads with source notes
    data/processed/    scripted outputs
    src/               pipeline and models
    tests/             reproduction and sanity tests
    docs/              this plan, methodology, decision log
    site/              generated website

## 10. Accessibility requirements for the site

Semantic headings for every section; real HTML tables with scope attributes; sortable tables must be keyboard-operable and announce sort state; every chart accompanied by the underlying table or a text summary; no information conveyed by color alone; skip links; tested with NVDA and JAWS before release.

## 11. Open questions

- Confirm handling of 1987 replacement games (default: include and flag).
- Choose the display scale for TSR (z-score only, or also 0–100).
- Decide whether Approximate Value can be redistributed or must be computed on the fly from source.
- Decide the exact ACC point schedule (to be drafted in Phase 5).

## 12. Decision log

2026-09-16 — Scope starts 1970. Playoffs count in TSR. Single network rating, components descriptive only. GitHub repo plus GitHub Pages site. Build document maintained in project and repo.
2026-09-16 — Python confirmed as pipeline language (Brian delegated the choice). Phase 1 may be run on any model; model-selection decisions in Phases 2–4 should be made by the coordinating session with Brian, not left to a research agent.

## 13. Notes for the next session

Start with Phase 1. First task: identify and download a game-results source covering 1970 to the latest completed season, store it under data/raw with a source note, and write the games-table cleaning script. Exit check before moving on: reproduce Pro Football Reference SRS for five seasons in different decades. Report data-quality findings back to Brian in plain-text tables.
