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


def render_all(out_dir: Path = OUT_DIR) -> dict:
    t = load_tables()
    facts = build_facts(t)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters.update({"f0": lambda x: "-" if pd.isna(x) else f"{x:.0f}", "f1": f1, "f2": f2, "f3": f3,
                        "pct": pct, "n": n_})
    env.globals.update({"pm": pm})

    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "static").mkdir(parents=True)
    (out_dir / "data").mkdir()
    shutil.copy(TEMPLATES_DIR / "style.css", out_dir / "static" / "style.css")
    shutil.copytree(TEMPLATES_DIR / "images", out_dir / "images")

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
