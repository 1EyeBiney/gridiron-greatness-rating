"""
Phase 6: generates the static site (BUILD_PLAN section 8) into site/,
which .github/workflows/deploy-pages.yml then publishes to GitHub Pages.
site/ is not committed to the repository (see .gitignore) - it is always
regenerated fresh from the data in data/processed/ and data/reference/,
the same reproducibility principle the rest of this pipeline follows.

Accessibility (BUILD_PLAN section 10), applied throughout the templates
in src/site_templates/: semantic headings, real <table> markup with
scope attributes on header cells, a skip link, and no chart anywhere -
every number on this site is in a plain HTML table and also downloadable
as CSV/JSON, which satisfies "usable non-visually first" (BUILD_PLAN
section 2, item 6) more directly than an accessible chart would. This
was built to the letter of that spec; it has not been tested with actual
screen reader software (NVDA/JAWS, which section 10 calls for) - that
needs a human with that software, not something this session can do.
"""
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from accomplishment import find_super_bowl_games
from models.common import load_games
from queries import build_all_queries

REPO = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = Path(__file__).resolve().parent / "site_templates"
OUT_DIR = REPO / "site"

def _fmt(x, decimals=2):
    if pd.isna(x):
        return "-"
    return f"{x:.{decimals}f}"


def _record(row):
    rec = f"{int(row['wins'])}-{int(row['losses'])}"
    if row.get("ties", 0):
        rec += f"-{int(row['ties'])}"
    return rec


def _playoffs_text(row):
    """Postseason record plus how the run ended, e.g. '3-1 (lost SB)'."""
    games = row.get("playoff_games")
    if pd.isna(games) or not games:
        return "Did not qualify"
    wins = int(row["playoff_wins"])
    losses = int(games) - wins
    text = f"{wins}-{losses}"
    if row.get("won_super_bowl"):
        text += " (won SB)"
    elif row.get("reached_super_bowl"):
        text += " (lost SB)"
    return text


def _vs_elite_text(row):
    """Win pct against elite (TSR z >= 1.0) regular-season opponents,
    with the opponent count, e.g. '66.7% (3)'. '-' if the team faced no
    elite opponent that season (see team_profile.py:record_vs_elite)."""
    n = row.get("elite_opponents_played")
    if pd.isna(n) or not n:
        return "-"
    return f"{_fmt(row['record_vs_elite_win_pct'] * 100, 1)}% ({int(n)})"


# The "full stat line" shared by season pages and the team-ranking query
# pages, so a stats-minded reader sees the same depth everywhere: not
# just True Strength Rating, but the descriptive sub-scores behind it
# (BUILD_PLAN section 3) and how the season actually ended.
FULL_STAT_COLUMNS = [
    ("conf_div", "Conf/Div", False),
    ("record", "Record", False),
    ("tsr_z", "TSR (z)", True),
    ("tsr_se", "TSR SE", True),
    ("acc", "ACC", True),
    ("offense_z", "Off (z)", True),
    ("defense_z", "Def (z)", True),
    ("dominance_z", "Dom (z)", True),
    ("schedule_difficulty", "Sched Diff", True),
    ("vs_elite", "vs Elite (z>=1)", False),
    ("playoffs", "Playoffs", False),
]


def _full_stat_row(r):
    return {
        "conf_div": f"{r['conference']} {r['division']}",
        "record": _record(r),
        "tsr_z": _fmt(r["bayes_rating_z"]),
        "tsr_se": _fmt(r["bayes_rating_se"]),
        "acc": _fmt(r["acc"], 1),
        "offense_z": _fmt(r["offense_z"]),
        "defense_z": _fmt(r["defense_z"]),
        "dominance_z": _fmt(r["dominance_z"]),
        "schedule_difficulty": _fmt(r["schedule_difficulty"]),
        "vs_elite": _vs_elite_text(r),
        "playoffs": _playoffs_text(r),
    }


_TEAM_SEASON_COLS = [("season", "Season", False), ("franchise", "Team", False)]

QUERY_META = [
    (
        "greatest_champions",
        "Greatest champions",
        "Super Bowl winners with the highest True Strength Rating.",
        _TEAM_SEASON_COLS + FULL_STAT_COLUMNS,
    ),
    (
        "weakest_champions",
        "Weakest champions",
        "Super Bowl winners with the lowest True Strength Rating - teams that won it all without being the best team on paper.",
        _TEAM_SEASON_COLS + FULL_STAT_COLUMNS,
    ),
    (
        "greatest_losers",
        "Greatest losers",
        "Super Bowl runners-up with the highest True Strength Rating - great teams that still came up short.",
        _TEAM_SEASON_COLS + FULL_STAT_COLUMNS,
    ),
    (
        "best_teams_never_to_win",
        "Best teams never to win",
        "The highest True Strength Rating of any team-season that didn't win that year's Super Bowl, playoffs or not.",
        _TEAM_SEASON_COLS + FULL_STAT_COLUMNS,
    ),
    (
        "largest_mismatches",
        "Largest Super Bowl mismatches",
        "Super Bowl matchups with the biggest True Strength gap between the two teams, both sides' full profile included.",
        [
            ("season", "Season", False),
            ("winner", "Winner", False),
            ("winner_record", "W Record", False),
            ("winner_bayes_rating_z", "W TSR (z)", True),
            ("winner_acc", "W ACC", True),
            ("winner_offense_z", "W Off (z)", True),
            ("winner_defense_z", "W Def (z)", True),
            ("loser", "Loser", False),
            ("loser_record", "L Record", False),
            ("loser_bayes_rating_z", "L TSR (z)", True),
            ("loser_acc", "L ACC", True),
            ("loser_offense_z", "L Off (z)", True),
            ("loser_defense_z", "L Def (z)", True),
            ("z_gap", "TSR gap", True),
            ("upset_label", "Upset?", False),
        ],
    ),
    (
        "greatest_conference_imbalance",
        "Greatest conference imbalance",
        "Seasons with the largest estimated strength gap between the AFC and NFC (Conference Strength Index), and that season's best team in each conference for concrete grounding.",
        [
            ("season", "Season", False),
            ("csi", "CSI", True),
            ("ci95", "95% range", False),
            ("stronger_conference", "Stronger conf", False),
            ("best_afc", "Best AFC team", False),
            ("best_nfc", "Best NFC team", False),
        ],
    ),
    (
        "best_decade",
        "Best decade",
        "Mean True Strength Rating of each decade's ten highest-rated team-seasons - since ratings are standardized within season, this asks which decade's best teams stood furthest above their own league average, not which decade scored the most points.",
        [
            ("decade", "Decade", False),
            ("seasons_covered", "Seasons", False),
            ("mean_top10_tsr_z", "Mean top-10 TSR (z)", True),
            ("n_elite_seasons", "Elite seasons (z>=1)", False),
            ("n_weak_seasons", "Weak seasons (z<=-1)", False),
            ("top3_team_seasons", "Top 3 team-seasons", False),
        ],
    ),
    (
        "records_that_most_overstated_strength",
        "Records that most overstated strength",
        "Team-seasons whose win-loss record was much better than their True Strength Rating - usually a lot of close wins mixed with a few lopsided losses.",
        [("season", "Season", False), ("franchise", "Team", False), ("win_pct", "Win pct", True), ("residual", "Gap", True)] + FULL_STAT_COLUMNS,
    ),
]

DATA_FILES = [
    ("team_seasons", "Team-season profile", "True Strength Rating, Accomplishment, and every descriptive sub-score for all 1,669 team-seasons, 1970-2025."),
    ("super_bowls", "Super Bowl matchups", "Every Super Bowl since 1970, both teams' ratings, and the final score."),
    ("conference_strength_index", "Conference Strength Index", "AFC-vs-NFC strength estimate and uncertainty range, one row per season."),
]


def load_data():
    games = load_games()
    profile = pd.read_csv(REPO / "data" / "processed" / "team_season_full_profile.csv")
    csi = pd.read_csv(REPO / "data" / "processed" / "conference_strength_index.csv")
    sb = find_super_bowl_games(games)
    return games, profile, csi, sb


def build_super_bowls_table(sb: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    z = profile.set_index(["season", "franchise"])
    rows = []
    for _, g in sb.iterrows():
        w = z.loc[(g["season"], g["winner"])]
        l = z.loc[(g["season"], g["loser"])]
        rows.append(
            {
                "season": int(g["season"]),
                "winner": g["winner"],
                "loser": g["loser"],
                "winner_score": int(g["winner_score"]),
                "loser_score": int(g["loser_score"]),
                "winner_tsr_z": w["bayes_rating_z"],
                "loser_tsr_z": l["bayes_rating_z"],
                "z_gap": w["bayes_rating_z"] - l["bayes_rating_z"],
            }
        )
    return pd.DataFrame(rows).sort_values("season", ascending=False)


def render_all(out_dir: Path = OUT_DIR):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "static").mkdir()
    (out_dir / "seasons").mkdir()
    (out_dir / "super-bowls").mkdir()
    (out_dir / "queries").mkdir()
    (out_dir / "data").mkdir()

    shutil.copy(TEMPLATES_DIR / "style.css", out_dir / "static" / "style.css")
    shutil.copytree(TEMPLATES_DIR / "images", out_dir / "images")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    generated_date = date.today().isoformat()

    def render(template_name, out_path, root, **context):
        template = env.get_template(template_name)
        html = template.render(root=root, generated_date=generated_date, **context)
        out_path.write_text(html, encoding="utf-8")

    games, profile, csi, sb = load_data()
    sb_table = build_super_bowls_table(sb, profile)
    queries = build_all_queries()

    seasons = sorted(profile["season"].unique().tolist())

    # --- index, methodology, electric football story ---
    render("index.html", out_dir / "index.html", root="")
    render("methodology.html", out_dir / "methodology.html", root="")
    render("electric_football.html", out_dir / "electric-football.html", root="")
    render("why.html", out_dir / "why.html", root="")
    render("what_it_means.html", out_dir / "what-it-means.html", root="")

    # --- seasons index ---
    by_decade = {}
    for s in seasons:
        by_decade.setdefault((s // 10) * 10, []).append(s)
    seasons_by_decade = [(d, sorted(v)) for d, v in sorted(by_decade.items())]
    render(
        "seasons_index.html",
        out_dir / "seasons" / "index.html",
        root="../",
        seasons=seasons,
        seasons_by_decade=seasons_by_decade,
    )

    # --- per-season pages ---
    for season in seasons:
        season_rows = profile[profile["season"] == season].sort_values("bayes_rating_z", ascending=False)
        teams = [
            {
                "franchise": r["franchise"],
                "division_title": "Yes" if r["division_title"] else "No",
                **_full_stat_row(r),
            }
            for _, r in season_rows.iterrows()
        ]
        csi_row = csi[csi["season"] == season].iloc[0]
        if csi_row["ci95_lower"] > 0:
            csi_text = f"AFC estimated stronger by {_fmt(csi_row['csi'])} points (95% range {_fmt(csi_row['ci95_lower'])} to {_fmt(csi_row['ci95_upper'])})."
        elif csi_row["ci95_upper"] < 0:
            csi_text = f"NFC estimated stronger by {_fmt(-csi_row['csi'])} points (95% range {_fmt(-csi_row['ci95_upper'])} to {_fmt(-csi_row['ci95_lower'])})."
        else:
            csi_text = f"No confidently stronger conference this season (estimate {_fmt(csi_row['csi'])}, 95% range {_fmt(csi_row['ci95_lower'])} to {_fmt(csi_row['ci95_upper'])})."
        render(
            "season.html",
            out_dir / "seasons" / f"{season}.html",
            root="../",
            season=season,
            n_teams=len(teams),
            teams=teams,
            csi_text=csi_text,
        )

    # --- super bowls index ---
    sb_rows = [
        {
            "season": int(r["season"]),
            "winner": r["winner"],
            "loser": r["loser"],
            "score": f"{r['winner_score']}-{r['loser_score']}",
            "z_gap": _fmt(r["z_gap"]),
            "upset_text": "Yes" if r["z_gap"] < 0 else "No",
        }
        for _, r in sb_table.iterrows()
    ]
    render("super_bowls_index.html", out_dir / "super-bowls" / "index.html", root="../", rows=sb_rows)

    # --- per-super-bowl pages ---
    for _, r in sb_table.iterrows():
        season = int(r["season"])
        w_row = profile[(profile["season"] == season) & (profile["franchise"] == r["winner"])].iloc[0]
        l_row = profile[(profile["season"] == season) & (profile["franchise"] == r["loser"])].iloc[0]
        upset_text = (
            "This was an upset by True Strength Rating: the losing team was rated stronger going in."
            if r["z_gap"] < 0
            else "The stronger team by True Strength Rating won."
        )

        def side(row, score):
            return {
                "franchise": row["franchise"],
                "score": int(score),
                "division_title": "Yes" if row["division_title"] else "No",
                **_full_stat_row(row),
            }

        render(
            "super_bowl.html",
            out_dir / "super-bowls" / f"{season}.html",
            root="../",
            season=season,
            winner=side(w_row, r["winner_score"]),
            loser=side(l_row, r["loser_score"]),
            upset_text=upset_text,
        )

    # --- queries ---
    render(
        "queries_index.html",
        out_dir / "queries" / "index.html",
        root="../",
        queries=[
            {"slug": slug.replace("_", "-"), "title": title, "description": desc}
            for slug, title, desc, _ in QUERY_META
        ],
    )
    full_stat_slugs = {
        "greatest_champions",
        "weakest_champions",
        "greatest_losers",
        "best_teams_never_to_win",
        "records_that_most_overstated_strength",
    }
    for slug, title, desc, cols in QUERY_META:
        page_slug = slug.replace("_", "-")
        table = queries[slug].copy()
        if slug in full_stat_slugs:
            stat_cols = pd.DataFrame(table.apply(_full_stat_row, axis=1).tolist(), index=table.index)
            table = table.drop(columns=stat_cols.columns, errors="ignore").join(stat_cols)
        if slug == "largest_mismatches":
            table["upset_label"] = table["upset"].map({True: "Yes", False: "No"})
            table["winner_record"] = table.apply(
                lambda r: _record({"wins": r["winner_wins"], "losses": r["winner_losses"], "ties": r["winner_ties"]}), axis=1
            )
            table["loser_record"] = table.apply(
                lambda r: _record({"wins": r["loser_wins"], "losses": r["loser_losses"], "ties": r["loser_ties"]}), axis=1
            )
        if slug == "greatest_conference_imbalance":
            table["ci95"] = table.apply(lambda r: f"{_fmt(r['ci95_lower'])} to {_fmt(r['ci95_upper'])}", axis=1)
        rows = []
        for _, r in table.iterrows():
            row = {}
            for key, _, is_num in cols:
                val = r[key]
                if isinstance(val, str):
                    row[key] = val
                elif key == "season":
                    row[key] = int(val)
                elif key == "win_pct":
                    row[key] = _fmt(val * 100, 1) + "%"
                elif key == "acc":
                    row[key] = _fmt(val, 1)
                elif is_num or isinstance(val, float):
                    row[key] = _fmt(val)
                else:
                    row[key] = val
            rows.append(row)
        columns = [{"key": key, "label": label, "num": is_num} for key, label, is_num in cols]
        render(
            "query.html",
            out_dir / "queries" / f"{page_slug}.html",
            root="../",
            title=title,
            description=desc,
            columns=columns,
            rows=rows,
        )

    # --- data exports ---
    export_tables = {
        "team_seasons": profile,
        "super_bowls": sb_table,
        "conference_strength_index": csi,
    }
    for name, table in export_tables.items():
        table.to_csv(out_dir / "data" / f"{name}.csv", index=False)
        (out_dir / "data" / f"{name}.json").write_text(
            table.to_json(orient="records", indent=2), encoding="utf-8"
        )
    render("data_index.html", out_dir / "data" / "index.html", root="../", files=[
        {"slug": slug, "title": title, "description": desc} for slug, title, desc in DATA_FILES
    ])

    build_studies(out_dir)
    print(f"Site generated at {out_dir} ({len(seasons)} season pages, {len(sb_table)} Super Bowl pages, {len(QUERY_META)} query pages)")


# Side studies live in studies/<name>/ with their own src/, data/, tests/ and
# templates, and publish as a sub-site at /<name>/ of this site. Each one's
# site generator exposes render_all(out_dir).
STUDIES = [("home-field-advantage", "hfa_site"), ("explosive-edge", "xe_site")]


def build_studies(out_dir: Path) -> None:
    import importlib.util

    for name, module in STUDIES:
        src = REPO / "studies" / name / "src"
        spec = importlib.util.spec_from_file_location(module, src / f"{module}.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.render_all(out_dir / name)


if __name__ == "__main__":
    render_all()
