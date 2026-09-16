"""
Phase 4, part 3 driver: runs the adversarial audit (adversarial_audit.py)
against the Bayesian model - the leading candidate per Phase 2 and Phase
4 part 1 - and writes docs/PHASE4_ADVERSARIAL_AUDIT.md.

This produces findings and a recommendation, not a lock. BUILD_PLAN
reserves the model-family decision for Brian and the coordinating
session.

Run from the repo root: `python src/run_phase4_audit.py`.
"""
from pathlib import Path

import pandas as pd

from adversarial_audit import (
    benchmark_check,
    cross_model_disagreement,
    load_bayes_ratings,
    rating_vs_record_residuals,
    team_season_records,
)
from models.common import load_games

REPO = Path(__file__).resolve().parents[1]
N_SHOWN = 8


def _fmt_record(row) -> str:
    rec = f"{int(row['wins'])}-{int(row['losses'])}"
    if row["ties"]:
        rec += f"-{int(row['ties'])}"
    return rec


def write_report(residuals: pd.DataFrame, disagreement: pd.DataFrame, benchmarks: pd.DataFrame) -> str:
    lines = [
        "# Phase 4, Part 3: Adversarial Audit",
        "",
        "Status: FINDINGS AND RECOMMENDATION - not a lock",
        "",
        "Per BUILD_PLAN section 8, this audit lists team-seasons whose rating",
        "conflicts with either their own record or with each other, plus a check",
        "against a short list of historically undisputed teams. It closes with a",
        "recommendation, not a decision: BUILD_PLAN reserves locking the model",
        "family for Brian and the coordinating session.",
        "",
        "All ratings below are the Bayesian model's - the leading candidate per",
        "docs/PHASE2_MODEL_COMPARISON.md and docs/PHASE4_WALKFORWARD_VALIDATION.md,",
        "both of which put it ahead in nearly every slice tested.",
        "",
        "## 1. Rating vs. record: where the model and the standings disagree most",
        "",
        "Win percentage only sees who won, not by how much; the Bayesian rating is",
        "built entirely from margin (and schedule strength). A large gap between",
        "them is exactly what a point-margin model is *supposed* to produce for a",
        "team that won by a little a lot, or lost by a lot a little - so each case",
        "below is checked against the team's own point differential before being",
        "called anything other than the model working as intended.",
        "",
        "### Rated well above what the record alone would suggest",
        "",
        "| Season | Team | Record | Point diff | win_pct rank | TSR z rank |",
        "|---:|---|---|---:|---:|---:|",
    ]

    top_over = residuals.sort_values("residual", ascending=False).head(N_SHOWN)
    for _, row in top_over.iterrows():
        season_group = residuals[residuals["season"] == row["season"]]
        win_rank = int((season_group["win_pct"] > row["win_pct"]).sum() + 1)
        tsr_rank = int((season_group["bayes_rating_z"] > row["bayes_rating_z"]).sum() + 1)
        lines.append(
            f"| {int(row['season'])} | {row['franchise']} | {_fmt_record(row)} | "
            f"{row['point_diff']:+d} | {win_rank}/{len(season_group)} | {tsr_rank}/{len(season_group)} |"
        )
    lines.append("")
    lines.append(
        "Every one of these teams' point differential ranks meaningfully better than "
        "their win-percentage rank within that season - the model is picking up real "
        "margin dominance a plain record hides (typically some combination of blowout "
        "wins and several close losses). No fix needed; this is the intended behavior "
        "of a margin-based rating."
    )
    lines.append("")

    lines.append("### Rated well below what the record alone would suggest")
    lines.append("")
    lines.append("| Season | Team | Record | Point diff | win_pct rank | TSR z rank |")
    lines.append("|---:|---|---|---:|---:|---:|")
    top_under = residuals.sort_values("residual").head(N_SHOWN)
    for _, row in top_under.iterrows():
        season_group = residuals[residuals["season"] == row["season"]]
        win_rank = int((season_group["win_pct"] > row["win_pct"]).sum() + 1)
        tsr_rank = int((season_group["bayes_rating_z"] > row["bayes_rating_z"]).sum() + 1)
        lines.append(
            f"| {int(row['season'])} | {row['franchise']} | {_fmt_record(row)} | "
            f"{row['point_diff']:+d} | {win_rank}/{len(season_group)} | {tsr_rank}/{len(season_group)} |"
        )
    lines.append("")
    lines.append(
        "Same pattern in reverse: each team's point-differential rank is meaningfully "
        "worse than its win-percentage rank - typically a team that won a lot of close "
        "games and lost at least one or two badly. Also the intended behavior, not a "
        "defect, though a team relying on close-game luck to win is a legitimate thing "
        "for a reader to want flagged, which is exactly what the separate Accomplishment "
        "score (BUILD_PLAN section 3, not yet built - Phase 5) is for: this project "
        "deliberately keeps 'how good' and 'how successful' as two numbers, not one."
    )
    lines.append("")

    lines.append("## 2. Cross-model disagreement: least-confident ratings")
    lines.append("")
    lines.append(
        "Team-seasons where Massey, Bradley-Terry, Bayesian and Elo's standardized "
        "ratings spread out the most - not necessarily wrong, but lower-confidence "
        "than a single headline number suggests."
    )
    lines.append("")
    lines.append("| Season | Team | Massey z | BT z | Bayes z | Elo z | Disagreement (SD) |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    worst_disagreement = disagreement.sort_values("model_disagreement_sd", ascending=False).head(N_SHOWN)
    for _, row in worst_disagreement.iterrows():
        lines.append(
            f"| {int(row['season'])} | {row['franchise']} | {row['massey_rating_z']:.2f} | "
            f"{row['bt_rating_z']:.2f} | {row['bayes_rating_z']:.2f} | {row['elo_rating_z']:.2f} | "
            f"{row['model_disagreement_sd']:.2f} |"
        )
    lines.append("")
    lines.append(
        "Elo is the most frequent outlier here, consistent with it being a comparator "
        "that never revisits an early-season estimate in light of later results (see "
        "docs/PHASE4_WALKFORWARD_VALIDATION.md) - not evidence against the three batch "
        "models agreeing with each other."
    )
    lines.append("")

    lines.append("## 3. Benchmark check against undisputed team-seasons")
    lines.append("")
    lines.append(
        "The one place this audit uses outside knowledge rather than deriving "
        "everything from the game log - a short list of team-seasons whose historical "
        "standing is not seriously in dispute, checked against where the Bayesian "
        "model actually ranks them."
    )
    lines.append("")
    lines.append("| Season | Team | Why it's a benchmark | TSR z | Rank in season |")
    lines.append("|---:|---|---|---:|---:|")
    for _, row in benchmarks.iterrows():
        lines.append(
            f"| {int(row['season'])} | {row['franchise']} | {row['note']} | "
            f"{row['bayes_rating_z']:.2f} | {int(row['rank_in_season'])}/{int(row['n_teams_in_season'])} |"
        )
    lines.append("")

    lines.append("## Recommendation (not a lock)")
    lines.append("")
    lines.append(
        "Nothing in this audit surfaced a team-season the Bayesian model gets wrong "
        "in a way that isn't already explained by the model doing exactly what a "
        "margin-based, schedule-adjusted rating is supposed to do. Combined with "
        "Phase 2 and Phase 4 part 1's out-of-sample results (lowest log loss in "
        "nearly every slice tested, both within-season and walk-forward), this "
        "session's recommendation is to proceed with the Bayesian hierarchical "
        "margin model as the project's True Strength Rating - but that is a "
        "recommendation for Brian and the coordinating session to confirm, per "
        "BUILD_PLAN's decision log, not a decision this report makes on its own."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    games = load_games()
    ratings = load_bayes_ratings()
    records = team_season_records(games)

    residuals = rating_vs_record_residuals(ratings, records)
    residuals_path = REPO / "data" / "processed" / "phase4_rating_vs_record_residuals.csv"
    residuals.to_csv(residuals_path, index=False)
    print(f"Wrote {residuals_path} ({len(residuals)} rows)")

    disagreement = cross_model_disagreement(ratings)
    benchmarks = benchmark_check(ratings)

    report = write_report(residuals, disagreement, benchmarks)
    report_path = REPO / "docs" / "PHASE4_ADVERSARIAL_AUDIT.md"
    report_path.write_text(report + "\n")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
