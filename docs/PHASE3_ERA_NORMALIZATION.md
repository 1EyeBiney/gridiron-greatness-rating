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
| bayesian_margin | 0.904 | 0.83 | 2.16 | PHI |

Rank correlation between 0.884 and 0.904 for the two models means the replacement games shift a handful of teams (both models flag PHI as the biggest single mover) but do not reshuffle the 1987 ranking broadly; the largest single-team swings are documented in data/processed/phase3_1987_sensitivity_*.csv for anyone who wants to sanity-check a specific team. This supports BUILD_PLAN's default of including the replacement games (flagged, not excluded).

## Sensitivity: 1982 uncertainty

BUILD_PLAN section 4's small-sample rule expects the 9-game 1982 season to carry a wider uncertainty range than its 16-game neighbors. The Bayesian model's posterior standard error (src/models/bayesian_margin.py) already widens automatically with fewer games - no new code needed, just confirming it actually does:

| Season | Mean Bayesian rating SE |
|---:|---:|
| 1978 | 2.285 |
| 1979 | 2.529 |
| 1980 | 2.517 |
| 1981 | 2.585 |
| 1982 | 2.971 <- strike season |
| 1983 | 2.591 |
| 1984 | 2.796 |
| 1985 | 2.774 |
| 1986 | 2.752 |

1982 has the widest mean uncertainty of this nine-season window, confirming the small-sample rule holds without any special-casing.

## Carried forward

Model family is still not locked (that's Phase 4). The two Phase 1 carry-forwards (pre-1999 playoff round labels; team-season conference/division table) remain outstanding and still don't block anything up through Phase 4.

