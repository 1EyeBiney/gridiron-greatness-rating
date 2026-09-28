"""Phase 0: cross-check the extracted head coach against the nflverse
schedule file (studies/home-field-advantage/data/raw/nflverse/games.csv),
which carries home_coach/away_coach per game. This validates the wiki
parsing independently of the wiki pages themselves.

Run from the study folder: python src/pc_headcoach_check.py
Writes data/processed/staff_phase0_headcoach_check.csv.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

STUDY = Path(__file__).resolve().parent.parent
MAIN = STUDY.parents[1]
XE_SRC = MAIN / "studies" / "explosive-edge" / "src"
if str(XE_SRC) not in sys.path:
    sys.path.insert(0, str(XE_SRC))

import xe_metrics  # noqa: E402

GAMES = MAIN / "studies" / "home-field-advantage" / "data" / "raw" / "nflverse" / "games.csv"


def last_name(name: str) -> str:
    name = re.sub(r"\(.*?\)", "", name).strip()
    parts = name.split()
    return parts[-1].lower() if parts else name.lower()


def schedule_coaches_by_franchise_season() -> pd.DataFrame:
    """One row per (franchise, season, coach) with a game count, built from
    the schedule file's home_coach/away_coach columns mapped through the
    same franchise crosswalk explosive-edge uses (xe_metrics.to_franchise)."""
    g = pd.read_csv(GAMES)
    g = g[g["game_type"].isin(["REG", "POST", "WC", "DIV", "CON", "SB"])]
    cw = xe_metrics.load_crosswalk()

    home = g[["season", "home_team", "home_coach"]].rename(
        columns={"home_team": "team", "home_coach": "coach"})
    away = g[["season", "away_team", "away_coach"]].rename(
        columns={"away_team": "team", "away_coach": "coach"})
    long = pd.concat([home, away], ignore_index=True)
    long = long.dropna(subset=["coach"])
    long["franchise"] = xe_metrics.to_franchise(long["team"], long["season"], cw)

    counts = long.groupby(["franchise", "season", "coach"]).size().reset_index(name="games")
    counts = counts.sort_values(["franchise", "season", "games"], ascending=[True, True, False])
    return counts


def build_check(staff_path: Path) -> pd.DataFrame:
    staff = pd.read_csv(staff_path)
    sched = schedule_coaches_by_franchise_season()

    rows = []
    for _, r in staff.iterrows():
        season, franchise = r["season"], r["franchise"]
        wiki_hc = str(r["head_coach"]) if pd.notna(r["head_coach"]) else ""
        wiki_names = [n.strip() for n in wiki_hc.split("|") if n.strip()]
        wiki_lastnames = {last_name(n) for n in wiki_names}

        sub = sched[(sched.franchise == franchise) & (sched.season == season)]
        sched_summary = "; ".join(f"{row.coach} ({row.games}g)" for row in sub.itertuples())
        sched_lastnames = {last_name(row.coach) for row in sub.itertuples()}

        match = bool(wiki_lastnames) and bool(sched_lastnames) and wiki_lastnames.issubset(sched_lastnames) or (
            bool(wiki_lastnames) and bool(sched_lastnames) and len(wiki_lastnames & sched_lastnames) > 0
            and wiki_lastnames.issubset(sched_lastnames)
        )
        # A clean match: every wiki head-coach last name appears among the
        # schedule's coaches for that team-season (order/count not required,
        # since the schedule can list a Week 18 fill-in the wiki page omits
        # or vice versa - see PHASE0_REPORT.md for every non-match).
        match = bool(wiki_lastnames) and bool(sched_lastnames) and wiki_lastnames.issubset(sched_lastnames)

        rows.append({
            "season": season, "franchise": franchise,
            "wiki_head_coach": wiki_hc,
            "schedule_head_coaches": sched_summary,
            "match": match,
        })
    return pd.DataFrame(rows)


def main():
    staff_path = STUDY / "data" / "processed" / "staff_phase0.csv"
    out_path = STUDY / "data" / "processed" / "staff_phase0_headcoach_check.csv"
    df = build_check(staff_path)
    df.to_csv(out_path, index=False)
    n_match = df["match"].sum()
    print(f"wrote {out_path}: {n_match} of {len(df)} matched")


if __name__ == "__main__":
    main()
