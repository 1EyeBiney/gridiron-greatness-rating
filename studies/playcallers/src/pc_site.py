"""
Renders the static site for "The Playcallers" into site/ from the tables
committed in data/processed/ and data/reference/. site/ is never committed
- it is regenerated from data every build, same pattern as the sibling
explosive-edge study: semantic landmarks, real tables with scope
attributes, a skip link, and no charts - every number is in a table and
every table is downloadable.
"""
from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "processed"
REFERENCE = REPO / "data" / "reference"
TEMPLATES_DIR = Path(__file__).resolve().parent / "site_templates"
OUT_DIR = REPO / "site"
REPO_URL = "https://github.com/1EyeBiney/gridiron-greatness-rating/tree/master/studies/playcallers"
MAIN_SITE = "../"  # this site is published under the main site as /playcallers/

FIRST_SEASON, LAST_SEASON = 1999, 2025

BASIS_LABELS = {
    "default_coordinator": "Coordinator by title",
    "model_knowledge_unverified": "Believed, unverified",
    "continuity_guess": "Guess from adjacent seasons",
    "default_no_coordinator_headcoach": "No coordinator listed (not rated)",
    "evidence_wikipedia": "Stated on Wikipedia",
}


def basis_label(b) -> str:
    if pd.isna(b):
        return "-"
    return BASIS_LABELS.get(b, str(b))


# ------------------------------------------------------------ formatting


def f1(x) -> str:
    return "-" if pd.isna(x) else f"{x:.1f}"


def f2(x) -> str:
    return "-" if pd.isna(x) else f"{x:.2f}"


def f3(x) -> str:
    return "-" if pd.isna(x) else f"{x:.3f}"


def pct(x) -> str:
    return "-" if pd.isna(x) else f"{100 * x:.1f}%"


def n_(x) -> str:
    return "-" if pd.isna(x) else f"{int(x):,}"


def yn(x) -> str:
    if pd.isna(x):
        return "-"
    return "Yes" if bool(x) else "No"


def s_(x) -> str:
    return "-" if pd.isna(x) else str(x)


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


# ------------------------------------------------------------------ facts


def load_tables() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in DATA.glob("*.csv")}


def build_facts(t: dict[str, pd.DataFrame]) -> dict:
    """Every number the Findings / What It Means prose uses, computed from
    the committed tables so the text and the tables can't disagree."""
    careers = t["playcaller_careers"]
    seasons = t["playcaller_seasons"]
    draft = t["playcaller_draft"]
    excluded = t["playcaller_excluded_unit_seasons"]
    qb_adj = t["playcaller_qb_adjusted"]
    qb_cv = t["playcaller_qb_model_cv"]
    var_comp = t["playcaller_variance_components"]
    moves = t["playcaller_moves"]
    moves_summary = t["playcaller_moves_summary"]
    tree_summary = t["coaching_tree_summary"]
    stints = t["staff_stints_all"]

    n_unit_seasons = int(len(draft))
    n_rated = int(len(seasons))
    n_excluded = int(len(excluded))

    basis_counts = seasons["basis"].value_counts().to_dict()
    basis_counts_draft = draft["basis"].value_counts().to_dict()

    first_season = int(seasons["season"].min())
    last_season = int(seasons["season"].max())

    def top10(unit: str) -> list[dict]:
        d = careers[(careers["unit"] == unit) & careers["rank_in_unit"].notna()]
        d = d.sort_values("rank_in_unit").head(10)
        return d.to_dict(orient="records")

    def career_row(person: str, unit: str) -> dict:
        d = careers[(careers["person"] == person) & (careers["unit"] == unit)]
        return d.iloc[0].to_dict() if len(d) else {}

    var_by_unit = {row["unit"]: row.to_dict() for _, row in var_comp.iterrows()}

    cv = {row["model"]: row.to_dict() for _, row in qb_cv.iterrows()}

    def qb_adj_rank(person: str) -> int | None:
        d = qb_adj.sort_values("rating_qb_adjusted", ascending=False).reset_index(drop=True)
        hit = d.index[d["person"] == person]
        return int(hit[0]) + 1 if len(hit) else None

    def unadjusted_rank(person: str, unit: str = "offense") -> int | None:
        d = careers[(careers["unit"] == unit) & careers["rank_in_unit"].notna()]
        hit = d[d["person"] == person]
        return int(hit.iloc[0]["rank_in_unit"]) if len(hit) else None

    moves_summary_idx = {(row["unit"], row["quantity"]): row.to_dict() for _, row in moves_summary.iterrows()}

    tree_top = tree_summary.sort_values("n_became_head_coach", ascending=False).head(10).to_dict(orient="records")
    n_coordinator_gaps = int((excluded["reason"].str.contains("no_coordinator_listed", na=False)).sum())

    n_disagreements = int((stints["disagreement"] == True).sum())  # noqa: E712
    n_stint_rows = int(len(stints))
    source_agreement_rate = 1 - (n_disagreements / n_stint_rows) if n_stint_rows else None

    kc = qb_cv.set_index("model") if "model" in qb_cv.columns else None

    return {
        "n_unit_seasons": n_unit_seasons,
        "n_rated": n_rated,
        "n_excluded": n_excluded,
        "basis_counts": basis_counts,
        "basis_counts_draft": basis_counts_draft,
        "first_season": first_season,
        "last_season": last_season,
        "top10_offense": top10("offense"),
        "top10_defense": top10("defense"),
        "ben_johnson": career_row("Ben Johnson", "offense"),
        "mike_macdonald": career_row("Mike Macdonald", "defense"),
        "ben_johnson_qb_adj_rank": qb_adj_rank("Ben Johnson"),
        "ben_johnson_unadjusted_rank": unadjusted_rank("Ben Johnson", "offense"),
        "variance_components": var_by_unit,
        "qb_model_cv": cv,
        "qb_model_crossed_mse": cv.get("crossed_caller_qb", {}).get("cv_mse"),
        "qb_model_caller_only_mse": cv.get("caller_only", {}).get("cv_mse"),
        "qb_model_qb_only_mse": cv.get("qb_only", {}).get("cv_mse"),
        "moves_summary": moves_summary_idx,
        "n_moves": int(len(moves)),
        "n_offense_moves": int((moves["unit"] == "offense").sum()),
        "n_defense_moves": int((moves["unit"] == "defense").sum()),
        "top_coaching_trees": tree_top,
        "n_coordinator_gaps": n_coordinator_gaps,
        "source_agreement_rate": source_agreement_rate,
        # biography coaching histories checked against team-season pages where both name a
        # coordinator (src/pc_gapfill_step5_validate.py, second pass; docs/PHASE1C_REPORT.md)
        "bio_agree_n": 1157, "bio_checked_n": 1172,
        "n_source_disagreements": n_disagreements,
        "n_stint_rows": n_stint_rows,
        "n_franchises": 32,
    }


# ----------------------------------------------------------------- columns

CAREER_RANKED_COLS = [
    ("rank_in_unit", "Rank", lambda x: str(int(x)), True),
    ("person", "Name", s_, False),
    ("seasons", "Seasons", n_, True),
    ("span", "First-last season", s_, False),
    ("franchises", "Teams", s_, False),
    ("mean_z_epa", "Average score (mean EPA z)", f2, True),
    ("rating", "Career rating", f2, True),
    ("rating_se", "±", f2, True),
    ("best_season", "Best season", s_, False),
    ("share_unverified", "Share of seasons unverified", pct, True),
    ("mean_z_explosive", "Explosive-play average (z)", f2, True),
    ("mean_z_ypp", "Yards/play average (z)", f2, True),
]

CAREER_UNRANKED_COLS = [c for c in CAREER_RANKED_COLS if c[0] != "rank_in_unit"]

QB_ADJUSTED_COLS = [
    ("rank", "Rank", lambda x: str(int(x)), True),
    ("person", "Name", s_, False),
    ("n_seasons", "Seasons", n_, True),
    ("n_distinct_qbs", "Distinct QBs", n_, True),
    ("separable", "Separable from QB", yn, False),
    ("rating_qb_adjusted", "QB-adjusted rating", f3, True),
    ("unadjusted_rank", "Unadjusted-list rank", lambda x: "-" if pd.isna(x) else str(int(x)), True),
]

QB_CV_COLS = [
    ("model", "Model", s_, False),
    ("lam_caller", "λ caller", f1, True),
    ("lam_qb", "λ QB", f1, True),
    ("cv_mse", "Cross-validated MSE", f3, True),
]

QB_EFFECT_COLS = [
    ("primary_qb_name", "Quarterback", s_, False),
    ("qb_effect", "QB effect (EPA z)", f3, True),
]

MOVES_SUMMARY_COLS = [
    ("unit", "Unit", s_, False),
    ("quantity", "Quantity", s_, False),
    ("n", "N", n_, True),
    ("mean", "Mean (EPA z)", f2, True),
    ("se", "± SE", f2, True),
]

MOVES_COLS = [
    ("person", "Person", s_, False),
    ("unit", "Unit", s_, False),
    ("old_franchise", "From team", s_, False),
    ("old_season", "From season", lambda x: str(int(x)), True),
    ("new_franchise", "To team", s_, False),
    ("new_season", "To season", lambda x: str(int(x)), True),
    ("old_team_with", "Old team, with him", f2, True),
    ("old_team_after", "Old team, after he left", f2, True),
    ("new_team_before", "New team, before him", f2, True),
    ("new_team_with", "New team, with him", f2, True),
    ("departure_change", "Departure change", f2, True),
    ("arrival_change", "Arrival change", f2, True),
]

TREE_COLS = [
    ("mentor", "Mentor", s_, False),
    ("n_distinct_coordinators", "Coordinators", n_, True),
    ("n_became_head_coach", "Later head coaches", n_, True),
    ("became_head_coach_detail", "Who", s_, False),
    ("n_already_head_coach", "Already head coach", n_, True),
    ("already_head_coach_detail", "Who", s_, False),
]

FRANCHISE_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), True),
    ("head_coach", "Head coach", s_, False),
    ("offensive_coordinator", "Offensive coordinator", s_, False),
    ("offensive_playcaller", "Offensive play caller", s_, False),
    ("offensive_basis", "Basis", basis_label, False),
    ("defensive_coordinator", "Defensive coordinator", s_, False),
    ("defensive_playcaller", "Defensive play caller", s_, False),
    ("defensive_basis", "Basis", basis_label, False),
    ("flags", "Flags", s_, False),
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


def _career_tables(careers: pd.DataFrame, unit: str) -> tuple[Markup, Markup]:
    d = careers[careers["unit"] == unit].copy()
    d["span"] = d["first_season"].astype(int).astype(str) + "-" + d["last_season"].astype(int).astype(str)
    ranked = d[d["rank_in_unit"].notna()].sort_values("rank_in_unit")
    unranked = d[d["rank_in_unit"].isna()].sort_values("rating", ascending=False)
    label = unit.capitalize()
    ranked_html = table_html(ranked, CAREER_RANKED_COLS,
                              f"{label} play-callers, ranked (3+ seasons), 1999-2025")
    unranked_html = table_html(unranked, CAREER_UNRANKED_COLS,
                                f"{label} play-callers with fewer than three seasons, sorted by rating", "person")
    return ranked_html, unranked_html


def _who_called_plays_tables(draft: pd.DataFrame) -> dict[str, Markup]:
    """One table per franchise, seasons 1999-2025, offense+defense columns."""
    tables: dict[str, Markup] = {}
    for franchise, g in draft.groupby("franchise"):
        off = g[g["unit"] == "offense"].set_index("season")
        deff = g[g["unit"] == "defense"].set_index("season")
        rows = []
        seasons = sorted(set(off.index) | set(deff.index))
        for s in seasons:
            o = off.loc[s] if s in off.index else None
            d = deff.loc[s] if s in deff.index else None
            head_coach = (o["head_coach"] if o is not None and pd.notna(o.get("head_coach")) else
                          (d["head_coach"] if d is not None else None))
            flags = []
            if o is not None and bool(o.get("midseason_change", False)):
                flags.append("Offense: mid-season change")
            if d is not None and bool(d.get("midseason_change", False)):
                flags.append("Defense: mid-season change")
            rows.append({
                "season": s,
                "head_coach": head_coach,
                "offensive_coordinator": o["coordinator"] if o is not None else np.nan,
                "offensive_playcaller": o["proposed_playcaller"] if o is not None else np.nan,
                "offensive_basis": o["basis"] if o is not None else np.nan,
                "defensive_coordinator": d["coordinator"] if d is not None else np.nan,
                "defensive_playcaller": d["proposed_playcaller"] if d is not None else np.nan,
                "defensive_basis": d["basis"] if d is not None else np.nan,
                "flags": "; ".join(flags) if flags else "-",
            })
        df = pd.DataFrame(rows)
        tables[franchise] = table_html(df, FRANCHISE_SEASON_COLS,
                                        f"{franchise}: proposed play-caller by season, 1999-2025 (best guess)",
                                        row_header="season")
    return tables


REASON_TEXT = {
    "midseason_change": "the head coach or coordinator changed during the season",
    "multiple_playcallers": "more than one play caller is named",
    "no_coordinator_listed": "no coordinator is listed",
    "no_proposed_playcaller": "no play caller could be identified",
}

CASE_STOP_COLS = [
    ("team", "Team", s_, False), ("span", "Seasons", s_, False), ("n", "Rated seasons", n_, True),
    ("mean", "Average score", f2, True), ("qbs", "Primary quarterbacks", s_, False),
]
CASE_SEASON_COLS = [
    ("season", "Season", lambda x: str(int(x)), False), ("team", "Team", s_, False),
    ("primary_qb_name", "Primary quarterback", s_, False),
    ("z_epa", "Score (efficiency per play)", f2, True), ("z_explosive", "Explosive plays", f2, True),
    ("z_ypp", "Yards per play", f2, True), ("basis_text", "How the play caller was decided", s_, False),
]


def ordinal(n) -> str:
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def build_case_pages(t: dict, env) -> list[dict]:
    """Render each case file's prose (numbers injected from its own facts)
    and its two tables. Returns the cases ready for the templates."""
    import pc_case_files as cf
    order = [cf.PROMPTED, cf.BETTER, cf.REPUTATION, cf.ONE_STOP, cf.QUARTERBACK, cf.TRAVELLED]
    cases = []
    for case in cf.build_cases(t):
        k = case["k"]
        unit = case["unit"]
        text = lambda src: str(env.from_string(src).render(k=k))          # noqa: E731
        stops = pd.DataFrame([{"team": r["team"], "span": f"{r['first']}-{r['last']}" if r["last"] > r["first"] else str(r["first"]),
                               "n": r["n"], "mean": r["mean"], "qbs": ", ".join(r["qbs"])} for r in k["runs"]])
        seasons = k["seasons_table"].copy()
        seasons["team"] = seasons["franchise"].map(cf.TEAM_NAMES).fillna(seasons["franchise"])
        seasons["basis_text"] = seasons["basis"].map(basis_label)
        drop_qb = (lambda cols: [c for c in cols if c[0] not in ("primary_qb_name", "qbs")]) if unit == "defense" else (lambda cols: cols)
        for e in k["excluded"]:
            e["team"] = cf.TEAM_NAMES.get(e["franchise"], e["franchise"])
            e["reason_text"] = "; ".join(REASON_TEXT.get(x, x) for x in str(e["reason"]).split(";"))
        cases.append({
            **case, "category_order": order.index(case["category"]),
            "verdict_text": text(case["verdict"]), "body_text": [text(p) for p in case["body"]],
            "stops_table": table_html(stops, drop_qb(CASE_STOP_COLS), f"{case['person']}: {unit} record by stop"),
            "seasons_table": table_html(seasons, drop_qb(CASE_SEASON_COLS),
                                        f"{case['person']}: every rated {unit} season", row_header="season"),
        })
    return cases


def render_all(out_dir: Path = OUT_DIR) -> dict:
    # The site builds only from the committed CSVs in data/processed and
    # data/reference. No analysis runs at render time; the pipeline scripts
    # in src/ (pc_unit_ratings.py, pc_playcaller_ratings.py, etc.) are run
    # by hand to regenerate those tables.
    t = load_tables()
    facts = build_facts(t)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.filters.update({"f0": lambda x: "-" if pd.isna(x) else f"{x:.0f}", "f1": f1, "f2": f2, "f3": f3,
                        "pct": pct, "n": n_, "ordinal": ordinal})
    cases = build_case_pages(t, env)
    facts["n_case_files"] = len(cases)
    facts["cases"] = {c["slug"]: c["k"] for c in cases}

    _reset_output_dir(out_dir)
    (out_dir / "static").mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(exist_ok=True)
    shutil.copy(TEMPLATES_DIR / "style.css", out_dir / "static" / "style.css")
    images_dir = TEMPLATES_DIR / "images"
    if images_dir.exists():
        shutil.copytree(images_dir, out_dir / "images", dirs_exist_ok=True)
    else:
        (out_dir / "images").mkdir(parents=True, exist_ok=True)

    common = {"generated_date": date.today().isoformat(), "repo_url": REPO_URL, "main_site": MAIN_SITE, "facts": facts}

    def render(template: str, target: Path, **ctx):
        html = env.get_template(template).render(**common, **ctx)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    careers = t["playcaller_careers"]
    tables: dict[str, Markup] = {}

    tables["offense_ranked"], tables["offense_unranked"] = _career_tables(careers, "offense")
    tables["defense_ranked"], tables["defense_unranked"] = _career_tables(careers, "defense")

    qb_adj = t["playcaller_qb_adjusted"].copy()
    qb_adj = qb_adj.sort_values("rating_qb_adjusted", ascending=False).reset_index(drop=True)
    qb_adj["rank"] = qb_adj.index + 1
    off_ranks = careers[(careers["unit"] == "offense")].set_index("person")["rank_in_unit"]
    qb_adj["unadjusted_rank"] = qb_adj["person"].map(off_ranks)
    qb_top40 = qb_adj.head(40)
    tables["qb_adjusted_top40"] = table_html(
        qb_top40, [("rank", "Rank", lambda x: str(int(x)), True), ("person", "Name", s_, False)] +
        QB_ADJUSTED_COLS[2:], "Top 40 offensive play-callers by quarterback-adjusted rating", row_header="person")
    tables["qb_model_cv"] = table_html(t["playcaller_qb_model_cv"], QB_CV_COLS,
                                       "Quarterback-adjusted model: cross-validated mean squared error by model")
    qb_effects = t["qb_effects_from_caller_model"].copy() if "qb_effects_from_caller_model" in t else pd.DataFrame()
    if len(qb_effects):
        qb_effects = qb_effects.sort_values("qb_effect", ascending=False).head(20)
        tables["qb_effects_top20"] = table_html(qb_effects, QB_EFFECT_COLS,
                                                "Top 20 quarterback effects from the crossed caller/QB model")

    tables["moves_summary"] = table_html(t["playcaller_moves_summary"], MOVES_SUMMARY_COLS,
                                         "Moves summary: arrival and departure changes vs regression-to-the-mean baselines, by unit")
    moves_sorted = t["playcaller_moves"].sort_values("new_season")
    tables["moves_full"] = table_html(moves_sorted, MOVES_COLS,
                                      "Every play-caller move, 1999-2025, sorted by season", row_header="person")

    tree = t["coaching_tree_summary"]
    tree_qualified = tree[tree["n_distinct_coordinators"] >= 2].sort_values(
        "n_became_head_coach", ascending=False)
    tables["coaching_trees"] = table_html(tree_qualified, TREE_COLS,
                                          "Coaching trees: mentors with at least two coordinators, ranked by how many later became head coaches")

    who_tables = _who_called_plays_tables(t["playcaller_draft"])

    files = []
    for p in sorted(DATA.glob("*.csv")):
        shutil.copy(p, out_dir / "data" / p.name)
        files.append({"name": p.name, "size_kb": max(1, p.stat().st_size // 1024),
                      "description": DATA_DESCRIPTIONS.get(p.name, "Derived table used by this site.")})
    overrides_path = REFERENCE / "playcaller_overrides_summary.csv"
    if overrides_path.exists():
        shutil.copy(overrides_path, out_dir / "data" / overrides_path.name)
        files.append({"name": overrides_path.name, "size_kb": max(1, overrides_path.stat().st_size // 1024),
                      "description": DATA_DESCRIPTIONS.get(overrides_path.name,
                                                            "Hand-reviewed play-caller override list with sources and confidence.")})
    files.sort(key=lambda f: f["name"])

    render("index.html", out_dir / "index.html", root="", tables=tables)
    render("offense.html", out_dir / "offense.html", root="", tables=tables)
    render("defense.html", out_dir / "defense.html", root="", tables=tables)
    render("qb_adjusted.html", out_dir / "qb-adjusted.html", root="", tables=tables)
    render("movers.html", out_dir / "movers.html", root="", tables=tables)
    render("coaching_trees.html", out_dir / "coaching-trees.html", root="", tables=tables)
    render("who_called_plays.html", out_dir / "who-called-plays.html", root="",
           franchises=sorted(who_tables.keys()), who_tables=who_tables)
    render("what_it_means.html", out_dir / "what-it-means.html", root="")
    render("methodology.html", out_dir / "methodology.html", root="")
    render("data_index.html", out_dir / "data" / "index.html", root="../", files=files)
    render("case_files_index.html", out_dir / "case-files" / "index.html", root="../", cases=cases)
    for case in cases:
        render("case_file.html", out_dir / "case-files" / f"{case['slug']}.html", root="../", case=case, k=case["k"],
               stops_table=case["stops_table"], seasons_table=case["seasons_table"])

    return facts


DATA_DESCRIPTIONS = {
    "playcaller_careers.csv": "One row per person per unit: career averages, shrunk rating, and rank.",
    "playcaller_seasons.csv": "One row per team-season-unit actually used in the ratings, with basis and confidence.",
    "playcaller_draft.csv": "Every team-season-unit's proposed play-caller, including excluded rows, with source and basis.",
    "playcaller_qb_adjusted.csv": "Offense ratings after splitting credit between the play-caller and the primary quarterback.",
    "playcaller_qb_model_cv.csv": "Cross-validated fit of the caller-only, QB-only, and crossed caller/QB models.",
    "playcaller_variance_components.csv": "Within- and between-person variance by unit, and seasons needed for half shrinkage weight.",
    "playcaller_moves.csv": "Every tracked move from one team to another, with before/after ratings at both stops.",
    "playcaller_moves_summary.csv": "Arrival/departure changes and regression-to-the-mean baselines, averaged by unit.",
    "playcaller_excluded_unit_seasons.csv": "Team-season-units left out of the ratings, with the reason (mid-season change, no coordinator listed, etc).",
    "coaching_tree_summary.csv": "Every mentor (head coach) and how many of his coordinators later became head coaches.",
    "coaching_tree_edges.csv": "Every mentor-to-protege edge: a coordinator who served under a head coach.",
    "unit_season_ratings.csv": "Opponent-adjusted offense/defense ratings per team-season-metric, before assigning them to a person.",
    "staff_stints_all.csv": "Every head coach/coordinator stint extracted from Wikipedia, 1999-2025, with source and any disagreement flag.",
    "playcaller_overrides_summary.csv": "Hand-reviewed list of play-caller overrides (cases where the titled coordinator is not the assumed play-caller), with source and confidence.",
    "qb_effects_from_caller_model.csv": "Per-quarterback effect estimated jointly with the caller effect in the QB-adjusted model.",
}


if __name__ == "__main__":
    render_all()
    print(f"Site generated at {OUT_DIR}")
