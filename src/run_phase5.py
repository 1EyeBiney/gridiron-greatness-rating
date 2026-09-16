"""
Phase 5 driver: builds the team-season conference/division table, the
Conference Strength Index, the Accomplishment score, and the descriptive
sub-score profile, then merges all of it plus the locked True Strength
Rating into one master team-season table.

Run from the repo root: `python src/run_phase5.py`.
"""
from pathlib import Path

import pandas as pd

from accomplishment import compute_acc
from conference_strength import build_csi_table
from division_alignment import build_team_season_conference_table
from models.common import load_games
from team_profile import build_profile_table

REPO = Path(__file__).resolve().parents[1]


def main():
    games = load_games()
    ratings = pd.read_csv(REPO / "data" / "processed" / "team_season_ratings.csv")

    print("Building team-season conference/division table...")
    conf_table = build_team_season_conference_table(games)
    conf_path = REPO / "data" / "reference" / "team_season_conference.csv"
    conf_table.to_csv(conf_path, index=False)
    print(f"Wrote {conf_path} ({len(conf_table)} rows)")

    print("Computing Conference Strength Index...")
    csi = build_csi_table(range(1970, 2026))
    csi_path = REPO / "data" / "processed" / "conference_strength_index.csv"
    csi.to_csv(csi_path, index=False)
    print(f"Wrote {csi_path} ({len(csi)} rows)")

    print("Computing Accomplishment scores...")
    acc = compute_acc(games)
    acc_path = REPO / "data" / "processed" / "team_season_accomplishment.csv"
    acc.to_csv(acc_path, index=False)
    print(f"Wrote {acc_path} ({len(acc)} rows)")

    print("Building descriptive sub-score profile...")
    profile = build_profile_table(games, ratings)

    print("Assembling the full team-season table...")
    acc_cols = [
        "season",
        "franchise",
        "wins",
        "losses",
        "ties",
        "win_pct",
        "conference",
        "division",
        "division_title",
        "conference_best_record",
        "playoff_wins",
        "reached_super_bowl",
        "won_super_bowl",
        "acc",
    ]
    full = profile.merge(acc[acc_cols], on=["season", "franchise"], how="left")
    full = full.merge(csi[["season", "csi", "csi_se"]], on="season", how="left")

    full_path = REPO / "data" / "processed" / "team_season_full_profile.csv"
    full.to_csv(full_path, index=False)
    print(f"Wrote {full_path} ({len(full)} rows, {len(full.columns)} columns)")


if __name__ == "__main__":
    main()
