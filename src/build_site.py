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

QUERY_META = [
    (
        "greatest_champions",
        "Greatest champions",
        "Super Bowl winners with the highest True Strength Rating.",
        [("season", "Season", False), ("franchise", "Team", False), ("bayes_rating_z", "TSR (z)", True), ("win_pct", "Record", False)],
    ),
    (
        "weakest_champions",
        "Weakest champions",
        "Super Bowl winners with the lowest True Strength Rating - teams that won it all without being the best team on paper.",
        [("season", "Season", False), ("franchise", "Team", False), ("bayes_rating_z", "TSR (z)", True), ("win_pct", "Record", False)],
    ),
    (
        "greatest_losers",
        "Greatest losers",
        "Super Bowl runners-up with the highest True Strength Rating - great teams that still came up short.",
        [("season", "Season", False), ("franchise", "Team", False), ("bayes_rating_z", "TSR (z)", True), ("win_pct", "Record", False)],
    ),
    (
        "best_teams_never_to_win",
        "Best teams never to win",
        "The highest True Strength Rating of any team-season that didn't win that year's Super Bowl, playoffs or not.",
        [("season", "Season", False), ("franchise", "Team", False), ("bayes_rating_z", "TSR (z)", True), ("win_pct", "Record", False)],
    ),
    (
        "largest_mismatches",
        "Largest Super Bowl mismatches",
        "Super Bowl matchups with the biggest True Strength gap between the two teams.",
        [("season", "Season", False), ("winner", "Winner", False), ("loser", "Loser", False), ("z_gap", "TSR gap", True), ("upset_label", "Upset?", False)],
    ),
    (
        "greatest_conference_imbalance",
        "Greatest conference imbalance",
        "Seasons with the largest estimated strength gap between the AFC and NFC (Conference Strength Index).",
        [("season", "Season", False), ("csi", "CSI", True), ("ci95", "95% range", False), ("stronger_conference", "Stronger conference", False)],
    ),
    (
        "best_decade",
        "Best decade",
        "Mean True Strength Rating of each decade's ten highest-rated team-seasons - since ratings are standardized within season, this asks which decade's best teams stood furthest above their own league average, not which decade scored the most points.",
        [("decade", "Decade", False), ("mean_top10_tsr_z", "Mean top-10 TSR (z)", True), ("best_team_season", "Best team-season", False), ("best_tsr_z", "Its TSR (z)", True)],
    ),
    (
        "records_that_most_overstated_strength",
        "Records that most overstated strength",
        "Team-seasons whose win-loss record was much better than their True Strength Rating - usually a lot of close wins mixed with a few lopsided losses.",
        [("season", "Season", False), ("franchise", "Team", False), ("win_pct", "Win pct", True), ("bayes_rating_z", "TSR (z)", True), ("residual", "Gap", True)],
    ),
]

DATA_FILES = [
    ("team_seasons", "Team-season profile", "True Strength Rating, Accomplishment, and every descriptive sub-score for all 1,669 team-seasons, 1970-2025."),
    ("super_bowls", "Super Bowl matchups", "Every Super Bowl since 1970, both teams' ratings, and the final score."),
    ("conference_strength_index", "Conference Strength Index", "AFC-vs-NFC strength estimate and uncertainty range, one row per season."),
]


def _fmt(x, decimals=2):
    if pd.isna(x):
        return "-"
    return f"{x:.{decimals}f}"


def _record(row):
    rec = f"{int(row['wins'])}-{int(row['losses'])}"
    if row.get("ties", 0):
        rec += f"-{int(row['ties'])}"
    return rec


def _season_result_text(row):
    if row.get("won_super_bowl"):
        return "Won the Super Bowl"
    if row.get("reached_super_bowl"):
        return "Lost the Super Bowl"
    if row.get("division_title"):
        return "Division champion"
    return ""


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


def render_all():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)
    (OUT_DIR / "static").mkdir()
    (OUT_DIR / "seasons").mkdir()
    (OUT_DIR / "super-bowls").mkdir()
    (OUT_DIR / "queries").mkdir()
    (OUT_DIR / "data").mkdir()

    shutil.copy(TEMPLATES_DIR / "style.css", OUT_DIR / "static" / "style.css")

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

    # --- index & methodology ---
    render("index.html", OUT_DIR / "index.html", root="")
    render("methodology.html", OUT_DIR / "methodology.html", root="")

    # --- seasons index ---
    by_decade = {}
    for s in seasons:
        by_decade.setdefault((s // 10) * 10, []).append(s)
    seasons_by_decade = [(d, sorted(v)) for d, v in sorted(by_decade.items())]
    render(
        "seasons_index.html",
        OUT_DIR / "seasons" / "index.html",
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
                "conference": r["conference"],
                "division": r["division"],
                "record": _record(r),
                "tsr_z": _fmt(r["bayes_rating_z"]),
                "acc": _fmt(r["acc"], 1),
                "result": _season_result_text(r),
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
            OUT_DIR / "seasons" / f"{season}.html",
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
    render("super_bowls_index.html", OUT_DIR / "super-bowls" / "index.html", root="../", rows=sb_rows)

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
                "record": _record(row),
                "tsr_z": _fmt(row["bayes_rating_z"]),
                "acc": _fmt(row["acc"], 1),
                "division_title": "Yes" if row["division_title"] else "No",
            }

        render(
            "super_bowl.html",
            OUT_DIR / "super-bowls" / f"{season}.html",
            root="../",
            season=season,
            winner=side(w_row, r["winner_score"]),
            loser=side(l_row, r["loser_score"]),
            upset_text=upset_text,
        )

    # --- queries ---
    render(
        "queries_index.html",
        OUT_DIR / "queries" / "index.html",
        root="../",
        queries=[{"slug": slug, "title": title, "description": desc} for slug, title, desc, _ in QUERY_META],
    )
    for slug, title, desc, cols in QUERY_META:
        table = queries[slug].copy()
        if slug == "largest_mismatches":
            table["upset_label"] = table["upset"].map({True: "Yes", False: "No"})
        if slug == "greatest_conference_imbalance":
            table["ci95"] = table.apply(lambda r: f"{_fmt(r['ci95_lower'])} to {_fmt(r['ci95_upper'])}", axis=1)
        rows = []
        for _, r in table.iterrows():
            row = {}
            for key, _, is_num in cols:
                val = r[key]
                if is_num:
                    row[key] = _fmt(val)
                elif key == "win_pct":
                    row[key] = _fmt(val * 100, 1) + "%"
                elif isinstance(val, float) and key not in ("season",):
                    row[key] = _fmt(val)
                elif key == "season":
                    row[key] = int(val)
                else:
                    row[key] = val
            rows.append(row)
        columns = [{"key": key, "label": label, "num": is_num} for key, label, is_num in cols]
        render(
            "query.html",
            OUT_DIR / "queries" / f"{slug.replace('_', '-')}.html",
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
        table.to_csv(OUT_DIR / "data" / f"{name}.csv", index=False)
        (OUT_DIR / "data" / f"{name}.json").write_text(
            table.to_json(orient="records", indent=2), encoding="utf-8"
        )
    render("data_index.html", OUT_DIR / "data" / "index.html", root="../", files=[
        {"slug": slug, "title": title, "description": desc} for slug, title, desc in DATA_FILES
    ])

    print(f"Site generated at {OUT_DIR} ({len(seasons)} season pages, {len(sb_table)} Super Bowl pages, {len(QUERY_META)} query pages)")


if __name__ == "__main__":
    render_all()
