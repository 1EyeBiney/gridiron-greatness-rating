"""
Renders the static site into site/ from the tables in data/processed/.
site/ is never committed - it is regenerated from data every build (see
.github/workflows/deploy-pages.yml). Same accessibility approach as the
sibling Gridiron Greatness site: semantic landmarks, real tables with
scope attributes, a skip link, and no charts - every number is in a
table and every table is downloadable.
"""
from __future__ import annotations

import json
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
REPO_URL = "https://github.com/1EyeBiney/gridiron-greatness-rating/tree/master/studies/home-field-advantage"
MAIN_SITE = "../"  # this site is published under the main site as /home-field-advantage/

STATUS_LABELS = {"alive": "In the race", "clinched": "Clinched a spot", "longshot": "3+ games back",
                 "eliminated": "Eliminated"}
STATUS_ORDER = ["clinched", "alive", "longshot", "eliminated"]
PHASE_LABELS = {1: "Early (first third)", 2: "Middle third", 3: "Late (final third)"}


# ------------------------------------------------------------ formatting


def f1(x) -> str:
    return "-" if pd.isna(x) else f"{x:.1f}"


def f2(x) -> str:
    return "-" if pd.isna(x) else f"{x:.2f}"


def pct(x) -> str:
    return "-" if pd.isna(x) else f"{100 * x:.1f}%"


def pm(x, se) -> str:
    return "-" if pd.isna(x) else f"{x:.1f} ± {se:.1f}"


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


HFA_COLS = [("hfa", "Home-field advantage (pts)", f1, True), ("hfa_se", "± SE", f1, True),
            ("home_win_pct", "Home win %", pct, True), ("raw_margin", "Raw home margin", f1, True),
            ("n", "Games", n_, True)]


def status_label(s) -> str:
    return STATUS_LABELS.get(s, str(s))


def ordered_status(df: pd.DataFrame, col: str = "status") -> pd.DataFrame:
    df = df.copy()
    df["_o"] = df[col].map({s: i for i, s in enumerate(STATUS_ORDER)})
    return df.sort_values("_o").drop(columns="_o")


CONTENTION_COLS = [("status", "Team's situation entering the window", status_label, False),
                   ("n_all", "Games involving such a team", n_, True),
                   ("hfa_all", "Home-field advantage in those games (pts)", f1, True),
                   ("hfa_all_se", "± SE", f1, True),
                   ("n_as_host", "…as host", n_, True), ("hfa_as_host", "HFA as host", f1, True),
                   ("home_win_pct_as_host", "Home win % as host", pct, True),
                   ("n_as_visitor", "…as visitor", n_, True), ("hfa_as_visitor", "HFA as visitor", f1, True)]
GB_ORDER = ["Holding a spot", "Within 1 game", "1 to 3 games back", "3+ games back"]
GB_COLS = [("gb", "Games behind the last playoff spot, entering the window", str, False)] + CONTENTION_COLS[1:]

SWING_COLS = [("franchise", "Franchise", str, False), ("seasons", "Seasons", n_, True),
              ("home_games", "Home games", n_, True), ("home_adj_margin", "Home: pts vs expectation", f1, True),
              ("road_games", "Road games", n_, True), ("road_adj_margin", "Road: pts vs expectation", f1, True),
              ("swing", "Home/road swing (pts)", f1, True), ("swing_se", "± SE", f1, True),
              ("swing_vs_league", "Swing vs league", f1, True), ("z", "z", f2, True)]


# ------------------------------------------------------------------ facts


def load_tables() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in DATA.glob("*.csv") if p.stem != "games_adjusted"}


def build_facts(t: dict[str, pd.DataFrame]) -> dict:
    """Every number the prose uses, computed from the tables so the text
    and the tables can't disagree. tests/test_narrative_claims.py checks
    the qualitative claims built on these."""
    dec = t["by_decade"].set_index("decade")
    ph = t["by_phase"].set_index("phase")
    dp = t["by_decade_phase"]
    per_decade = {d: grp.set_index("phase")["hfa"] for d, grp in dp.groupby("decade")}
    decades_late_highest = [d for d, s in per_decade.items() if s.idxmax() == 3]
    decades_late_not_highest = [d for d in per_decade if d not in decades_late_highest]
    late_shortfall = {d: per_decade[d].max() - per_decade[d].loc[3] for d in decades_late_not_highest}
    week = t["by_week_1999"].set_index("week_index")
    covid = t["covid"].set_index("window")
    last3 = t["contention_last3"].set_index("status")
    last3_gb = t["contention_last3_games_back"].set_index("gb")
    third = t["contention_third"].set_index("status")
    naive = t["contention_late_naive"].set_index("home_status")
    roof = t["roof_phase"].set_index(["indoor", "phase"])
    div = t["division_phase"].set_index(["div_game", "phase"])
    sw = t["franchise_swing"].set_index("franchise")
    sw_modern = t["franchise_swing_2000_2025"].set_index("franchise")
    seasons = t["by_season"].set_index("season")
    week = t["by_week_1999"].set_index("week_index")
    with open(DATA / "current_season.json") as f:
        current = json.load(f)
    return {
        "n_games": int(t["by_phase"]["n"].sum()),
        "n_seasons": int(len(seasons)),
        "first_season": int(seasons.index.min()), "last_season": int(seasons.index.max()),
        "dec": dec, "ph": ph, "dp": dp,
        "n_decades": len(per_decade), "n_decades_late_highest": len(decades_late_highest),
        "decades_late_not_highest": decades_late_not_highest,
        "late_shortfall_max": max(late_shortfall.values()) if late_shortfall else 0.0,
        "weakest_weeks": week["hfa"].nsmallest(2).index.tolist(),
        "hfa_all": float(t["by_phase"].eval("hfa * n").sum() / t["by_phase"]["n"].sum()),
        "hfa_1970s": dec.loc["1970s", "hfa"], "hfa_1990s": dec.loc["1990s", "hfa"],
        "hfa_2010s": dec.loc["2010s", "hfa"], "hfa_2020s": dec.loc["2020s", "hfa"],
        "se_1990s": dec.loc["1990s", "hfa_se"], "se_2020s": dec.loc["2020s", "hfa_se"],
        "winpct_1990s": dec.loc["1990s", "home_win_pct"], "winpct_2020s": dec.loc["2020s", "home_win_pct"],
        "hfa_early": ph.loc[1, "hfa"], "hfa_mid": ph.loc[2, "hfa"], "hfa_late": ph.loc[3, "hfa"],
        "se_early": ph.loc[1, "hfa_se"], "se_late": ph.loc[3, "hfa_se"],
        "late_minus_early": ph.loc[3, "hfa"] - ph.loc[1, "hfa"],
        "late_2020s": dp.set_index(["decade", "phase"]).loc[("2020s", 3), "hfa"],
        "early_2020s": dp.set_index(["decade", "phase"]).loc[("2020s", 1), "hfa"],
        "final_week": t["final_week_vs_rest"].set_index("final").loc["Final week", "hfa"],
        "covid": covid,
        "hfa_2020": covid.loc["2020 (limited or no fans)", "hfa"], "se_2020": covid.loc["2020 (limited or no fans)", "hfa_se"],
        "hfa_2015_19": covid.loc["2015-2019", "hfa"], "hfa_2021_25": covid.loc["2021-2025", "hfa"],
        "last3": last3, "last3_gb": last3_gb, "third": third, "naive": naive,
        "elim_last3": last3.loc["eliminated", "hfa_all"], "elim_last3_se": last3.loc["eliminated", "hfa_all_se"],
        "alive_last3": last3.loc["alive", "hfa_all"], "alive_last3_se": last3.loc["alive", "hfa_all_se"],
        "n_elim_last3": int(last3.loc["eliminated", "n_all"]),
        "gb3_last3": last3_gb.loc["3+ games back", "hfa_all"], "spot_last3": last3_gb.loc["Holding a spot", "hfa_all"],
        "naive_elim": naive.loc["eliminated", "hfa"], "naive_alive": naive.loc["alive", "hfa"],
        "longshot_third": third.loc["longshot", "hfa_all"], "alive_third": third.loc["alive", "hfa_all"],
        "outdoor_late": roof.loc[(0.0, 3), "hfa"], "indoor_late": roof.loc[(1.0, 3), "hfa"],
        "outdoor_early": roof.loc[(0.0, 1), "hfa"], "indoor_early": roof.loc[(1.0, 1), "hfa"],
        "div_late": div.loc[(1.0, 3), "hfa"], "nondiv_late": div.loc[(0.0, 3), "hfa"],
        "div_all": float(div.xs(1.0).eval("hfa * n").sum() / div.xs(1.0)["n"].sum()),
        "nondiv_all": float(div.xs(0.0).eval("hfa * n").sum() / div.xs(0.0)["n"].sum()),
        "swing_league": float((sw["swing"] - sw["swing_vs_league"]).iloc[0]),
        "swing_max_team": sw["swing"].idxmax(), "swing_max": sw["swing"].max(), "swing_max_z": sw.loc[sw["swing"].idxmax(), "z"],
        "swing_min_team": sw["swing"].idxmin(), "swing_min": sw["swing"].min(), "swing_min_z": sw.loc[sw["swing"].idxmin(), "z"],
        "n_franchises": int(len(sw)),
        "n_abs_z_over_2": int((sw["z"].abs() >= 2).sum()),
        "pit_swing": sw.loc["PIT", "swing"], "pit_z": sw.loc["PIT", "z"],
        "sf_swing": sw.loc["SF", "swing"], "sf_z": sw.loc["SF", "z"],
        "dal_z": sw.loc["DAL", "z"], "gb_z": sw.loc["GB", "z"], "oak_z": sw.loc["OAK", "z"],
        "pit_z_modern": sw_modern.loc["PIT", "z"], "sf_z_modern": sw_modern.loc["SF", "z"],
        "no_z_modern": sw_modern.loc["NO", "z"],
        "season_min": int(seasons["hfa"].idxmin()), "season_min_hfa": seasons["hfa"].min(),
        "season_max": int(seasons["hfa"].idxmax()), "season_max_hfa": seasons["hfa"].max(),
        "n_seasons_late_gt_early": int((seasons["hfa_phase3"] > seasons["hfa_phase1"]).sum()),
        "week1": week.loc[1, "hfa"], "week1_se": week.loc[1, "hfa_se"],
        "current": current,
    }


# ----------------------------------------------------------------- render


def render_all(out_dir: Path = OUT_DIR) -> dict:
    t = load_tables()
    facts = build_facts(t)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters.update({"f1": f1, "f2": f2, "pct": pct, "n": n_})
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

    tables = {}
    dec = t["by_decade"].copy()
    tables["by_decade"] = table_html(dec, [("decade", "Decade", str, False)] + HFA_COLS,
                                     "Home-field advantage by decade, regular season, 1970-2025 (1982 excluded)")
    ph = t["by_phase"].copy()
    ph["phase"] = ph["phase"].map(PHASE_LABELS)
    tables["by_phase"] = table_html(ph, [("phase", "Part of season", str, False)] + HFA_COLS,
                                    "Home-field advantage by part of the regular season, all seasons")
    dp = t["by_decade_phase"].copy()
    dp["phase"] = dp["phase"].map(PHASE_LABELS)
    dp["row"] = dp["decade"] + ", " + dp["phase"]
    tables["by_decade_phase"] = table_html(
        dp, [("row", "Decade and part of season", str, False)] + HFA_COLS,
        "Home-field advantage by decade and part of the season")
    bs = t["by_season"].copy()
    tables["by_season"] = table_html(bs, [
        ("season", "Season", lambda x: str(int(x)), False), ("n", "Home-field games", n_, True),
        ("home_win_pct", "Home win %", pct, True), ("raw_margin", "Raw home margin", f1, True),
        ("home_adv", "Fitted HFA (pts)", f1, True), ("home_adv_se", "± SE", f1, True),
        ("hfa_phase1", "Early third", f1, True), ("hfa_phase2", "Middle third", f1, True),
        ("hfa_phase3", "Final third", f1, True), ("sigma", "Residual SD", f1, True)],
        "Every season: fitted home-field advantage and the adjusted home margin by part of the season")
    tables["by_week"] = table_html(t["by_week_1999"], [("week_index", "Week", lambda x: str(int(x)), False)] + HFA_COLS,
                                   "Home-field advantage by week number, 1999-2025 (week 18 exists only from 2021)")
    tables["final_week"] = table_html(t["final_week_vs_rest"], [("final", "", str, False)] + HFA_COLS,
                                      "The final regular-season week against every other week, 1970-2025")

    tables["last3"] = table_html(ordered_status(t["contention_last3"]), CONTENTION_COLS,
                                 "Final three weeks of the season, status frozen entering that window, ratings fit on those weeks only")
    gb = t["contention_last3_games_back"].set_index("gb").loc[GB_ORDER].reset_index()
    tables["last3_gb"] = table_html(gb, GB_COLS, "Final three weeks, by how far behind the last playoff spot the team was entering the window")
    tables["third"] = table_html(ordered_status(t["contention_third"]), CONTENTION_COLS,
                                 "Final third of the season, status frozen entering that window, ratings fit on that third only")
    gb3 = t["contention_third_games_back"].set_index("gb").loc[GB_ORDER].reset_index()
    tables["third_gb"] = table_html(gb3, GB_COLS, "Final third of the season, by games behind entering the window")
    era = ordered_status(t["contention_last3_by_era"]).sort_values(["era"], kind="stable")
    era["row"] = era["era"] + ": " + era["status"].map(status_label)
    tables["last3_era"] = table_html(era, [("row", "Era and situation", str, False)] + CONTENTION_COLS[1:],
                                     "Final three weeks by era")
    naive = ordered_status(t["contention_late_naive"], "home_status")
    naive["home_status"] = naive["home_status"].map(status_label)
    tables["naive"] = table_html(naive, [("home_status", "Home team's situation that week", str, False)] + HFA_COLS,
                                 "The naive version: running status against full-season ratings, final third of the season. Do not read this as home-field advantage - see the text.")

    roof = t["roof_phase"].copy()
    roof["row"] = np.where(roof["indoor"] == 1.0, "Indoors (dome or closed roof), ", "Outdoors, ") + roof["phase"].map(PHASE_LABELS)
    tables["roof"] = table_html(roof, [("row", "Venue and part of season", str, False)] + HFA_COLS,
                                "Indoor versus outdoor home fields by part of the season, 1999-2025")
    div = t["division_phase"].copy()
    div["row"] = np.where(div["div_game"] == 1.0, "Division game, ", "Non-division game, ") + div["phase"].map(PHASE_LABELS)
    tables["division"] = table_html(div, [("row", "Opponent and part of season", str, False)] + HFA_COLS,
                                    "Division versus non-division opponents by part of the season, 1999-2025")
    tables["covid"] = table_html(t["covid"], [("window", "Seasons", str, False)] + HFA_COLS,
                                 "The 2020 season, played in mostly empty stadiums, against the five seasons either side")

    for key, name in [("franchise_swing", "1970-2025"), ("franchise_swing_2000_2025", "2000-2025"),
                      ("franchise_swing_1970_1999", "1970-1999")]:
        tables[key] = table_html(t[key], SWING_COLS,
                                 f"Home/road swing by franchise, {name}, smallest swing first. Swing vs league is the swing minus twice the league home-field advantage over the same seasons.")

    render("index.html", out_dir / "index.html", root="", tables=tables)
    render("season.html", out_dir / "season-and-week.html", root="", tables=tables)
    render("playoff_race.html", out_dir / "playoff-race.html", root="", tables=tables)
    render("venues.html", out_dir / "venues.html", root="", tables=tables)
    render("franchises.html", out_dir / "franchises.html", root="", tables=tables)
    render("methodology.html", out_dir / "methodology.html", root="")
    render("what_it_means.html", out_dir / "what-it-means.html", root="")

    files = []
    for p in sorted(DATA.glob("*.csv")) + [DATA / "current_season.json"]:
        shutil.copy(p, out_dir / "data" / p.name)
        files.append({"name": p.name, "size_kb": max(1, p.stat().st_size // 1024)})
    render("data_index.html", out_dir / "data" / "index.html", root="../", files=files)
    return facts


if __name__ == "__main__":
    render_all()
    print(f"Site generated at {OUT_DIR}")
