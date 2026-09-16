# Source: FiveThirtyEight nfl-elo-game

URL: https://raw.githubusercontent.com/fivethirtyeight/nfl-elo-game/master/data/nfl_games.csv
Repo: https://github.com/fivethirtyeight/nfl-elo-game
Fetched: 2026-09-16
License: MIT (repo LICENSE, copyright ABC News Internet Ventures 2021)
Coverage: every NFL/AFL game 1920-2020 (16,810 rows). This project uses only the
1970-1998 slice as the pre-nflverse backbone for the Core model.

Columns: date, season, neutral, playoff, team1, team2, elo1, elo2, elo_prob1,
score1, score2, result1.

Notes:
- team1/team2 use a stable per-franchise code that persists across relocations
  (e.g. IND represents the Colts continuously back through the Baltimore era;
  LAR represents the Rams continuously through the St. Louis era; OAK
  represents the Raiders continuously through the Los Angeles era). Verified
  by spot-checking IND (1953-2020), LAR (1937-2020 incl. 1995 St. Louis
  season), OAK (1960-2020) against known franchise relocation history.
- `playoff` is a binary flag only (no round: WC/DIV/CONF/SB). Round detail for
  1970-1998 postseason games must be sourced separately (open item).
- No overtime flag in this file.
- Not actively maintained past the 2020 season - irrelevant here since we only
  draw the 1970-1998 slice from it and use nflverse for 1999-present.
