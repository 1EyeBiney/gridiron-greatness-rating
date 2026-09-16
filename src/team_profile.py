"""
Phase 5 team-season profile: descriptive sub-scores (BUILD_PLAN section 3)
computed purely from the game log and the locked model's own ratings,
assembled alongside True Strength Rating and Conference Strength Index
into one per-team-season table. None of these feed True Strength Rating
(BUILD_PLAN section 2, item 3) - they are profile-only context.

Two of BUILD_PLAN's eight listed sub-scores are not computed here:
Roster Quality (needs Approximate Value data - BUILD_PLAN section 11
flags its redistribution rights as an open, unresolved question, the
same category of provenance issue as the Phase 4 spread-data pause) and
Coach Strength Entering Season (needs a head-coach-by-team-season
dataset this project has never acquired). Both are left as an explicit
gap rather than approximated with something that isn't actually them.
"""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]

# BUILD_PLAN doesn't fix a threshold for "elite opponent"; documented
# choice: one full standard deviation above the league mean that season
# (roughly the top sixth of teams), consistent with how every other
# standardized value in this project is expressed.
ELITE_Z_THRESHOLD = 1.0


def _long_games(games: pd.DataFrame, game_type_filter=None) -> pd.DataFrame:
    """Every game viewed from both teams' perspectives: one row per
    (season, team, opponent, margin, points_for, points_against)."""
    g = games if game_type_filter is None else game_type_filter(games)
    home = pd.DataFrame(
        {
            "season": g["season"],
            "team": g["home_franchise"],
            "opponent": g["away_franchise"],
            "margin": g["margin"],
            "points_for": g["home_score"],
            "points_against": g["away_score"],
        }
    )
    away = pd.DataFrame(
        {
            "season": g["season"],
            "team": g["away_franchise"],
            "opponent": g["home_franchise"],
            "margin": -g["margin"],
            "points_for": g["away_score"],
            "points_against": g["home_score"],
        }
    )
    return pd.concat([home, away], ignore_index=True)


def _zscore_within_season(df: pd.DataFrame, col: str) -> pd.Series:
    grouped = df.groupby("season")[col]
    mean = grouped.transform("mean")
    std = grouped.transform(lambda s: s.std(ddof=0))
    return pd.Series(np.where(std > 0, (df[col] - mean) / std, 0.0), index=df.index)


def dominance(games: pd.DataFrame) -> pd.DataFrame:
    """Raw average margin per regular-season game, standardized within
    season - distinct from True Strength Rating, which is schedule-
    adjusted; this is deliberately not."""
    long = _long_games(games, lambda g: g[g["game_type"] == "REG"])
    out = long.groupby(["season", "team"], as_index=False)["margin"].mean()
    out = out.rename(columns={"margin": "avg_margin", "team": "franchise"})
    out["dominance_z"] = _zscore_within_season(out.rename(columns={"franchise": "team"}), "avg_margin")
    return out[["season", "franchise", "avg_margin", "dominance_z"]]


def offense_defense(games: pd.DataFrame) -> pd.DataFrame:
    long = _long_games(games, lambda g: g[g["game_type"] == "REG"])
    out = long.groupby(["season", "team"], as_index=False).agg(
        points_for_per_game=("points_for", "mean"), points_against_per_game=("points_against", "mean")
    )
    out = out.rename(columns={"team": "franchise"})
    tmp = out.rename(columns={"franchise": "team"})
    out["offense_z"] = _zscore_within_season(tmp, "points_for_per_game")
    tmp["points_against_per_game_neg"] = -tmp["points_against_per_game"]
    out["defense_z"] = _zscore_within_season(tmp, "points_against_per_game_neg")
    return out


def schedule_difficulty(games: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    """Average True Strength z-score of every regular-season opponent
    faced - how hard the schedule was, in the same units as the rating
    it's checking against, not a separate scale."""
    long = _long_games(games, lambda g: g[g["game_type"] == "REG"])
    z = ratings[["season", "franchise", "bayes_rating_z"]].rename(
        columns={"franchise": "opponent", "bayes_rating_z": "opponent_z"}
    )
    merged = long.merge(z, on=["season", "opponent"], how="left")
    out = merged.groupby(["season", "team"], as_index=False)["opponent_z"].mean()
    return out.rename(columns={"team": "franchise", "opponent_z": "schedule_difficulty"})


def record_vs_elite(games: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    """Win percentage (ties = 0.5) against regular-season opponents rated
    >= ELITE_Z_THRESHOLD that same season."""
    long = _long_games(games, lambda g: g[g["game_type"] == "REG"])
    z = ratings[["season", "franchise", "bayes_rating_z"]].rename(
        columns={"franchise": "opponent", "bayes_rating_z": "opponent_z"}
    )
    merged = long.merge(z, on=["season", "opponent"], how="left")
    vs_elite = merged[merged["opponent_z"] >= ELITE_Z_THRESHOLD].copy()
    vs_elite["win"] = np.where(vs_elite["margin"] > 0, 1.0, np.where(vs_elite["margin"] < 0, 0.0, 0.5))
    out = vs_elite.groupby(["season", "team"], as_index=False).agg(
        elite_opponents_played=("win", "size"), record_vs_elite_win_pct=("win", "mean")
    )
    return out.rename(columns={"team": "franchise"})


def postseason_evidence(games: pd.DataFrame) -> pd.DataFrame:
    """Average margin in postseason games only - zero rows (NaN) for a
    team that didn't make the playoffs that season."""
    long = _long_games(games, lambda g: g[g["game_type"] != "REG"])
    out = long.groupby(["season", "team"], as_index=False).agg(
        playoff_games=("margin", "size"), playoff_avg_margin=("margin", "mean")
    )
    return out.rename(columns={"team": "franchise"})


def build_profile_table(games: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    profile = ratings[["season", "franchise", "bayes_rating", "bayes_rating_z", "bayes_rating_se", "bayes_rating_display"]].copy()
    for table in (
        dominance(games),
        offense_defense(games),
        schedule_difficulty(games, ratings),
        record_vs_elite(games, ratings),
        postseason_evidence(games),
    ):
        profile = profile.merge(table, on=["season", "franchise"], how="left")
    return profile


if __name__ == "__main__":
    from models.common import load_games

    games = load_games()
    ratings = pd.read_csv(REPO / "data" / "processed" / "team_season_ratings.csv")
    profile = build_profile_table(games, ratings)
    out_path = REPO / "data" / "processed" / "team_season_profile.csv"
    profile.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(profile)} rows, {len(profile.columns)} columns)")
