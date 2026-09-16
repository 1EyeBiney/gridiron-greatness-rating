# Source: nflverse nfldata games.csv

URL: https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv
Repo: https://github.com/nflverse/nfldata (maintained by Lee Sharpe and the
nflverse team)
Fetched: 2026-09-16
License: CC BY 4.0 (nflverse-data org LICENSE.md). Requires attribution, a
link to the license, and a note if the data is modified. This project
attributes nflverse in README.md and docs/BUILD_PLAN.md and will note that
values are merged/transformed for the unified games table.
Coverage: 1999 through the 2026 season (in progress at fetch time; 7,548
rows). Includes REG, WC, DIV, CON, SB game types - this gives us playoff
round detail for free from 1999 forward.

Columns include: game_id, season, game_type, week, gameday, home/away team
and score, location, result, overtime, div_game, roof, surface, coaches,
QBs, spread_line, moneyline, and more.

Notes:
- Team codes are relocation-specific, not franchise-stable (e.g. LA vs STL
  for the Rams, OAK vs LV for the Raiders). A franchise crosswalk is required
  to unify these with the FiveThirtyEight codes used for 1970-1998.
- Actively maintained; re-fetch before any future rebuild to pick up newly
  completed games.
- Rows for the season still in progress at fetch time (2026) have null
  scores and must be excluded from the "latest completed season" cutoff.
