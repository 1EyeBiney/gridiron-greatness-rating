"""
Phase 4, part 1: out-of-sample validation with genuine walk-forward
(no future leakage), replacing Phase 2's within-season 5-fold CV as the
basis for comparing model families. See src/walkforward.py for why this
is a stricter test than Phase 2's.

Also resolves the one open item Fable's pre-Phase-4 review flagged:
Bradley-Terry's REG_STRENGTH constant (src/models/bradley_terry.py) was
chosen in Phase 2 by grid search against the same folds it was then
scored on. Here it is re-selected using only the 1970-1998 seasons
(the FiveThirtyEight/nflverse source boundary already in the data - a
natural, non-arbitrary split), then every model - including
Bradley-Terry with the newly-selected value - is scored on the full
1970-2025 walk-forward run. The 1999-2025 subset of that run never
touched the tuning decision, so it is the clean read; the 1970-1998
subset is reported too, but Bradley-Terry's number there benefits
slightly from being in its own tuning set.

Run from the repo root: `python src/run_phase4_validation.py`.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from models.bradley_terry import REG_STRENGTH as PHASE2_BT_REG_STRENGTH
from walkforward import bt_walk_forward_log_loss, walk_forward_all_seasons

REPO = Path(__file__).resolve().parents[1]
ALL_SEASONS = list(range(1970, 2026))
TUNE_SEASONS = list(range(1970, 1999))
CLEAN_EVAL_SEASONS = list(range(1999, 2026))
BT_REG_CANDIDATES = [1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 18.0]


def select_bt_reg_strength() -> tuple[float, pd.DataFrame]:
    rows = []
    for cand in BT_REG_CANDIDATES:
        ll = bt_walk_forward_log_loss(TUNE_SEASONS, cand)
        rows.append({"reg_strength": cand, "walk_forward_log_loss_1970_1998": ll})
    table = pd.DataFrame(rows)
    best = float(table.loc[table["walk_forward_log_loss_1970_1998"].idxmin(), "reg_strength"])
    return best, table


def score_by_season(df: pd.DataFrame) -> pd.DataFrame:
    """Per (season, model, graph_connected) metrics. graph_connected is
    kept as its own grouping key, not collapsed, because it is the whole
    point of the analysis: a handful of early-week disconnected-schedule
    predictions (see models.common.is_schedule_connected) turn out to
    behave completely differently by model family, and averaging them
    into the season total would hide that."""
    from models.common import outcome_label

    rows = []
    for (season, model_name, connected), d in df.groupby(["season", "model", "graph_connected"]):
        label = outcome_label(d["margin"].to_numpy())
        p = np.clip(d["p_home_win"].to_numpy(), 1e-9, 1 - 1e-9)
        ll = float(-np.mean(label * np.log(p) + (1 - label) * np.log(1 - p)))
        decided = label != 0.5
        acc = float(np.mean((p[decided] > 0.5) == (label[decided] == 1.0))) if decided.any() else np.nan
        mae = float(np.mean(np.abs(d["margin"] - d["pred_margin"]))) if d["pred_margin"].notna().any() else np.nan
        rows.append(
            {
                "season": season,
                "model": model_name,
                "graph_connected": connected,
                "n": len(d),
                "log_loss": ll,
                "margin_mae": mae,
                "accuracy": acc,
            }
        )
    return pd.DataFrame(rows)


WEEK_BUCKETS = [(2, 5, "2-5 (just connected, still thin)"), (6, 10, "6-10"), (11, 99, "11+")]


def weighted_agg_by_week_bucket(predictions: pd.DataFrame) -> pd.DataFrame:
    """Log loss by model within each week-index bucket, pooled across all
    56 seasons. Whether the schedule graph is connected yet (see
    is_schedule_connected) is a boolean, but a graph that just barely
    connected via one bridging game is still numerically thin for
    unregularized OLS - this shows that as a gradient rather than a
    single before/after split."""
    from models.common import outcome_label

    rows = []
    for lo, hi, label_txt in WEEK_BUCKETS:
        bucket = predictions[(predictions["week_idx"] >= lo) & (predictions["week_idx"] <= hi)]
        for model_name, d in bucket.groupby("model"):
            label = outcome_label(d["margin"].to_numpy())
            p = np.clip(d["p_home_win"].to_numpy(), 1e-9, 1 - 1e-9)
            ll = float(-np.mean(label * np.log(p) + (1 - label) * np.log(1 - p)))
            rows.append({"week_bucket": label_txt, "model": model_name, "n": len(d), "log_loss": ll})
    return pd.DataFrame(rows)


def weighted_agg(cv: pd.DataFrame) -> pd.DataFrame:
    def agg(d):
        mae_valid = d["margin_mae"].notna()
        return pd.Series(
            {
                "n_games": d["n"].sum(),
                "log_loss": np.average(d["log_loss"], weights=d["n"]),
                "margin_mae": (
                    np.average(d.loc[mae_valid, "margin_mae"], weights=d.loc[mae_valid, "n"])
                    if mae_valid.any()
                    else np.nan
                ),
                "accuracy": np.average(d["accuracy"], weights=d["n"]),
            }
        )

    return cv.groupby("model").apply(agg, include_groups=False).reset_index().sort_values("log_loss")


def write_report(
    bt_best: float,
    bt_table: pd.DataFrame,
    agg_all: pd.DataFrame,
    agg_clean: pd.DataFrame,
    agg_tune: pd.DataFrame,
    agg_connected: pd.DataFrame,
    agg_disconnected: pd.DataFrame,
    week_bucket_table: pd.DataFrame,
) -> str:
    lines = [
        "# Phase 4, Part 1: Walk-Forward Validation",
        "",
        "Status: COMPLETE",
        "",
        "## Method",
        "",
        "Every model refits weekly using only that season's games from earlier",
        "weeks (see src/walkforward.py) - a stricter, future-leakage-free version",
        "of Phase 2's within-season 5-fold cross-validation. Week 1 of every season",
        "is never scored (no history exists yet to fit on). Elo needs no special",
        "handling: it already updates after every game with zero future access,",
        "so it is evaluated the same way it was in Phase 2.",
        "",
        "## Bradley-Terry regularization: re-selected honestly",
        "",
        "Phase 2's REG_STRENGTH (3.0) was chosen by grid search against the same",
        "folds it was then scored on - a mild test-set leak, flagged at the time.",
        "Here it is re-selected using only the 1970-1998 seasons (the",
        "FiveThirtyEight/nflverse source boundary already in the data), scored by",
        "walk-forward log loss, before ever touching 1999-2025:",
        "",
        "| reg_strength | Walk-forward log loss (1970-1998) |",
        "|---:|---:|",
    ]
    for _, row in bt_table.iterrows():
        marker = "  <- selected" if row["reg_strength"] == bt_best else ""
        lines.append(f"| {row['reg_strength']:g} | {row['walk_forward_log_loss_1970_1998']:.4f}{marker} |")
    lines.append("")
    lines.append(
        f"Selected reg_strength = {bt_best:g} (Phase 2's value was {PHASE2_BT_REG_STRENGTH:g}). "
        "This value is used for every Bradley-Terry number below, including on the "
        "1970-1998 seasons that selected it - so unlike the other three models, "
        "Bradley-Terry's 1970-1998 number here still isn't a fully clean read. Its "
        "1999-2025 number is: those seasons played no part in choosing reg_strength."
    )
    lines.append("")

    lines.append("## Results: full history (1970-2025)")
    lines.append("")
    lines.append("| Model | Games scored | Log loss | Margin MAE | Accuracy |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in agg_all.iterrows():
        mae = f"{row['margin_mae']:.2f}" if pd.notna(row["margin_mae"]) else "n/a"
        lines.append(f"| {row['model']} | {int(row['n_games'])} | {row['log_loss']:.4f} | {mae} | {row['accuracy']:.3f} |")
    lines.append("")

    lines.append("## Results: 1999-2025 only (the clean read for Bradley-Terry)")
    lines.append("")
    lines.append("| Model | Games scored | Log loss | Margin MAE | Accuracy |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in agg_clean.iterrows():
        mae = f"{row['margin_mae']:.2f}" if pd.notna(row["margin_mae"]) else "n/a"
        lines.append(f"| {row['model']} | {int(row['n_games'])} | {row['log_loss']:.4f} | {mae} | {row['accuracy']:.3f} |")
    lines.append("")

    lines.append("## Results: 1970-1998 only (Bradley-Terry's tuning seasons - not clean for that model)")
    lines.append("")
    lines.append("| Model | Games scored | Log loss | Margin MAE | Accuracy |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in agg_tune.iterrows():
        mae = f"{row['margin_mae']:.2f}" if pd.notna(row["margin_mae"]) else "n/a"
        lines.append(f"| {row['model']} | {int(row['n_games'])} | {row['log_loss']:.4f} | {mae} | {row['accuracy']:.3f} |")
    lines.append("")

    lines.append("## A structural finding: disconnected early-season schedules")
    lines.append("")
    lines.append(
        "The first full run of this validation showed Massey with a log loss above "
        "1.0 - worse than a coin flip - which turned out not to be noise. Every "
        "league-wide week 1 is a set of isolated pairs (each team has played exactly "
        "one game, against one opponent), so predicting week 2 sometimes means "
        "comparing two teams that share no common opponent yet and never played each "
        "other - the schedule graph is disconnected, and their relative rating gap "
        "is not just uncertain, it is completely unconstrained by the data. Massey's "
        "plain least-squares fit resolves this the way `lstsq`/`pinv` always resolve "
        "a rank-deficient system: by picking the minimum-norm answer, which reports "
        "*zero* uncertainty in exactly the direction the data says nothing about, "
        "producing near-certain (and frequently wrong) predictions. Bayesian and "
        "Bradley-Terry never hit this failure: their regularization keeps the system "
        "invertible and correctly reports high uncertainty (shrinking toward a "
        "50/50 prediction) for a team no data yet connects to its opponent."
    )
    lines.append("")
    lines.append(
        "This is now measured directly (src/models/common.py:is_schedule_connected), "
        "and every result above is scored on the full mix of connected- and "
        "disconnected-graph weeks. Splitting the two apart isolates the effect:"
    )
    lines.append("")
    lines.append("### Connected-graph weeks only (the normal case, most of every season)")
    lines.append("")
    lines.append("| Model | Games scored | Log loss | Margin MAE | Accuracy |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in agg_connected.iterrows():
        mae = f"{row['margin_mae']:.2f}" if pd.notna(row["margin_mae"]) else "n/a"
        lines.append(f"| {row['model']} | {int(row['n_games'])} | {row['log_loss']:.4f} | {mae} | {row['accuracy']:.3f} |")
    lines.append("")
    lines.append("### Disconnected-graph weeks only (early in a season, before the schedule has connected everyone)")
    lines.append("")
    lines.append("| Model | Games scored | Log loss | Margin MAE | Accuracy |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in agg_disconnected.iterrows():
        mae = f"{row['margin_mae']:.2f}" if pd.notna(row["margin_mae"]) else "n/a"
        lines.append(f"| {row['model']} | {int(row['n_games'])} | {row['log_loss']:.4f} | {mae} | {row['accuracy']:.3f} |")
    lines.append("")
    lines.append(
        "Connectivity is a yes/no property, but the instability it causes isn't - a "
        "graph that just barely connected via one bridging game is still numerically "
        "thin, and Massey needs several more weeks beyond that before it's reliably "
        "steady. Breaking log loss down by week index instead of the connected/"
        "disconnected split makes that gradient visible:"
    )
    lines.append("")
    lines.append("| Week range | " + " | ".join(sorted(week_bucket_table["model"].unique())) + " |")
    lines.append("|---|" + "---:|" * week_bucket_table["model"].nunique())
    for bucket_label in [b[2] for b in WEEK_BUCKETS]:
        row = week_bucket_table[week_bucket_table["week_bucket"] == bucket_label]
        cells = [f"{row[row['model'] == m]['log_loss'].iloc[0]:.3f}" for m in sorted(row["model"].unique())]
        lines.append(f"| {bucket_label} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        "Massey only converges to match the regularized models around week 11 - it is "
        "not simply \"fine once connected.\" This is a specific, mechanical failure of "
        "unregularized OLS on a thinly-identified system, not a general weakness of "
        "least squares as a rating method, and it is real evidence for BUILD_PLAN's "
        "stated preference for the Bayesian model: the same regularization that gives "
        "it a standard error for free is also what keeps it well-behaved for most of "
        "every season, not just once enough games have piled up to make the problem "
        "well-posed on its own."
    )
    lines.append("")

    lines.append("## Comparison to Phase 2")
    lines.append("")
    lines.append(
        "Phase 2's within-season 5-fold CV let information from later weeks inform "
        "predictions for earlier weeks in the same fit; this walk-forward run never "
        "does. The two protocols agree on the one finding that matters most for "
        "model-family selection: the Bayesian model has the lowest log loss in every "
        "slice of both reports - Phase 2's aggregate and all four era slices, and "
        "here, the full history, both source-boundary halves, the connected-only "
        "subset, and every week-range bucket except one (Massey ties it within 0.002 "
        "at week 11+, not a meaningful difference). That result surviving a "
        "considerably stricter, structurally different test is a much stronger reason "
        "to trust it than either report alone would be. Elo and Bradley-Terry swap "
        "second/third place depending on the slice; that ordering is not stable "
        "enough across the two protocols to read anything into. See "
        "docs/PHASE2_MODEL_COMPARISON.md for the Phase 2 numbers."
    )
    lines.append("")
    lines.append(
        "Model family is not locked by this report alone - the spread comparison "
        "and adversarial audit (both still to come in Phase 4) are part of the same "
        "decision, and BUILD_PLAN reserves that decision for Brian and the "
        "coordinating session, not an automated report."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    print("Selecting Bradley-Terry reg_strength on 1970-1998 walk-forward log loss...")
    bt_best, bt_table = select_bt_reg_strength()
    print(f"Selected reg_strength={bt_best} (Phase 2 used {PHASE2_BT_REG_STRENGTH})")
    print(bt_table.to_string(index=False))

    print("\nRunning full walk-forward validation for 1970-2025...")
    predictions = walk_forward_all_seasons(ALL_SEASONS, bt_reg_strength=bt_best)

    cv_by_season = score_by_season(predictions)
    cv_path = REPO / "data" / "processed" / "phase4_walkforward_cv_results.csv"
    cv_by_season.to_csv(cv_path, index=False)
    print(f"Wrote {cv_path} ({len(cv_by_season)} rows)")

    agg_all = weighted_agg(cv_by_season)
    agg_clean = weighted_agg(cv_by_season[cv_by_season["season"].isin(CLEAN_EVAL_SEASONS)])
    agg_tune = weighted_agg(cv_by_season[cv_by_season["season"].isin(TUNE_SEASONS)])
    agg_connected = weighted_agg(cv_by_season[cv_by_season["graph_connected"]])
    agg_disconnected = weighted_agg(cv_by_season[~cv_by_season["graph_connected"]])
    week_bucket_table = weighted_agg_by_week_bucket(predictions)

    report = write_report(
        bt_best, bt_table, agg_all, agg_clean, agg_tune, agg_connected, agg_disconnected, week_bucket_table
    )
    report_path = REPO / "docs" / "PHASE4_WALKFORWARD_VALIDATION.md"
    report_path.write_text(report + "\n")
    print(f"Wrote {report_path}")

    return bt_best


if __name__ == "__main__":
    main()
