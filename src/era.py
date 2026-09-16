"""
BUILD_PLAN section 6 era-handling rules that aren't already satisfied by
construction elsewhere in the pipeline:

- Schedule length (14/16/17 games) needs no code here: every model in
  src/models/ already predicts a per-game rating (a single game's margin
  or win probability), never a season total, so a longer or shorter
  schedule changes how many games inform the estimate, not the scale the
  estimate is reported on. Confirmed in docs/PHASE3_ERA_NORMALIZATION.md.
- Expansion/realignment (26 to 32 teams) needs no code here either:
  z-scoring within season (standardize.py) automatically adapts to
  however many teams played that season, and Phase 1's data-quality audit
  already confirmed every season has the historically correct team count.
- Franchise relocations, ties, neutral sites, overtime: already handled
  in Phase 1 (franchise_crosswalk.csv) and Phase 2 (src/models/common.py).

What's left, and what this module does:
- Identify the 1987 replacement-player games so their effect on ratings
  can be measured (BUILD_PLAN: "include but flag; test sensitivity").
- Produce a season-level metadata table (team count, schedule length,
  which seasons are strike-shortened) for the standardization step and
  for reporting.
"""
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]

# The 1987 players' strike cancelled the week that would have been played
# Sept 27-28, 1987 (visible in the data as a 13-day gap with zero games -
# every other week that season is 6-7 days apart), then three weeks of
# replacement-player games followed before the regular players returned
# for the Oct 25-26 weekend. Dates below are exactly those three weekends,
# confirmed against our own games table: 3 x 14 games = 42, and the
# following Oct 25-26 weekend returns to the normal 13+1 split seen every
# other week of the season.
REPLACEMENT_GAME_DATES_1987 = {
    "1987-10-04", "1987-10-05",
    "1987-10-11", "1987-10-12",
    "1987-10-18", "1987-10-19",
}

STRIKE_SEASONS = {
    1982: "9-game regular season, 16-team expanded playoff tournament.",
    1987: "15-game regular season (one week cancelled outright); 3 of the "
    "15 weeks played with replacement players.",
}


def flag_1987_replacement_games(games: pd.DataFrame) -> pd.Series:
    """Boolean Series aligned to games' index: True for the 42 regular-
    season games played by replacement players in 1987."""
    is_1987_reg = (games["season"] == 1987) & (games["game_type"] == "REG")
    return is_1987_reg & games["date"].isin(REPLACEMENT_GAME_DATES_1987)


def season_metadata(games: pd.DataFrame) -> pd.DataFrame:
    """One row per season: team count, regular-season games per team
    (schedule length), and strike-season flag/note."""
    rows = []
    for season, g in games.groupby("season"):
        reg = g[g["game_type"] == "REG"]
        teams = sorted(set(reg["home_franchise"]).union(reg["away_franchise"]))
        games_per_team = (reg["home_franchise"].value_counts().add(
            reg["away_franchise"].value_counts(), fill_value=0
        ))
        rows.append(
            {
                "season": season,
                "teams": len(teams),
                "schedule_length": int(games_per_team.median()),
                "strike_season": season in STRIKE_SEASONS,
                "note": STRIKE_SEASONS.get(season, ""),
            }
        )
    return pd.DataFrame(rows).sort_values("season").reset_index(drop=True)


def write_era_tables(games: pd.DataFrame) -> None:
    flags = pd.DataFrame(
        {
            "game_uid": games["game_uid"],
            "season": games["season"],
            "is_1987_replacement_game": flag_1987_replacement_games(games),
        }
    )
    flags = flags[flags["is_1987_replacement_game"]].drop(columns=["is_1987_replacement_game"])
    flags_path = REPO / "data" / "processed" / "era_flags_1987_replacement_games.csv"
    flags.to_csv(flags_path, index=False)

    meta = season_metadata(games)
    meta_path = REPO / "data" / "reference" / "season_metadata.csv"
    meta.to_csv(meta_path, index=False)

    return flags_path, meta_path


if __name__ == "__main__":
    from models.common import load_games

    flags_path, meta_path = write_era_tables(load_games())
    print(f"Wrote {flags_path}")
    print(f"Wrote {meta_path}")
