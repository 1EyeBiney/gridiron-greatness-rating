"""
Phase 2 driver. For every season 1970-2025:
  1. Fit all four candidate models (Massey, Bradley-Terry, Bayesian
     hierarchical margin, Elo) on every game that season - regular season
     and postseason - and collect per-team ratings.
  2. Run the k-fold / prequential out-of-sample comparison in evaluate.py.

Writes:
  data/processed/team_season_ratings.csv - one row per team-season with
    each model's rating (and the Bayesian model's posterior SD).
  data/processed/model_params.csv - one row per season/model with the
    fitted home-field term and other per-model parameters.
  data/processed/phase2_cv_results.csv - the raw per-season, per-model
    cross-validation metrics behind the comparison report.
  docs/PHASE2_MODEL_COMPARISON.md - the human-readable comparison report.

Run from the repo root: `python src/run_phase2.py`, then
`python src/run_phase3.py` - or `python src/run_all.py` for both. This
script rewrites team_season_ratings.csv WITHOUT the z-score columns that
Phase 3 adds, so Phase 3 must always be re-run after Phase 2.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate import evaluate_all_seasons
from models.bayesian_margin import fit_bayesian_margin
from models.bradley_terry import fit_bradley_terry
from models.common import load_games, season_games
from models.elo import final_ratings as elo_final_ratings, run_elo
from models.massey import fit_massey

REPO = Path(__file__).resolve().parents[1]
SEASONS = list(range(1970, 2026))


def build_ratings_tables(games: pd.DataFrame):
    rating_rows = []
    param_rows = []

    for season in SEASONS:
        g = season_games(games, season)

        massey = fit_massey(g)
        bt = fit_bradley_terry(g)
        bayes = fit_bayesian_margin(g)
        elo = elo_final_ratings(run_elo(g))

        teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
        for team in teams:
            rating_rows.append(
                {
                    "season": season,
                    "franchise": team,
                    "massey_rating": massey["ratings"].get(team, np.nan),
                    "bt_rating": bt["ratings"].get(team, np.nan),
                    "bayes_rating": bayes["ratings"].get(team, np.nan),
                    "bayes_rating_se": bayes["ratings_se"].get(team, np.nan),
                    "elo_rating": elo.get(team, np.nan),
                }
            )

        param_rows.extend(
            [
                {"season": season, "model": "massey", "home_adv": massey["home_adv"], "sigma": massey["sigma"]},
                {"season": season, "model": "bradley_terry", "home_adv": bt["home_adv"], "sigma": np.nan},
                {
                    "season": season,
                    "model": "bayesian_margin",
                    "home_adv": bayes["home_adv"],
                    "sigma": bayes["sigma"],
                    "tau": bayes["tau"],
                    "alpha": bayes["alpha"],
                },
            ]
        )

    ratings_df = pd.DataFrame.from_records(rating_rows)
    params_df = pd.DataFrame.from_records(param_rows)
    return ratings_df, params_df


def write_comparison_report(cv: pd.DataFrame, params: pd.DataFrame) -> str:
    lines = [
        "# Phase 2: Candidate Model Comparison",
        "",
        "Status: COMPLETE",
        f"Seasons covered: {SEASONS[0]}-{SEASONS[-1]} ({len(SEASONS)} seasons, every game - regular season and",
        "postseason, per BUILD_PLAN section 2).",
        "",
        "## Method",
        "",
        "Massey (ordinary least squares on blowout-capped margin), Bradley-Terry",
        "(margin-weighted logistic win/loss), and the Bayesian hierarchical margin",
        "model (ridge regression with an empirical-Bayes shrinkage prior) are each",
        "evaluated by 5-fold cross-validation within every season: fit on 4/5 of that",
        "season's games, predict the held-out 1/5, repeat for all 5 folds, and",
        "pool the results. Elo is evaluated prequentially instead (see src/evaluate.py",
        "and src/models/elo.py for why its evaluation is not k-fold), so its numbers",
        "are informative but not from an identical protocol.",
        "",
        "Metrics: log loss on the win/loss outcome (ties count as a 0.5 outcome),",
        "mean absolute error on the point margin (undefined for Bradley-Terry, which",
        "only ever targets win/loss), and plain win/decided-game accuracy.",
        "",
        "This is Phase 2's first predictive-accuracy look, run to see whether one",
        "model family is obviously and consistently ahead of the others. It is not",
        "Phase 4's validation: no held-out future weeks, no spread comparison, no",
        "adversarial audit, and no model family is locked in by this report.",
        "",
        "## Aggregate results (all seasons pooled, game-count weighted)",
        "",
    ]

    agg = (
        cv.groupby("model")
        .apply(
            lambda d: pd.Series(
                {
                    "n_games": d["n"].sum(),
                    "log_loss": np.average(d["log_loss"], weights=d["n"]),
                    "margin_mae": (
                        np.average(d["margin_mae"].dropna(), weights=d.loc[d["margin_mae"].notna(), "n"])
                        if d["margin_mae"].notna().any()
                        else np.nan
                    ),
                    "accuracy": np.average(d["accuracy"], weights=d["n"]),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        .sort_values("log_loss")
    )

    lines.append("| Model | Games scored | Log loss | Margin MAE | Accuracy |")
    lines.append("|---|---:|---:|---:|---:|")
    for _, row in agg.iterrows():
        mae = f"{row['margin_mae']:.2f}" if pd.notna(row["margin_mae"]) else "n/a"
        lines.append(
            f"| {row['model']} | {int(row['n_games'])} | {row['log_loss']:.4f} | {mae} | {row['accuracy']:.3f} |"
        )
    lines.append("")
    lines.append("Lower log loss and margin MAE are better; higher accuracy is better.")
    lines.append("")

    lines.append("## By era (log loss, game-count weighted)")
    lines.append("")
    cv2 = cv.copy()
    cv2["era"] = pd.cut(
        cv2["season"],
        bins=[1969, 1977, 1994, 2010, 2026],
        labels=["1970-1977 (14-game)", "1978-1994", "1995-2010", "2011-2025"],
    )
    era_agg = (
        cv2.groupby(["era", "model"], observed=True)
        .apply(lambda d: np.average(d["log_loss"], weights=d["n"]), include_groups=False)
        .reset_index(name="log_loss")
        .pivot(index="era", columns="model", values="log_loss")
    )
    lines.append("| Era | " + " | ".join(era_agg.columns) + " |")
    lines.append("|---|" + "---:|" * len(era_agg.columns))
    for era, row in era_agg.iterrows():
        lines.append(f"| {era} | " + " | ".join(f"{v:.4f}" for v in row) + " |")
    lines.append("")

    lines.append("## Fitted home-field advantage (mean across seasons)")
    lines.append("")
    hf = params[params["model"].isin(["massey", "bradley_terry", "bayesian_margin"])]
    hf_summary = hf.groupby("model")["home_adv"].agg(["mean", "std"]).reset_index()
    lines.append("| Model | Mean home_adv | SD across seasons |")
    lines.append("|---|---:|---:|")
    for _, row in hf_summary.iterrows():
        unit = "points" if row["model"] != "bradley_terry" else "log-odds"
        lines.append(f"| {row['model']} | {row['mean']:.3f} {unit} | {row['std']:.3f} |")
    lines.append("")
    lines.append(
        "Massey and the Bayesian model fit home-field advantage directly in points; "
        "Bradley-Terry fits it in log-odds, so its number is not on the same scale."
    )
    lines.append("")

    lines.append("## Reading these results")
    lines.append("")
    lines.append(
        "See docs/PHASE2_SUMMARY.md for the interpretation and the recommendation "
        "carried into Phase 3."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    games = load_games()

    print("Fitting all four models for every season...")
    ratings_df, params_df = build_ratings_tables(games)
    ratings_path = REPO / "data" / "processed" / "team_season_ratings.csv"
    params_path = REPO / "data" / "processed" / "model_params.csv"
    ratings_df.to_csv(ratings_path, index=False)
    params_df.to_csv(params_path, index=False)
    print(f"Wrote {ratings_path} ({len(ratings_df)} rows)")
    print(f"Wrote {params_path} ({len(params_df)} rows)")

    print("Running cross-validation comparison (this fits every model 5x per season)...")
    cv_results = evaluate_all_seasons(SEASONS)
    cv_path = REPO / "data" / "processed" / "phase2_cv_results.csv"
    cv_results.to_csv(cv_path, index=False)
    print(f"Wrote {cv_path} ({len(cv_results)} rows)")

    report = write_comparison_report(cv_results, params_df)
    report_path = REPO / "docs" / "PHASE2_MODEL_COMPARISON.md"
    report_path.write_text(report + "\n")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
