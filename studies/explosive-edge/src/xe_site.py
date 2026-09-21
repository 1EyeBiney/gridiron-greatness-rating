"""
Renders the static site into site/ from the tables in data/processed/.
site/ is never committed - it is regenerated from data every build, same
pattern as the sibling home-field-advantage study: semantic landmarks,
real tables with scope attributes, a skip link, and no charts - every
number is in a table and every table is downloadable.
"""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape


REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "processed"
TEMPLATES_DIR = Path(__file__).resolve().parent / "site_templates"
OUT_DIR = REPO / "site"
REPO_URL = "https://github.com/1EyeBiney/gridiron-greatness-rating/tree/master/studies/explosive-edge"
MAIN_SITE = "../"  # this site is published under the main site as /explosive-edge/

ERAS = ["1999-2007", "2008-2016", "2017-2025"]
FIRST_SEASON, LAST_SEASON = 1999, 2025


# ------------------------------------------------------------ formatting


def f1(x) -> str:
    return "-" if pd.isna(x) else f"{x:.1f}"


def f2(x) -> str:
    return "-" if pd.isna(x) else f"{x:.2f}"


def f3(x) -> str:
    return "-" if pd.isna(x) else f"{x:.3f}"


def pct(x) -> str:
    return "-" if pd.isna(x) else f"{100 * x:.1f}%"


def pm(x, se) -> str:
    return "-" if pd.isna(x) else f"{x:.2f} ± {se:.2f}"


def n_(x) -> str:
    return "-" if pd.isna(x) else f"{int(x):,}"


def table_html(df: pd.DataFrame, columns: list[tuple], caption: str, row_header: str | None = None) -> Markup:
    """columns: (column_name, header_label, formatter, is_numeric). The
    first column is the row header (scope=row) unless row_header names one."""
    row_header = row_header or columns[0][0]
    head = "".join(
        f'<th scope="col"{" class=\"num\"" if num else ""}>{escape(label)}</th>' for _, label, _, num in columns)
    body = []
    for _, r in df.iterrows():
        cells = []
        for col, _, fmt, num in columns:
            val = escape(fmt(r[col]) if fmt else str(r[col]))
            cls = ' class="num"' if num else ""
            if col == row_header:
                cells.append(f'<th scope="row"{cls}>{val}</th>')
            else:
                cells.append(f"<td{cls}>{val}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return Markup(
        f'<div class="table-scroll stats"><table><caption>{escape(caption)}</caption>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>")


CAT_LABELS = {
    "won_both": "Won explosive battle and turnover battle",
    "won_explosive_lost_turnover": "Won explosive battle, lost turnover battle",
    "explosive_only": "Won explosive battle, turnover battle even",
    "turnover_only": "Won turnover battle, explosive battle even",
    "both_even": "Both even",
}


def cat_label(c) -> str:
    return CAT_LABELS.get(c, str(c))


# ------------------------------------------------------------------ facts


def load_tables() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in DATA.glob("*.csv")}


def _era_dict(df: pd.DataFrame, era_col: str = "era") -> dict[str, dict]:
    return {row[era_col]: row.to_dict() for _, row in df.iterrows()}


def _persistence_dict(df: pd.DataFrame, group_col: str) -> dict:
    out: dict[str, dict] = {}
    for key, g in df.groupby(group_col):
        out[str(key)] = {row["metric"]: {"n": row["n"], "r": row["r"], "ci_lo": row["ci_lo"], "ci_hi": row["ci_hi"]}
                          for _, row in g.iterrows()}
    return out


def _head_to_head_dict(df: pd.DataFrame) -> dict:
    out: dict[str, dict] = {}
    for era, g in df.groupby("era"):
        out[str(era)] = {row["category"]: {"n_games": row["n_games"], "win_rate": row["win_rate"]}
                          for _, row in g.iterrows()}
    return out


def build_facts(t: dict[str, pd.DataFrame]) -> dict:
    """Every number the What It Means / Findings prose will use, computed
    from the tables so the text and the tables can't disagree."""
    tg = t["team_game"]
    reg = tg[(tg["game_type"] == "REG") & tg["season"].between(FIRST_SEASON, LAST_SEASON)]
    n_games = int(reg["game_id"].nunique())
    n_seasons = int(reg["season"].nunique())
    first_season = int(reg["season"].min())
    last_season = int(reg["season"].max())

    shift_era = _era_dict(t["shift_logit_by_era"])
    exch_era = _era_dict(t["exchange_rate_by_era"])
    strategy_era = _era_dict(t["mechanism_strategy_by_era"])
    persistence_era = _persistence_dict(t["persistence_by_era"], "era")
    persistence_yoy = _persistence_dict(t["persistence_year_to_year"], "era")
    h2h_era = _head_to_head_dict(t["head_to_head_by_era"])
    h2h_ng_era = _head_to_head_dict(t["head_to_head_ng_by_era"])
    tsr_corr = _era_dict(t["leaderboard_correlations"])

    ct_era = _era_dict(t["competitive_time_logit_by_era"])
    pp_era = _era_dict(t["playoff_prediction"])
    pp_all = pp_era.get("ALL", {})
    hth_post = {row["category"]: row.to_dict() for _, row in t["playoff_head_to_head"].iterrows()}
    sb = t["super_bowl_ranks"]
    sb_summary = sb[sb["season"] == "median"].iloc[0].to_dict() if (sb["season"] == "median").any() else {}
    qb_cont = {row["qb_continuity"]: row.to_dict() for _, row in t["qb_continuity_persistence"].iterrows()}
    qb_top3 = t["qb_career_explosive_leaders"].head(3).to_dict(orient="records")
    qb_top1_season = t["qb_season_explosive_leaders"].iloc[0].to_dict()
    qb_join = t["qb_join_coverage"].iloc[0].to_dict() if "qb_join_coverage" in t else {}
    rel = {(r["era"], r["metric"]): r.to_dict() for _, r in t["reliability_decomposition"].iterrows()} \
        if "reliability_decomposition" in t else {}
    last_era_label = "2017-2025"
    rel_exp = rel.get((last_era_label, "explosive_diff_per_game"), {})
    rel_tod = rel.get((last_era_label, "turnover_diff_per_game"), {})
    decomp = t["pass_run_decomposition"].iloc[0].to_dict()

    def _nested(df, val_col, era_col="era", bucket_col="bucket"):
        out: dict[str, dict] = {}
        for _, row in df.iterrows():
            out.setdefault(str(row[era_col]), {})[str(row[bucket_col])] = row[val_col]
        return out

    drive_pos = _nested(t["drive_position_explosive_rate"], "explosive_rate")
    garbage_mean = float(t["garbage_share_by_season"]["garbage_share_of_explosives"].mean())
    defplay = _nested(t["defensive_play_by_drive_position"], "def_play_rate")
    drive_out = _era_dict(t["drive_outcomes_by_era"])
    followup_first_era, followup_last_era = ERAS[0], ERAS[-1]

    mech = t["mechanism_by_season"].set_index("season")
    mech_1999 = mech.loc[1999].to_dict() if 1999 in mech.index else {}
    mech_2025 = mech.loc[2025].to_dict() if 2025 in mech.index else {}

    trend = {row["coefficient"]: row.to_dict() for _, row in t["shift_trend"].iterrows()}

    board = t["leaderboard_team_seasons"].sort_values("explosive_diff_per_game", ascending=False)
    top5 = board.head(5).to_dict(orient="records")

    garbage_comparison = {}
    for era in list(h2h_era.keys()):
        if era in h2h_ng_era:
            garbage_comparison[era] = {
                "all_plays": h2h_era[era].get("won_explosive_lost_turnover", {}).get("win_rate"),
                "no_garbage": h2h_ng_era[era].get("won_explosive_lost_turnover", {}).get("win_rate"),
            }

    last_era = ERAS[-1]

    return {
        "n_games": n_games, "n_seasons": n_seasons, "first_season": first_season, "last_season": last_season,
        "eras": ERAS, "last_era": last_era,
        "shift_by_era": shift_era, "exchange_by_era": exch_era, "strategy_by_era": strategy_era,
        "persistence_by_era": persistence_era, "persistence_year_to_year": persistence_yoy,
        "head_to_head_by_era": h2h_era, "head_to_head_ng_by_era": h2h_ng_era,
        "tsr_correlations_by_era": tsr_corr,
        "mechanism_1999": mech_1999, "mechanism_2025": mech_2025,
        "trend": trend,
        "leaderboard_top5": top5,
        "garbage_time_comparison": garbage_comparison,
        # convenience: the last era's headline numbers, flattened
        "shift_last_era": shift_era.get(last_era, {}),
        "exchange_last_era": exch_era.get(last_era, {}),
        "tsr_corr_all": tsr_corr.get("ALL", {}),

        # -------- follow-up analyses (2026-09-20 overnight exploration) --------
        "competitive_time_by_era": ct_era,
        "playoff_prediction_by_era": pp_era,
        "playoff_prediction_all": pp_all,
        "playoff_prediction_b_epd": pp_all.get("b_epd"),
        "playoff_prediction_se_epd": pp_all.get("se_epd"),
        "playoff_prediction_b_tod": pp_all.get("b_tod"),
        "playoff_prediction_se_tod": pp_all.get("se_tod"),
        "playoff_prediction_n": pp_all.get("n_games"),
        "postseason_won_explosive_lost_turnover_win_rate":
            hth_post.get("won_explosive_lost_turnover", {}).get("win_rate"),
        "postseason_won_explosive_lost_turnover_n":
            hth_post.get("won_explosive_lost_turnover", {}).get("n_games"),
        "super_bowl_median_epd_rank": sb_summary.get("epd_rank"),
        "super_bowl_median_tod_rank": sb_summary.get("tod_rank"),
        "qb_continuity_same_qb_r": qb_cont.get("same_qb", {}).get("correlation"),
        "qb_continuity_same_qb_n": qb_cont.get("same_qb", {}).get("n_team_seasons"),
        "qb_continuity_changed_qb_r": qb_cont.get("changed_qb", {}).get("correlation"),
        "qb_continuity_changed_qb_n": qb_cont.get("changed_qb", {}).get("n_team_seasons"),
        "qb_continuity_same_qb_ci_lo": qb_cont.get("same_qb", {}).get("ci_lo"),
        "qb_continuity_changed_qb_ci_hi": qb_cont.get("changed_qb", {}).get("ci_hi"),
        # do the two groups' 95% intervals overlap? if so the gap itself is not firmly established
        "qb_continuity_ci_overlap": (qb_cont.get("same_qb", {}).get("ci_lo", 0) or 0)
                                    < (qb_cont.get("changed_qb", {}).get("ci_hi", 0) or 0),
        "qb_career_top3": qb_top3,
        "qb_top_season": qb_top1_season,
        "qb_join_team_games": qb_join.get("team_games"),
        "qb_join_unmatched": qb_join.get("unmatched"),
        "qb_join_unmatched_v1": 894,        # what the raw team-code join dropped, for the correction note
        # rarity vs skill (last era): what counting noise alone would leave
        "rel_explosive_implied": rel_exp.get("implied_reliability"),
        "rel_explosive_observed": rel_exp.get("observed_split_half_r"),
        "rel_turnover_implied": rel_tod.get("implied_reliability"),
        "rel_turnover_observed": rel_tod.get("observed_split_half_r"),
        "rel_gap_share_from_rarity": (
            ((rel_exp.get("implied_reliability") or 0) - (rel_tod.get("implied_reliability") or 0))
            / ((rel_exp.get("observed_split_half_r") or 1) - (rel_tod.get("observed_split_half_r") or 0))
            if rel_exp and rel_tod else None),
        "playoff_prediction_tod_upper": (
            (pp_all.get("b_tod") or 0) + 2 * (pp_all.get("se_tod") or 0)) if pp_all else None,
        "playoff_prediction_tod_lower": (
            (pp_all.get("b_tod") or 0) - 2 * (pp_all.get("se_tod") or 0)) if pp_all else None,
        "decomposition_2018_2025": decomp,
        "decomposition_from_rate": decomp.get("total_rate_per_play_from"),
        "decomposition_to_rate": decomp.get("total_rate_per_play_to"),
        "decomposition_rate_effect": decomp.get("rate_effect_within_type"),
        "decomposition_mix_effect": decomp.get("mix_effect_pass_rate"),
        "decomposition_share_rate_effect": decomp.get("share_of_change_that_is_rate_effect"),
        "drive_position_play1_first_era": drive_pos.get("2010-2017", {}).get("1"),
        "drive_position_play1_last_era": drive_pos.get("2018-2025", {}).get("1"),
        "garbage_share_mean": garbage_mean,
        "def_play_rate_play1_last_era": defplay.get("2017-2025", {}).get("1"),
        "def_play_rate_play3_last_era": defplay.get("2017-2025", {}).get("3"),
        "def_play_rate_play8plus_last_era": defplay.get("2017-2025", {}).get("8+"),
        "def_play_rate_play1_first_era": defplay.get("1999-2007", {}).get("1"),
        "def_play_rate_play3_first_era": defplay.get("1999-2007", {}).get("3"),
        "def_play_rate_play8plus_first_era": defplay.get("1999-2007", {}).get("8+"),
        "drive_outcomes_by_era": drive_out,
        "points_per_drive_first_era": drive_out.get(followup_first_era, {}).get("points_per_drive"),
        "points_per_drive_last_era": drive_out.get(followup_last_era, {}).get("points_per_drive"),
        "p_def_play_per_drive_first_era": drive_out.get(followup_first_era, {}).get("p_at_least_one_def_play_per_drive"),
        "p_def_play_per_drive_last_era": drive_out.get(followup_last_era, {}).get("p_at_least_one_def_play_per_drive"),
    }


# ----------------------------------------------------------------- render


SHIFT_ERA_COLS = [
    ("era", "Era", str, False),
    ("n_games", "Games", n_, True),
    ("both_b_epd", "Std. EPD coef.", f2, True),
    ("both_se_b_epd", "± SE", f2, True),
    ("both_b_tod", "Std. TOD coef.", f2, True),
    ("both_se_b_tod", "± SE", f2, True),
    ("epd_only_log_loss", "Log loss, EPD only", f3, True),
    ("tod_only_log_loss", "Log loss, TOD only", f3, True),
    ("both_log_loss", "Log loss, both", f3, True),
    ("epd_only_accuracy", "Accuracy, EPD only", pct, True),
    ("tod_only_accuracy", "Accuracy, TOD only", pct, True),
    ("both_accuracy", "Accuracy, both", pct, True),
]

SHIFT_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), False),
    ("n_games", "Games", n_, True),
    ("both_b_epd", "Std. EPD coef.", f2, True),
    ("both_se_b_epd", "± SE", f2, True),
    ("both_b_tod", "Std. TOD coef.", f2, True),
    ("both_se_b_tod", "± SE", f2, True),
    ("both_log_loss", "Log loss, both", f3, True),
    ("both_accuracy", "Accuracy, both", pct, True),
]

TREND_COLS = [
    ("coefficient", "Coefficient", str, False),
    ("slope_per_season", "Slope per season", f3, True),
    ("slope_se", "± SE", f3, True),
    ("intercept", "Intercept", f2, True),
    ("r2", "R²", f2, True),
    ("n_seasons", "Seasons", n_, True),
]

EXCHANGE_COLS = [
    ("n_games", "Games", n_, True),
    ("points_per_explosive", "Points per explosive play", f2, True),
    ("points_per_explosive_se", "± SE", f2, True),
    ("points_per_turnover", "Points per turnover", f2, True),
    ("points_per_turnover_se", "± SE", f2, True),
    ("exchange_ratio_turnover_to_explosive", "1 turnover = N explosive plays", f2, True),
    ("exchange_ratio_se", "± SE", f2, True),
]

SENSITIVITY_COLS = [
    ("definition", "Explosive-play definition", str, False),
    ("n_games", "Games", n_, True),
    ("both_b_epd", "Std. EPD coef.", f2, True),
    ("both_se_b_epd", "± SE", f2, True),
    ("both_log_loss", "Log loss, both", f3, True),
    ("both_accuracy", "Accuracy, both", pct, True),
]

MECHANISM_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), False),
    ("explosive_rate_per_play", "Explosive rate / play", pct, True),
    ("explosive_rate_per_drive", "Explosive rate / drive", pct, True),
    ("plays_per_drive", "Plays / drive", f2, True),
    ("seconds_per_drive", "Seconds / drive", f1, True),
    ("pass_rate", "Pass rate", pct, True),
    ("def_play_rate_per_snap", "Defensive-play rate / snap", pct, True),
    ("turnovers_per_game", "Turnovers / game (league)", f2, True),
]

STRATEGY_COLS = [
    ("era", "Era", str, False),
    ("n_team_seasons", "Team-seasons", n_, True),
    ("correlation", "Correlation (explosive rate vs plays/drive)", f2, True),
    ("fisher_z_se", "± SE (Fisher z)", f2, True),
]

PERSISTENCE_LABELS = {
    "explosive_rate_per_play": "Explosive rate per play",
    "explosive_diff_per_game": "Explosive differential / game",
    "turnovers_per_game": "Turnovers / game",
    "turnover_diff_per_game": "Turnover differential / game",
    "margin_per_game": "Margin / game",
    "yards_per_play": "Yards / play",
}


def metric_label(m) -> str:
    return PERSISTENCE_LABELS.get(m, str(m))


PERSISTENCE_COLS = [
    ("era", "Era", str, False),
    ("metric", "Metric", metric_label, False),
    ("n", "Team-seasons", n_, True),
    ("r", "Split-half r", f2, True),
    ("ci_lo", "95% CI low", f2, True),
    ("ci_hi", "95% CI high", f2, True),
]

PERSISTENCE_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), False),
    ("metric", "Metric", metric_label, False),
    ("n", "Teams", n_, True),
    ("r", "Split-half r", f2, True),
]

HEAD_TO_HEAD_COLS = [
    ("era", "Era", str, False),
    ("category", "Category", cat_label, False),
    ("n_games", "Games", n_, True),
    ("win_rate", "Win rate", pct, True),
]

HEAD_TO_HEAD_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), False),
    ("category", "Category", cat_label, False),
    ("n_games", "Games", n_, True),
    ("win_rate", "Win rate", pct, True),
]

LEADERBOARD_COLS = [
    ("franchise", "Team", str, False),
    ("season", "Season", lambda x: str(int(x)), False),
    ("record", "Record", str, False),
    ("explosive_diff_per_game", "Explosive differential / game", f2, True),
    ("turnover_diff_per_game", "Turnover differential / game", f2, True),
    ("bayes_rating_z", "TSR z", f2, True),
    ("won_super_bowl", "Won Super Bowl", lambda x: "Yes" if x else "", False),
]

TOP_OFF_DEF_COLS = [
    ("franchise", "Team", str, False),
    ("season", "Season", lambda x: str(int(x)), False),
    ("record", "Record", str, False),
    ("explosive_per_game", "Explosive plays / game (off.)", f2, True),
    ("explosive_allowed_per_game", "Explosive plays allowed / game (def.)", f2, True),
    ("points_per_game", "Points / game", f1, True),
]

TSR_CORR_COLS = [
    ("era", "Era", str, False),
    ("n", "Team-seasons", n_, True),
    ("r_explosive_diff", "r, explosive diff vs TSR", f2, True),
    ("r_turnover_diff", "r, turnover diff vs TSR", f2, True),
    ("r2_both", "R², both", f2, True),
]


COMPETITIVE_TIME_COLS = [
    ("era", "Era", str, False),
    ("n_games", "Games", n_, True),
    ("all_b_epd", "All plays: EPD coef.", f2, True),
    ("all_b_tod", "All plays: TOD coef.", f2, True),
    ("all_epd_minus_tod_gap", "All plays: EPD − |TOD|", f2, True),
    ("ng_b_epd", "Competitive time: EPD coef.", f2, True),
    ("ng_b_tod", "Competitive time: TOD coef.", f2, True),
    ("ng_epd_minus_tod_gap", "Competitive time: EPD − |TOD|", f2, True),
]

PLAYOFF_PREDICTION_COLS = [
    ("era", "Era", str, False),
    ("n_games", "Playoff games", n_, True),
    ("b_epd", "Reg.-season EPD diff. coef.", f2, True),
    ("se_epd", "± SE", f2, True),
    ("b_tod", "Reg.-season TOD diff. coef.", f2, True),
    ("se_tod", "± SE", f2, True),
    ("accuracy", "Accuracy", pct, True),
]

PLAYOFF_HEAD_TO_HEAD_COLS = [
    ("category", "Category", cat_label, False),
    ("n_games", "Playoff games", n_, True),
    ("win_rate", "Win rate", pct, True),
]

SUPER_BOWL_RANK_COLS = [
    ("season", "Season", str, False),
    ("champion", "Champion", lambda x: "" if pd.isna(x) else str(x), False),
    ("n_teams", "Teams", n_, True),
    ("explosive_diff_pg", "Explosive diff. / game", f2, True),
    ("epd_rank", "EPD rank", n_, True),
    ("turnover_diff_pg", "Turnover diff. / game", f2, True),
    ("tod_rank", "TOD rank", n_, True),
]

QB_CONTINUITY_COLS = [
    ("qb_continuity", "QB continuity", lambda x: "Same QB" if x == "same_qb" else "Changed QB", False),
    ("n_team_seasons", "Team-seasons", n_, True),
    ("correlation", "Year-to-year r", f2, True),
    ("ci_lo", "95% CI low", f2, True),
    ("ci_hi", "95% CI high", f2, True),
]

_QB_MEASURE_COLS = [
    ("dropbacks", "Own dropbacks", n_, True),
    ("explosive_pass", "Explosive completions (20+)", n_, True),
    ("rate", "Explosive completions / dropback", pct, True),
    ("air_share", "Share 20+ in the air (2006 on)", pct, True),
    ("qb_rushes", "QB rushes", n_, True),
    ("explosive_rush", "Explosive QB rushes (10+)", n_, True),
    ("rush_rate", "Explosive rate / QB rush", pct, True),
]

QB_CAREER_COLS = [
    ("qb_name", "Quarterback", str, False),
    ("seasons", "Seasons", n_, True),
    ("games", "Games", n_, True),
] + _QB_MEASURE_COLS

QB_SEASON_COLS = [
    ("qb_name", "Quarterback", str, False),
    ("season", "Season", lambda x: str(int(x)), False),
    ("games", "Games", n_, True),
] + _QB_MEASURE_COLS

RELIABILITY_COLS = [
    ("era", "Era", str, False),
    ("metric", "Metric", lambda x: {"explosive_diff_per_game": "Explosive diff. / game",
                                    "turnover_diff_per_game": "Turnover diff. / game"}.get(x, x), False),
    ("mean_per_game", "Mean per game", f2, True),
    ("observed_var", "Between-team variance (half-seasons)", f2, True),
    ("poisson_noise_var", "Counting-noise variance", f2, True),
    ("implied_reliability", "Reliability if noise were the only problem", f2, True),
    ("observed_split_half_r", "Observed split-half r", f2, True),
]

PASS_RUN_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), False),
    ("pass_rate", "Pass rate", pct, True),
    ("explosive_pass_rate_per_dropback", "Explosive-pass rate / dropback", pct, True),
    ("explosive_rush_rate_per_attempt", "Explosive-rush rate / attempt", pct, True),
    ("rush_share_of_explosives", "Rush share of explosives", pct, True),
]

PASS_RUN_DECOMP_COLS = [
    ("from_season", "From season", lambda x: str(int(x)), False),
    ("to_season", "To season", lambda x: str(int(x)), False),
    ("total_rate_per_play_from", "Explosive rate / play, from", pct, True),
    ("total_rate_per_play_to", "Explosive rate / play, to", pct, True),
    ("total_change", "Total change", pct, True),
    ("mix_effect_pass_rate", "Mix effect (pass rate)", pct, True),
    ("rate_effect_within_type", "Rate effect (within type)", pct, True),
    ("share_of_change_that_is_rate_effect", "Share of change: rate effect", pct, True),
]

DRIVE_POSITION_COLS = [
    ("era", "Era", str, False),
    ("bucket", "Play # in drive", str, False),
    ("plays", "Plays", n_, True),
    ("explosive_rate", "Explosive rate", pct, True),
]

DEFENSIVE_PLAY_POSITION_COLS = [
    ("era", "Era", str, False),
    ("bucket", "Play # in drive", str, False),
    ("plays", "Plays", n_, True),
    ("def_play_rate", "Defensive-play rate", pct, True),
]

DRIVE_OUTCOMES_COLS = [
    ("era", "Era", str, False),
    ("drives", "Drives", n_, True),
    ("p_at_least_one_def_play_per_drive", "P(≥1 defensive play)", pct, True),
    ("points_per_drive", "Points / drive", f2, True),
    ("plays_per_drive", "Plays / drive", f2, True),
]


def _reset_output_dir(out_dir) -> None:
    """Empty `out_dir` (creating it if needed) without insisting that every
    folder disappear. On Windows another process (Explorer, the search
    indexer, an antivirus scan of freshly written images) can hold a folder
    handle that makes os.rmdir fail long after its files are gone; such a
    folder is left empty and reused, which is all the build needs. Files
    are retried briefly because their locks are short-lived."""
    import os
    import time
    out_dir = Path(out_dir)
    if out_dir.exists():
        for root, dirs, files in os.walk(out_dir, topdown=False):
            for name in files:
                path = os.path.join(root, name)
                for attempt in range(20):
                    try:
                        os.remove(path)
                        break
                    except PermissionError:
                        if attempt == 19:
                            raise
                        time.sleep(0.25)
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass                      # held open by someone else; it is empty, reuse it
    out_dir.mkdir(parents=True, exist_ok=True)


def render_all(out_dir: Path = OUT_DIR) -> dict:
    # Regenerate the follow-up-analysis CSVs (data/processed has no single
    # existing pipeline entrypoint that chains xe_metrics.run() ->
    # xe_analysis_shift.run() / xe_analysis_teams.run() -> xe_site -- each
    # is run by hand -- so this is the one step of the chain that DOES run
    # automatically on every site build, keeping the follow-up tables from
    # going stale relative to team_game.csv).
    # Analyses are NOT run here: the site builds from the committed tables in
    # data/processed/ (CI has no raw play-by-play). Run src/xe_build.py locally
    # to regenerate them.
    t = load_tables()
    facts = build_facts(t)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters.update({"f0": lambda x: "-" if pd.isna(x) else f"{x:.0f}", "f1": f1, "f2": f2, "f3": f3,
                        "pct": pct, "n": n_})
    env.globals.update({"pm": pm})

    _reset_output_dir(out_dir)
    (out_dir / "static").mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(exist_ok=True)
    shutil.copy(TEMPLATES_DIR / "style.css", out_dir / "static" / "style.css")
    shutil.copytree(TEMPLATES_DIR / "images", out_dir / "images", dirs_exist_ok=True)

    common = {"generated_date": date.today().isoformat(), "repo_url": REPO_URL, "main_site": MAIN_SITE, "facts": facts}

    def render(template: str, target: Path, **ctx):
        html = env.get_template(template).render(**common, **ctx)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    tables: dict[str, Markup] = {}

    tables["shift_by_era"] = table_html(t["shift_logit_by_era"], SHIFT_ERA_COLS,
                                        "The shift, by era: standardized coefficients (win ~ EPD + TOD) and model fit")
    tables["shift_by_season"] = table_html(t["shift_logit_by_season"], SHIFT_SEASON_COLS,
                                           "The shift, by season: standardized coefficients and model fit")
    tables["shift_trend"] = table_html(t["shift_trend"], TREND_COLS,
                                       "Trend across seasons of the standardized EPD and TOD coefficients")
    sens = t["shift_logit_sensitivity"].groupby("definition", as_index=False).agg(
        n_games=("n_games", "sum"),
        both_b_epd=("both_b_epd", "mean"), both_se_b_epd=("both_se_b_epd", "mean"),
        both_log_loss=("both_log_loss", "mean"), both_accuracy=("both_accuracy", "mean"))
    tables["shift_sensitivity"] = table_html(sens, SENSITIVITY_COLS,
                                             "Sensitivity check: the 'both' model's EPD coefficient and fit, averaged across seasons, for each explosive-play definition")
    tables["exchange_by_era"] = table_html(t["exchange_rate_by_era"], [("era", "Era", str, False)] + EXCHANGE_COLS,
                                           "Exchange rate by era: points per explosive play and per turnover")
    tables["exchange_by_season"] = table_html(
        t["exchange_rate_by_season"], [("season", "Season", lambda x: str(int(x)), False)] + EXCHANGE_COLS,
        "Exchange rate by season: points per explosive play and per turnover")

    tables["mechanism_by_season"] = table_html(t["mechanism_by_season"], MECHANISM_SEASON_COLS,
                                               "League mechanism trends by season")
    tables["mechanism_strategy_by_era"] = table_html(t["mechanism_strategy_by_era"], STRATEGY_COLS,
                                                     "Do teams with a higher explosive rate run fewer plays per drive? Correlation by era")

    persist_era = t["persistence_by_era"].copy()
    persist_era = persist_era[persist_era["metric"].isin(
        ["explosive_diff_per_game", "turnover_diff_per_game", "margin_per_game", "explosive_rate_per_play"])]
    tables["persistence_by_era"] = table_html(persist_era, PERSISTENCE_COLS,
                                              "Split-half reliability (weeks 1-9 vs weeks 10-end) by era")
    tables["persistence_by_season"] = table_html(
        t["persistence_by_season"][t["persistence_by_season"]["metric"].isin(
            ["explosive_diff_per_game", "turnover_diff_per_game", "margin_per_game"])],
        PERSISTENCE_SEASON_COLS, "Split-half reliability by season")
    tables["persistence_year_to_year"] = table_html(t["persistence_year_to_year"], PERSISTENCE_COLS,
                                                     "Year-to-year persistence (season s vs season s+1) by era")

    tables["head_to_head_by_era"] = table_html(t["head_to_head_by_era"], HEAD_TO_HEAD_COLS,
                                               "Head-to-head: who wins when a team wins the explosive battle but loses the turnover battle (and vice versa), by era")
    tables["head_to_head_by_season"] = table_html(t["head_to_head_by_season"], HEAD_TO_HEAD_SEASON_COLS,
                                                  "Head-to-head categories by season")
    tables["head_to_head_ng_by_era"] = table_html(t["head_to_head_ng_by_era"], HEAD_TO_HEAD_COLS,
                                                  "Head-to-head, excluding garbage-time plays (win probability outside 5%-95%), by era")

    tables["leaderboard_top25"] = table_html(t["leaderboard_team_seasons"].head(25), LEADERBOARD_COLS,
                                             "Top 25 team-seasons by explosive-play differential per game, 1999-2025")
    tables["leaderboard_top_offenses"] = table_html(t["leaderboard_top_offenses"].head(25), TOP_OFF_DEF_COLS,
                                                     "Top 25 offenses by explosive plays per game")
    tables["leaderboard_top_defenses"] = table_html(t["leaderboard_top_defenses"].head(25), TOP_OFF_DEF_COLS,
                                                     "Top 25 defenses by fewest explosive plays allowed per game")
    tables["leaderboard_correlations"] = table_html(t["leaderboard_correlations"], TSR_CORR_COLS,
                                                     "Correlation of explosive/turnover differentials with the main project's True Strength Rating, by era")

    tables["competitive_time"] = table_html(t["competitive_time_logit_by_era"], COMPETITIVE_TIME_COLS,
                                            "Win ~ EPD + TOD, all plays vs competitive time only (win probability 5%-95%), by era")
    tables["playoff_prediction"] = table_html(t["playoff_prediction"], PLAYOFF_PREDICTION_COLS,
                                              "Predicting postseason wins from the two teams' regular-season explosive and turnover differentials")
    tables["playoff_head_to_head"] = table_html(t["playoff_head_to_head"], PLAYOFF_HEAD_TO_HEAD_COLS,
                                                "Postseason head-to-head: who wins when the explosive and turnover battles disagree")
    tables["super_bowl_ranks"] = table_html(t["super_bowl_ranks"], SUPER_BOWL_RANK_COLS,
                                            "Each Super Bowl champion's regular-season rank in explosive and turnover differential")
    tables["qb_continuity"] = table_html(t["qb_continuity_persistence"], QB_CONTINUITY_COLS,
                                         "Year-to-year persistence of team explosive-pass rate (explosive completions per dropback), by quarterback continuity")
    tables["qb_career_leaders"] = table_html(t["qb_career_explosive_leaders"], QB_CAREER_COLS,
                                             "Top 20 quarterbacks by career explosive completions per own dropback, regular season 1999-2025 (min. 1,500 dropbacks)")
    tables["qb_season_leaders"] = table_html(t["qb_season_explosive_leaders"], QB_SEASON_COLS,
                                             "Top 15 single seasons by explosive completions per own dropback (min. 300 dropbacks)")
    if "reliability_decomposition" in t:
        tables["reliability"] = table_html(t["reliability_decomposition"], RELIABILITY_COLS,
                                           "How much of each metric's between-team spread is counting noise, by era")
    tables["pass_run_by_season"] = table_html(t["pass_run_explosives_by_season"], PASS_RUN_SEASON_COLS,
                                              "Explosive-pass and explosive-rush rates by season")
    tables["pass_run_decomposition"] = table_html(t["pass_run_decomposition"], PASS_RUN_DECOMP_COLS,
                                                  "Decomposition of the 2018-2025 change in explosive rate per play into a within-type rate effect and a pass-rate mix effect")
    tables["drive_position"] = table_html(t["drive_position_explosive_rate"], DRIVE_POSITION_COLS,
                                          "Explosive rate by play number within a drive, 2010-2017 vs 2018-2025")
    tables["defensive_play_by_position"] = table_html(t["defensive_play_by_drive_position"], DEFENSIVE_PLAY_POSITION_COLS,
                                                       "Probability a scrimmage play is a defensive play, by play number within a drive, by era")
    tables["drive_outcomes"] = table_html(t["drive_outcomes_by_era"], DRIVE_OUTCOMES_COLS,
                                          "Per-drive outcomes by era: chance of a defensive play, points per drive, plays per drive")

    render("index.html", out_dir / "index.html", root="", tables=tables)
    render("the_shift.html", out_dir / "the-shift.html", root="", tables=tables)
    render("mechanism.html", out_dir / "mechanism.html", root="", tables=tables)
    render("skill_or_luck.html", out_dir / "skill-or-luck.html", root="", tables=tables)
    render("head_to_head.html", out_dir / "head-to-head.html", root="", tables=tables)
    render("leaderboard.html", out_dir / "leaderboard.html", root="", tables=tables)
    render("methodology.html", out_dir / "methodology.html", root="")
    render("what_it_means.html", out_dir / "what-it-means.html", root="")

    files = []
    for p in sorted(DATA.glob("*.csv")):
        shutil.copy(p, out_dir / "data" / p.name)
        files.append({"name": p.name, "size_kb": max(1, p.stat().st_size // 1024)})
    render("data_index.html", out_dir / "data" / "index.html", root="../", files=files)
    return facts


if __name__ == "__main__":
    render_all()
    print(f"Site generated at {OUT_DIR}")
