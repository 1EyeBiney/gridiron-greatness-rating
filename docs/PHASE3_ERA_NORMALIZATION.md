# Phase 3: Era Normalization

Status: COMPLETE

## What changed and why nothing else needed to

BUILD_PLAN section 6 lists seven era-handling rules. Four were already
satisfied by how Phase 1 and Phase 2 were built, not by anything new here:

- **Schedule length** (14/16/17 games): every model predicts a single
  game's margin or win probability, never a season total, so a longer or
  shorter schedule changes how many games inform a team's rating, not the
  scale it's reported on. No conversion needed.
- **Expansion/realignment** (26 to 32 teams): standardizing within season
  (below) automatically adapts to however many teams played that season.
  Phase 1's data-quality audit already confirmed every season has the
  historically correct team count.
- **Franchise relocations**: handled in Phase 1 by franchise_crosswalk.csv.
- **Ties, overtime, neutral sites**: handled in Phase 2's src/models/common.py
  (ties score as a half-win/zero margin; overtime is recorded but unused by
  any model; neutral sites zero out the home-field term).

What this phase actually added:

1. **Standardization layer** (src/standardize.py): every model's rating is
   now also expressed as a z-score within its season (mean 0, sd 1 across
   that season's teams) plus an optional 0-100 display scale. The z-score,
   not the raw rating, is the canonical cross-era value per BUILD_PLAN
   section 5. Applied in place to data/processed/team_season_ratings.csv.
2. **1982 and 1987 strike handling** (src/era.py): both seasons are flagged
   in the new data/reference/season_metadata.csv, and the 42 specific 1987
   games played by replacement players are flagged in
   data/processed/era_flags_1987_replacement_games.csv. Both are included,
   not excluded, per BUILD_PLAN's default proposal - see the sensitivity
   results below for why that held up.

## Season metadata

56 seasons, 26 to 32 teams,
schedule length 9 to 17
games. Full table in data/reference/season_metadata.csv. Flagged strike seasons:

- 1982: 9-game regular season, 16-team expanded playoff tournament.
- 1987: 15-game regular season (one week cancelled outright); 3 of the 15 weeks played with replacement players.

## Sensitivity: 1987 replacement-player games

Refit 1987 twice - with all 210 regular-season games, and with the 42 replacement-player games removed - for the two point-margin models, and compared the resulting team ratings.

| Model | Spearman rank correlation | Mean \|change\| | Max \|change\| | Most affected |
|---|---:|---:|---:|---|
| massey | 0.884 | 1.56 | 4.13 | PHI |
| bayesian_margin | 0.905 | 0.82 | 2.07 | PHI |

Rank correlation between 0.884 and 0.905 for the two models means the replacement games shift a handful of teams (both models flag PHI as the biggest single mover) but do not reshuffle the 1987 ranking broadly; the largest single-team swings are documented in data/processed/phase3_1987_sensitivity_*.csv for anyone who wants to sanity-check a specific team. This supports BUILD_PLAN's default of including the replacement games (flagged, not excluded).

Who the replacement weeks helped and hurt, from the 42 games themselves (worst and best point differential):

| Team | Replacement-game record | Point diff |
|---|---:|---:|
| KC | 0-3 | -69 |
| PHI | 0-3 | -57 |
| NYG | 0-3 | -49 |
| CLE | 2-1 | +39 |
| WSH | 3-0 | +39 |
| CHI | 2-1 | +50 |

This is the historical record of that strike, recovered from the data rather than assumed: Philadelphia's and the defending-champion Giants' replacement squads were among the worst, and Washington's went unbeaten (the team the film The Replacements was based on). It is also why Washington barely moves in the with/without comparison - its regulars went on to win the Super Bowl, so its replacement results were consistent with its strength - while Philadelphia's regular roster was far better than its replacement results, making it the biggest mover under both models.

## Sensitivity: 1982 uncertainty

BUILD_PLAN section 4's small-sample rule expects the 9-game 1982 season to carry a wider uncertainty range than its 16-game neighbors. The Bayesian model's posterior standard error (src/models/bayesian_margin.py) already widens automatically with fewer games - no new code needed, just confirming it actually does:

| Season | Mean Bayesian rating SE |
|---:|---:|
| 1978 | 2.257 |
| 1979 | 2.465 |
| 1980 | 2.473 |
| 1981 | 2.577 |
| 1982 | 3.051 <- strike season |
| 1983 | 2.569 |
| 1984 | 2.827 |
| 1985 | 2.716 |
| 1986 | 2.764 |

1982 has the widest mean uncertainty of this nine-season window, confirming the small-sample rule holds without any special-casing.

## Carried forward

Model family is still not locked (that's Phase 4). The two Phase 1 carry-forwards (pre-1999 playoff round labels; team-season conference/division table) remain outstanding and still don't block anything up through Phase 4.

