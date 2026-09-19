# Source: nflverse play-by-play (nflfastR)

URL pattern: https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet
Repo: https://github.com/nflverse/nflverse-data (release tag `pbp`), data built by the nflverse team (nflfastR)
Fetched: 2026-09-19
License: CC BY 4.0 (nflverse-data org LICENSE.md). Requires attribution, a link to the license, and a note if the data is modified. This project attributes nflverse in README.md, docs/BUILD_PLAN.md and the site footer; play-by-play is aggregated to one row per team-game before anything is committed (see data/processed/team_game.csv).
Coverage: 1999-2025, one parquet file per season.

Row counts per season (raw plays, all game types):

- 1999: 46,136
- 2000: 45,491
- 2001: 44,969
- 2002: 47,355
- 2003: 46,811
- 2004: 46,705
- 2005: 46,823
- 2006: 46,299
- 2007: 46,266
- 2008: 45,917
- 2009: 46,519
- 2010: 46,892
- 2011: 47,448
- 2012: 47,834
- 2013: 48,158
- 2014: 47,629
- 2015: 48,122
- 2016: 47,651
- 2017: 47,245
- 2018: 47,109
- 2019: 47,260
- 2020: 47,705
- 2021: 49,922
- 2022: 49,434
- 2023: 49,665
- 2024: 49,492
- 2025: 48,771

Plays per season with a null win probability (`wp`) - these are treated as garbage time (excluded) by xe_metrics.py's `_ng` non-garbage-time counters, since there is no probability to compare against [0.05, 0.95]:

- 1999: 259 of 46,136
- 2000: 270 of 45,491
- 2001: 272 of 44,969
- 2002: 274 of 47,355
- 2003: 275 of 46,811
- 2004: 274 of 46,705
- 2005: 275 of 46,823
- 2006: 275 of 46,299
- 2007: 276 of 46,266
- 2008: 275 of 45,917
- 2009: 275 of 46,519
- 2010: 274 of 46,892
- 2011: 274 of 47,448
- 2012: 275 of 47,834
- 2013: 276 of 48,158
- 2014: 272 of 47,629
- 2015: 275 of 48,122
- 2016: 275 of 47,651
- 2017: 273 of 47,245
- 2018: 275 of 47,109
- 2019: 275 of 47,260
- 2020: 269 of 47,705
- 2021: 285 of 49,922
- 2022: 284 of 49,434
- 2023: 285 of 49,665
- 2024: 285 of 49,492
- 2025: 285 of 48,771

Notes:
- Raw parquet files are NOT committed (data/raw/nflverse_pbp/*.parquet is gitignored); only the team-game aggregate is. Re-run `python src/xe_ingest.py --refresh` to re-download.
- Team codes (posteam/defteam/home_team/away_team) are relocation-specific (e.g. STL vs LAR), mapped to franchise-stable codes via data/reference/franchise_crosswalk.csv in the main repo, same as the home-field-advantage study.
