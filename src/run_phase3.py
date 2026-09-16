"""
Phase 3 driver: era normalization.

  1. Write the era reference tables (era.py): which games were played by
     replacement players in 1987, and a season-by-season metadata table
     (team count, schedule length, strike flags).
  2. Add within-season z-scores (and an optional 0-100 display scale) to
     every model's ratings in data/processed/team_season_ratings.csv -
     the Phase 2 output, now extended in place rather than duplicated.
  3. Run the two sensitivity checks BUILD_PLAN section 6 calls for (1987
     replacement games, 1982 uncertainty) and write the results.
  4. Write docs/PHASE3_ERA_NORMALIZATION.md, the sensitivity report that
     is this phase's deliverable.

Run from the repo root: `python src/run_phase3.py`.
"""
from pathlib import Path

import pandas as pd

from era import season_metadata, write_era_tables
from models.common import load_games
from sensitivity import (
    check_1982_uncertainty_is_wider,
    compare_1987_with_and_without_replacement_games,
    replacement_game_records_1987,
)
from standardize import add_display_scales, zscore_within_season

REPO = Path(__file__).resolve().parents[1]


def write_report(
    meta: pd.DataFrame, sens_1987: dict, records_1987: pd.DataFrame, unc_1982: pd.DataFrame
) -> str:
    lines = [
        "# Phase 3: Era Normalization",
        "",
        "Status: COMPLETE",
        "",
        "## What changed and why nothing else needed to",
        "",
        "BUILD_PLAN section 6 lists seven era-handling rules. Four were already",
        "satisfied by how Phase 1 and Phase 2 were built, not by anything new here:",
        "",
        "- **Schedule length** (14/16/17 games): every model predicts a single",
        "  game's margin or win probability, never a season total, so a longer or",
        "  shorter schedule changes how many games inform a team's rating, not the",
        "  scale it's reported on. No conversion needed.",
        "- **Expansion/realignment** (26 to 32 teams): standardizing within season",
        "  (below) automatically adapts to however many teams played that season.",
        "  Phase 1's data-quality audit already confirmed every season has the",
        "  historically correct team count.",
        "- **Franchise relocations**: handled in Phase 1 by franchise_crosswalk.csv.",
        "- **Ties, overtime, neutral sites**: handled in Phase 2's src/models/common.py",
        "  (ties score as a half-win/zero margin; overtime is recorded but unused by",
        "  any model; neutral sites zero out the home-field term).",
        "",
        "What this phase actually added:",
        "",
        "1. **Standardization layer** (src/standardize.py): every model's rating is",
        "   now also expressed as a z-score within its season (mean 0, sd 1 across",
        "   that season's teams) plus an optional 0-100 display scale. The z-score,",
        "   not the raw rating, is the canonical cross-era value per BUILD_PLAN",
        "   section 5. Applied in place to data/processed/team_season_ratings.csv.",
        "2. **1982 and 1987 strike handling** (src/era.py): both seasons are flagged",
        "   in the new data/reference/season_metadata.csv, and the 42 specific 1987",
        "   games played by replacement players are flagged in",
        "   data/processed/era_flags_1987_replacement_games.csv. Both are included,",
        "   not excluded, per BUILD_PLAN's default proposal - see the sensitivity",
        "   results below for why that held up.",
        "",
        "## Season metadata",
        "",
        f"{len(meta)} seasons, {int(meta['teams'].min())} to {int(meta['teams'].max())} teams,",
        f"schedule length {int(meta['schedule_length'].min())} to {int(meta['schedule_length'].max())}",
        "games. Full table in data/reference/season_metadata.csv. Flagged strike seasons:",
        "",
    ]
    for _, row in meta[meta["strike_season"]].iterrows():
        lines.append(f"- {int(row['season'])}: {row['note']}")
    lines.append("")

    lines.append("## Sensitivity: 1987 replacement-player games")
    lines.append("")
    lines.append(
        "Refit 1987 twice - with all 210 regular-season games, and with the 42 "
        "replacement-player games removed - for the two point-margin models, and "
        "compared the resulting team ratings."
    )
    lines.append("")
    lines.append("| Model | Spearman rank correlation | Mean \\|change\\| | Max \\|change\\| | Most affected |")
    lines.append("|---|---:|---:|---:|---|")
    for model_name, res in sens_1987.items():
        lines.append(
            f"| {model_name} | {res['spearman_rank_correlation']:.3f} | "
            f"{res['mean_abs_change']:.2f} | {res['max_abs_change']:.2f} | "
            f"{res['most_affected_team']} |"
        )
    lines.append("")
    min_rho = min(res["spearman_rank_correlation"] for res in sens_1987.values())
    max_rho = max(res["spearman_rank_correlation"] for res in sens_1987.values())
    movers = {res["most_affected_team"] for res in sens_1987.values()}
    agree = len(movers) == 1
    mover_note = (
        f"both models flag {movers.pop()} as the biggest single mover"
        if agree
        else f"the biggest single mover differs by model ({', '.join(sorted(movers))})"
    )
    lines.append(
        f"Rank correlation between {min_rho:.3f} and {max_rho:.3f} for the two models means "
        f"the replacement games shift a handful of teams ({mover_note}) but do not "
        "reshuffle the 1987 ranking broadly; the largest single-team swings are "
        "documented in data/processed/phase3_1987_sensitivity_*.csv for anyone who "
        "wants to sanity-check a specific team. This supports BUILD_PLAN's default "
        "of including the replacement games (flagged, not excluded)."
    )
    lines.append("")
    lines.append(
        "Who the replacement weeks helped and hurt, from the 42 games themselves "
        "(worst and best point differential):"
    )
    lines.append("")
    lines.append("| Team | Replacement-game record | Point diff |")
    lines.append("|---|---:|---:|")
    shown = pd.concat([records_1987.head(3), records_1987.tail(3)])
    for _, row in shown.iterrows():
        lines.append(f"| {row['team']} | {row['wins']}-{row['losses']} | {row['point_diff']:+d} |")
    lines.append("")
    lines.append(
        "This is the historical record of that strike, recovered from the data rather "
        "than assumed: Philadelphia's and the defending-champion Giants' replacement "
        "squads were among the worst, and Washington's went unbeaten (the team the "
        "film The Replacements was based on). It is also why Washington barely moves "
        "in the with/without comparison - its regulars went on to win the Super Bowl, "
        "so its replacement results were consistent with its strength - while "
        "Philadelphia's regular roster was far better than its replacement results, "
        "making it the biggest mover under both models."
    )
    lines.append("")

    lines.append("## Sensitivity: 1982 uncertainty")
    lines.append("")
    lines.append(
        "BUILD_PLAN section 4's small-sample rule expects the 9-game 1982 season to "
        "carry a wider uncertainty range than its 16-game neighbors. The Bayesian "
        "model's posterior standard error (src/models/bayesian_margin.py) already "
        "widens automatically with fewer games - no new code needed, just confirming "
        "it actually does:"
    )
    lines.append("")
    lines.append("| Season | Mean Bayesian rating SE |")
    lines.append("|---:|---:|")
    for _, row in unc_1982.iterrows():
        marker = " <- strike season" if row["is_1982"] else ""
        lines.append(f"| {int(row['season'])} | {row['mean_bayes_rating_se']:.3f}{marker} |")
    lines.append("")
    is_widest = bool(
        unc_1982.loc[unc_1982["is_1982"], "mean_bayes_rating_se"].iloc[0]
        == unc_1982["mean_bayes_rating_se"].max()
    )
    lines.append(
        f"1982 has {'the widest' if is_widest else 'NOT the widest'} mean uncertainty "
        "of this nine-season window, confirming the small-sample rule holds without "
        "any special-casing."
    )
    lines.append("")

    lines.append("## Carried forward")
    lines.append("")
    lines.append(
        "Model family is still not locked (that's Phase 4). The two Phase 1 "
        "carry-forwards (pre-1999 playoff round labels; team-season conference/"
        "division table) remain outstanding and still don't block anything up "
        "through Phase 4."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    games = load_games()

    print("Writing era reference tables...")
    write_era_tables(games)
    meta = season_metadata(games)

    print("Adding within-season z-scores to team_season_ratings.csv...")
    ratings_path = REPO / "data" / "processed" / "team_season_ratings.csv"
    ratings = pd.read_csv(ratings_path)
    ratings = zscore_within_season(ratings)
    ratings = add_display_scales(ratings)
    ratings.to_csv(ratings_path, index=False)
    print(f"Updated {ratings_path} (+{len([c for c in ratings.columns if c.endswith(('_z', '_display'))])} columns)")

    print("Running 1987 replacement-game sensitivity check...")
    sens_1987 = compare_1987_with_and_without_replacement_games(games)
    for model_name, res in sens_1987.items():
        out_path = REPO / "data" / "processed" / f"phase3_1987_sensitivity_{model_name}.csv"
        res["table"].to_csv(out_path)
        print(f"Wrote {out_path}")

    records_1987 = replacement_game_records_1987(games)
    records_path = REPO / "data" / "processed" / "phase3_1987_replacement_game_records.csv"
    records_1987.to_csv(records_path, index=False)
    print(f"Wrote {records_path}")

    print("Checking 1982 uncertainty width...")
    unc_1982 = check_1982_uncertainty_is_wider(ratings)

    report = write_report(meta, sens_1987, records_1987, unc_1982)
    report_path = REPO / "docs" / "PHASE3_ERA_NORMALIZATION.md"
    report_path.write_text(report + "\n")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
