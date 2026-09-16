"""
Phase 6 query pages, BUILD_PLAN section 8: "greatest champions, weakest
champions, greatest losers, best teams never to win, largest mismatches,
greatest conference imbalance, best decade, records that most overstated
strength."

Every ranking uses the locked Bayesian model's True Strength z-score
(bayes_rating_z) - the canonical cross-era value per BUILD_PLAN section 5
- so a 1972 team and a 2024 team are compared on equal footing.
"""
from pathlib import Path

import pandas as pd

from accomplishment import find_super_bowl_games
from adversarial_audit import rating_vs_record_residuals, team_season_records
from models.common import load_games

REPO = Path(__file__).resolve().parents[1]
TOP_N = 15


def greatest_champions(profile: pd.DataFrame) -> pd.DataFrame:
    return profile[profile["won_super_bowl"]].sort_values("bayes_rating_z", ascending=False).head(TOP_N)


def weakest_champions(profile: pd.DataFrame) -> pd.DataFrame:
    return profile[profile["won_super_bowl"]].sort_values("bayes_rating_z", ascending=True).head(TOP_N)


def greatest_losers(profile: pd.DataFrame) -> pd.DataFrame:
    """Super Bowl runners-up, ranked by how strong they were anyway."""
    mask = profile["reached_super_bowl"] & ~profile["won_super_bowl"]
    return profile[mask].sort_values("bayes_rating_z", ascending=False).head(TOP_N)


def best_teams_never_to_win(profile: pd.DataFrame) -> pd.DataFrame:
    """Highest True Strength of any team-season that did not win that
    year's Super Bowl - not restricted to teams that even made the
    playoffs, since the question is about strength, not the trophy."""
    return profile[~profile["won_super_bowl"]].sort_values("bayes_rating_z", ascending=False).head(TOP_N)


def largest_mismatches(profile: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Super Bowl matchups with the largest True Strength gap between
    the two participants."""
    sb = find_super_bowl_games(games)[["season", "winner", "loser", "winner_score", "loser_score"]]
    z = profile[["season", "franchise", "bayes_rating_z"]]
    sb = sb.merge(z.rename(columns={"franchise": "winner", "bayes_rating_z": "winner_z"}), on=["season", "winner"])
    sb = sb.merge(z.rename(columns={"franchise": "loser", "bayes_rating_z": "loser_z"}), on=["season", "loser"])
    sb["z_gap"] = sb["winner_z"] - sb["loser_z"]
    sb["upset"] = sb["z_gap"] < 0
    return sb.sort_values("z_gap", key=lambda s: s.abs(), ascending=False).head(TOP_N)


def greatest_conference_imbalance(csi: pd.DataFrame) -> pd.DataFrame:
    out = csi.copy()
    out["stronger_conference"] = out["csi"].apply(lambda x: "AFC" if x > 0 else "NFC")
    return out.sort_values("csi", key=lambda s: s.abs(), ascending=False).head(TOP_N)


def best_decade(profile: pd.DataFrame) -> pd.DataFrame:
    """Which decade produced the most concentrated excellence at the
    top - the mean True Strength z-score of each decade's 10 highest-
    rated team-seasons. (A simple mean across every team-season would
    average to ~0 in every decade, since z-scores are standardized
    within season by construction - this instead asks which decade's
    *best* teams were furthest above their own league average.)"""
    out = profile.copy()
    out["decade"] = (out["season"] // 10) * 10
    rows = []
    for decade, g in out.groupby("decade"):
        top10 = g.sort_values("bayes_rating_z", ascending=False).head(10)
        rows.append(
            {
                "decade": f"{int(decade)}s",
                "mean_top10_tsr_z": top10["bayes_rating_z"].mean(),
                "best_team_season": f"{int(top10.iloc[0]['season'])} {top10.iloc[0]['franchise']}",
                "best_tsr_z": top10.iloc[0]["bayes_rating_z"],
            }
        )
    return pd.DataFrame(rows).sort_values("mean_top10_tsr_z", ascending=False)


def records_that_most_overstated_strength(profile: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Team-seasons whose record was much better than their True
    Strength Rating - i.e. the record overstates how good they actually
    were, typically a lot of close wins and few but lopsided losses."""
    records = team_season_records(games)
    ratings_only = profile[["season", "franchise", "bayes_rating_z"]]
    merged = rating_vs_record_residuals(ratings_only, records)
    return merged.sort_values("residual", ascending=True).head(TOP_N)


def build_all_queries() -> dict:
    games = load_games()
    profile = pd.read_csv(REPO / "data" / "processed" / "team_season_full_profile.csv")
    csi = pd.read_csv(REPO / "data" / "processed" / "conference_strength_index.csv")

    return {
        "greatest_champions": greatest_champions(profile),
        "weakest_champions": weakest_champions(profile),
        "greatest_losers": greatest_losers(profile),
        "best_teams_never_to_win": best_teams_never_to_win(profile),
        "largest_mismatches": largest_mismatches(profile, games),
        "greatest_conference_imbalance": greatest_conference_imbalance(csi),
        "best_decade": best_decade(profile),
        "records_that_most_overstated_strength": records_that_most_overstated_strength(profile, games),
    }


if __name__ == "__main__":
    out_dir = REPO / "data" / "processed" / "queries"
    out_dir.mkdir(exist_ok=True)
    for name, table in build_all_queries().items():
        path = out_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        print(f"Wrote {path} ({len(table)} rows)")
