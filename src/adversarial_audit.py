"""
Phase 4, part 3: adversarial audit. BUILD_PLAN section 8 calls for "an
adversarial audit listing teams whose ratings conflict with historical
evidence and an explanation or fix for each."

This produces findings and a recommendation - it does not lock the model
family. BUILD_PLAN's own decision log (2026-09-16, Phase 1 tooling entry)
reserves model-selection decisions for Brian and the coordinating
session, not an automated report.

Three checks, in increasing order of how much outside knowledge they
need:

1. Rating-vs-record residuals, computed entirely from our own game log:
   which team-seasons does the (leading, per Phase 2-4) Bayesian model
   rate very differently than their plain win percentage would suggest,
   and can that be explained by margin of victory/defeat, which the game
   log shows directly?
2. Cross-model disagreement: team-seasons where Massey, Bradley-Terry,
   Bayesian and Elo substantially disagree - not necessarily wrong, but
   lower-confidence ratings worth flagging rather than presenting as
   settled.
3. A curated check against a short list of teams whose historical
   reputation is not in serious dispute (undefeated seasons, 0-16
   seasons) - the one place this script relies on outside knowledge,
   clearly marked as such rather than blended in with the data-only
   checks above.
"""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]

# Team-seasons whose historical standing is not seriously disputed -
# general NFL history knowledge, not derived from this project's data,
# used only to sanity-check the leading model rather than to fit it.
KNOWN_BENCHMARKS = {
    (1972, "MIA"): "Only perfect season in NFL history (17-0 including playoffs).",
    (1985, "CHI"): "15-1, dominant defense, won Super Bowl XX by 36.",
    (2007, "NE"): "16-0 regular season, widely regarded as one of the greatest ever.",
    (1991, "WSH"): "14-2, outscored playoff opponents 102-41, won Super Bowl XXVI.",
    (2000, "BAL"): "Historically dominant defense (allowed the fewest points in a 16-game season); offense was weak - a real test of whether a point-margin model still rates a defense-carried team highly.",
    (2008, "DET"): "0-16, the only 0-16 season in the 16-game-schedule era.",
    (2017, "CLE"): "0-16.",
    (1976, "TB"): "0-14, first-year expansion team.",
    (1976, "LAR"): "Beat Atlanta 59-0, part of a dominant regular season.",
    (2011, "NYG"): "9-7 regular season, won the Super Bowl - a common test case for whether a rating agrees with the trophy (BUILD_PLAN deliberately keeps TSR and ACC separate, so a modest TSR here is not itself a conflict).",
}


def load_bayes_ratings() -> pd.DataFrame:
    r = pd.read_csv(REPO / "data" / "processed" / "team_season_ratings.csv")
    return r


def team_season_records(games: pd.DataFrame) -> pd.DataFrame:
    """Regular-season win pct (ties = 0.5) and average margin per
    team-season, computed directly from the game log."""
    reg = games[games["game_type"] == "REG"]
    rows = []
    for season, g in reg.groupby("season"):
        teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
        for team in teams:
            home = g[g["home_franchise"] == team]
            away = g[g["away_franchise"] == team]
            wins = (home["margin"] > 0).sum() + (away["margin"] < 0).sum()
            losses = (home["margin"] < 0).sum() + (away["margin"] > 0).sum()
            ties = (home["margin"] == 0).sum() + (away["margin"] == 0).sum()
            games_played = wins + losses + ties
            win_pct = (wins + 0.5 * ties) / games_played if games_played else np.nan
            point_diff = home["margin"].sum() - away["margin"].sum()
            rows.append(
                {
                    "season": season,
                    "franchise": team,
                    "wins": int(wins),
                    "losses": int(losses),
                    "ties": int(ties),
                    "win_pct": win_pct,
                    "point_diff": int(point_diff),
                    "point_diff_per_game": point_diff / games_played if games_played else np.nan,
                }
            )
    return pd.DataFrame(rows)


def rating_vs_record_residuals(ratings: pd.DataFrame, records: pd.DataFrame) -> pd.DataFrame:
    """Within each season, standardize win_pct the same way ratings are
    standardized (z-score), then compare to the Bayesian model's z-score.
    A large residual means the model's point-margin-based rating and the
    team's plain record tell noticeably different stories - which, since
    win_pct only sees who won, not by how much, is usually explainable by
    margin of victory/defeat, checkable directly in the game log."""
    merged = ratings.merge(records, on=["season", "franchise"])
    merged["win_pct_z"] = merged.groupby("season")["win_pct"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else 0.0
    )
    merged["residual"] = merged["bayes_rating_z"] - merged["win_pct_z"]
    return merged


def cross_model_disagreement(ratings: pd.DataFrame) -> pd.DataFrame:
    z_cols = ["massey_rating_z", "bt_rating_z", "bayes_rating_z", "elo_rating_z"]
    out = ratings.copy()
    out["model_disagreement_sd"] = out[z_cols].std(axis=1, ddof=0)
    return out


def benchmark_check(ratings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (season, team), note in KNOWN_BENCHMARKS.items():
        row = ratings[(ratings["season"] == season) & (ratings["franchise"] == team)]
        if row.empty:
            continue
        row = row.iloc[0]
        season_teams = ratings[ratings["season"] == season]
        rank = int((season_teams["bayes_rating_z"] > row["bayes_rating_z"]).sum() + 1)
        rows.append(
            {
                "season": season,
                "franchise": team,
                "note": note,
                "bayes_rating_z": row["bayes_rating_z"],
                "rank_in_season": rank,
                "n_teams_in_season": len(season_teams),
            }
        )
    return pd.DataFrame(rows)
