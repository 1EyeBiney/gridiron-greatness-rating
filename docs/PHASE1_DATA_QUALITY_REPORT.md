# Phase 1 Data Quality Report

Total games: 13685
Season range: 1970-2025

## 1. Teams per season

All 56 seasons (1970-2025) have the expected team count for their era. PASS.

## 2. Regular-season games per team per season

Team-seasons checked: 1669
Team-seasons matching expected schedule length: 1667
Team-seasons NOT matching (including known strike-year exceptions): 2
Breakdown by season:
  2022: 2 team(s) off from expected count *** UNEXPECTED ***

Detail on UNEXPECTED mismatches (not 1982/1987):
 season team  games  expected
   2022  BUF     16        17
   2022  CIN     16        17

## 3. Score sanity checks

Negative scores: 0
Missing scores: 0
Games with |margin| > 55 (extreme, not necessarily wrong - listed for manual spot check): 3
 season       date home_franchise away_franchise  home_score  away_score
   1976 1976-12-04            LAR            ATL          59           0
   2009 2009-10-18             NE            TEN          59           0
   2012 2012-12-09            SEA            ARI          58           0

## 4. Duplicate game detection

Exact duplicate rows (same season/date/teams/scores): 0
PASS - no duplicates found.

## 5. Playoff bracket reconciliation

All seasons match expected playoff game counts for their era. PASS.

CAVEAT: the expected-count table itself was recalled from general knowledge, not
verified season-by-season against a primary source. Treat this check as a first
pass, not a certification.

## Known open items (not fixed by this audit)

- Pre-1999 playoff games (FiveThirtyEight source) carry only a binary playoff flag,
  not a round label (Wild Card / Divisional / Conference / Super Bowl). Round detail
  needs a dedicated follow-up pass, e.g. reconstructing rounds from each season's
  known bracket size and game dates, cross-checked against Wikipedia per-season
  playoff articles.
- No week number for 1970-1998 games (FiveThirtyEight has date only, no week field).
- No team-season conference/division table yet (needed for Phase 5 Conference
  Strength Index and for a more precise div_game check pre-1999).
