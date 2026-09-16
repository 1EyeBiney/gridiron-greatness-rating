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
    the two participants, with each side's full profile attached (suffixed
    winner_*/loser_*) so the page can show more than just the gap."""
    sb = find_super_bowl_games(games)[["season", "winner", "loser", "winner_score", "loser_score"]]
    stat_cols = [c for c in profile.columns if c not in ("season", "franchise")]
    winner_cols = {"franchise": "winner", **{c: f"winner_{c}" for c in stat_cols}}
    loser_cols = {"franchise": "loser", **{c: f"loser_{c}" for c in stat_cols}}
    sb = sb.merge(profile.rename(columns=winner_cols), on=["season", "winner"])
    sb = sb.merge(profile.rename(columns=loser_cols), on=["season", "loser"])
    sb["z_gap"] = sb["winner_bayes_rating_z"] - sb["loser_bayes_rating_z"]
    sb["upset"] = sb["z_gap"] < 0
    return sb.sort_values("z_gap", key=lambda s: s.abs(), ascending=False).head(TOP_N)


def greatest_conference_imbalance(csi: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    """Seasons with the largest |CSI|, plus that season's best AFC and
    best NFC team-season for concrete grounding of the abstract gap."""
    out = csi.copy()
    out["stronger_conference"] = out["csi"].apply(lambda x: "AFC" if x > 0 else "NFC")

    best_by_conf = {}
    for season, g in profile.groupby("season"):
        for conf in ("AFC", "NFC"):
            sub = g[g["conference"] == conf]
            if not sub.empty:
                top = sub.loc[sub["bayes_rating_z"].idxmax()]
                best_by_conf[(season, conf)] = f"{top['franchise']} ({top['bayes_rating_z']:.2f})"

    out["best_afc"] = out["season"].map(lambda s: best_by_conf.get((s, "AFC"), "-"))
    out["best_nfc"] = out["season"].map(lambda s: best_by_conf.get((s, "NFC"), "-"))
    return out.sort_values("csi", key=lambda s: s.abs(), ascending=False).head(TOP_N)


def best_decade(profile: pd.DataFrame) -> pd.DataFrame:
    """Which decade produced the most concentrated excellence at the
    top - the mean True Strength z-score of each decade's 10 highest-
    rated team-seasons. (A simple mean across every team-season would
    average to ~0 in every decade, since z-scores are standardized
    within season by construction - this instead asks which decade's
    *best* teams were furthest above their own league average.) Also
    reports how many team-seasons that decade produced at the "elite"
    threshold used elsewhere on the site (z >= 1.0, see
    src/team_profile.py ELITE_Z_THRESHOLD) and at the mirror-image
    "replacement-level or worse" threshold (z <= -1.0), and the top 3
    team-seasons by name, not just the single best."""
    out = profile.copy()
    out["decade"] = (out["season"] // 10) * 10
    rows = []
    for decade, g in out.groupby("decade"):
        ranked = g.sort_values("bayes_rating_z", ascending=False)
        top10 = ranked.head(10)
        top3 = ranked.head(3)
        rows.append(
            {
                "decade": f"{int(decade)}s",
                "seasons_covered": g["season"].nunique(),
                "mean_top10_tsr_z": top10["bayes_rating_z"].mean(),
                "n_elite_seasons": int((g["bayes_rating_z"] >= 1.0).sum()),
                "n_weak_seasons": int((g["bayes_rating_z"] <= -1.0).sum()),
                "top3_team_seasons": "; ".join(
                    f"{int(r['season'])} {r['franchise']} ({r['bayes_rating_z']:.2f})" for _, r in top3.iterrows()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("mean_top10_tsr_z", ascending=False)


def records_that_most_overstated_strength(profile: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Team-seasons whose record was much better than their True
    Strength Rating - i.e. the record overstates how good they actually
    were, typically a lot of close wins and few but lopsided losses. The
    residual, win_pct, and win_pct_z come from ratings_only/records (via
    rating_vs_record_residuals) to avoid a column collision; every other
    descriptive column is merged back in afterward from profile, which
    duplicates wins/losses/ties/win_pct and so has them dropped first."""
    records = team_season_records(games)
    ratings_only = profile[["season", "franchise", "bayes_rating_z"]]
    merged = rating_vs_record_residuals(ratings_only, records)
    enriched = merged.merge(
        profile.drop(columns=["bayes_rating_z", "wins", "losses", "ties", "win_pct"], errors="ignore"),
        on=["season", "franchise"],
        how="left",
    )
    return enriched.sort_values("residual", ascending=True).head(TOP_N)


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
        "greatest_conference_imbalance": greatest_conference_imbalance(csi, profile),
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
