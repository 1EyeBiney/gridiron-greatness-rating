"""
Phase 1 data quality audit for data/processed/games.csv.

Checks:
  1. Teams per season vs. known NFL franchise-count history.
  2. Regular-season games per team per season vs. known schedule-length
     history (flagging the 1982 and 1987 strike seasons as expected
     exceptions rather than errors).
  3. Score sanity: no negative or missing scores, no implausible margins.
  4. Duplicate game detection.
  5. Playoff game count per season vs. known playoff-format history.

Writes a plain-text report to docs/PHASE1_DATA_QUALITY_REPORT.md.
"""
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
games = pd.read_csv(REPO / "data" / "processed" / "games.csv")

lines = []


def log(s=""):
    lines.append(s)
    print(s)


log("# Phase 1 Data Quality Report")
log()
log(f"Total games: {len(games)}")
log(f"Season range: {games['season'].min()}-{games['season'].max()}")
log()

# ---------------------------------------------------------------
# 1. Teams per season vs. known franchise-count history
# ---------------------------------------------------------------
log("## 1. Teams per season")
log()
expected_team_counts = {
    1970: 26, 1976: 28, 1995: 30, 1999: 31, 2002: 32,
}


def expected_teams(season):
    val = 26
    for yr, n in sorted(expected_team_counts.items()):
        if season >= yr:
            val = n
    return val


team_counts_by_season = {}
for season, grp in games.groupby("season"):
    teams = set(grp["home_franchise"]).union(set(grp["away_franchise"]))
    team_counts_by_season[season] = len(teams)

mismatches = []
for season in sorted(team_counts_by_season):
    actual = team_counts_by_season[season]
    expected = expected_teams(season)
    if actual != expected:
        mismatches.append((season, actual, expected))

if mismatches:
    log(f"MISMATCHES found ({len(mismatches)} seasons) - actual team count vs. expected:")
    for season, actual, expected in mismatches:
        log(f"  {season}: actual={actual} expected={expected}")
else:
    log("All 56 seasons (1970-2025) have the expected team count for their era. PASS.")
log()

# ---------------------------------------------------------------
# 2. Regular-season games per team per season
# ---------------------------------------------------------------
log("## 2. Regular-season games per team per season")
log()


def expected_reg_games(season):
    if season == 1982:
        return 9
    if season == 1987:
        return 15
    if season <= 1977:
        return 14
    if season <= 2020:
        return 16
    return 17


reg = games[games["game_type"] == "REG"]
reg_counts = pd.concat([
    reg[["season", "home_franchise"]].rename(columns={"home_franchise": "team"}),
    reg[["season", "away_franchise"]].rename(columns={"away_franchise": "team"}),
]).groupby(["season", "team"]).size().reset_index(name="games")

reg_counts["expected"] = reg_counts["season"].apply(expected_reg_games)
bad = reg_counts[reg_counts["games"] != reg_counts["expected"]]

# 2022 BUF/CIN: their Week 17 game was permanently cancelled after Damar
# Hamlin's on-field cardiac arrest (2023-01-02); the NFL ruled it would not
# be made up, so both teams legitimately finished with 16 regular-season
# games that year. This is a known historical fact, not a data error.
known_strike_seasons = {1982, 1987}
known_exceptions = {(2022, "BUF"), (2022, "CIN")}
unexpected_bad = bad[
    ~bad["season"].isin(known_strike_seasons)
    & ~bad.apply(lambda r: (r["season"], r["team"]) in known_exceptions, axis=1)
]

log(f"Team-seasons checked: {len(reg_counts)}")
log(f"Team-seasons matching expected schedule length: {len(reg_counts) - len(bad)}")
if len(bad):
    log(f"Team-seasons NOT matching (including known strike-year and known-event exceptions): {len(bad)}")
    log("Breakdown by season:")
    for season, grp in bad.groupby("season"):
        if season in known_strike_seasons:
            note = " (known strike season - expected)"
        elif all((season, t) in known_exceptions for t in grp["team"]):
            note = " (BUF/CIN Week 17 game cancelled after Damar Hamlin's on-field cardiac arrest, never made up - expected)"
        else:
            note = " *** UNEXPECTED ***"
        log(f"  {season}: {len(grp)} team(s) off from expected count{note}")
if len(unexpected_bad):
    log()
    log("Detail on UNEXPECTED mismatches (not 1982/1987):")
    log(unexpected_bad.to_string(index=False))
else:
    log()
    log("No unexpected schedule-length mismatches outside the 1982 and 1987 strike seasons. PASS.")
log()

# ---------------------------------------------------------------
# 3. Score sanity
# ---------------------------------------------------------------
log("## 3. Score sanity checks")
log()
neg = games[(games["home_score"] < 0) | (games["away_score"] < 0)]
missing = games[games["home_score"].isna() | games["away_score"].isna()]
huge_margin = games[games["margin"].abs() > 55]
log(f"Negative scores: {len(neg)}")
log(f"Missing scores: {len(missing)}")
log(f"Games with |margin| > 55 (extreme, not necessarily wrong - listed for manual spot check): {len(huge_margin)}")
if len(huge_margin):
    log(huge_margin[["season", "date", "home_franchise", "away_franchise", "home_score", "away_score"]].to_string(index=False))
log()

# ---------------------------------------------------------------
# 4. Duplicate detection
# ---------------------------------------------------------------
log("## 4. Duplicate game detection")
log()
dupe_key = ["season", "date", "home_franchise", "away_franchise", "home_score", "away_score"]
dupes = games[games.duplicated(subset=dupe_key, keep=False)]
log(f"Exact duplicate rows (same season/date/teams/scores): {len(dupes)}")
if len(dupes):
    log(dupes.to_string(index=False))
else:
    log("PASS - no duplicates found.")
log()

# ---------------------------------------------------------------
# 5. Playoff game counts per season vs. known playoff-format history
# ---------------------------------------------------------------
log("## 5. Playoff bracket reconciliation")
log()


def expected_playoff_games(season):
    if season == 1982:
        return 15  # strike-year 16-team single-elimination tournament
    if season <= 1977:
        return 7  # no wild-card round: divisional (4) + conf champ (2) + SB (1)
    if season <= 1989:
        return 9  # WC(2) + DIV(4) + CON(2) + SB(1)
    if season <= 2019:
        return 11  # WC(4) + DIV(4) + CON(2) + SB(1)
    return 13  # 2020+: WC(6) + DIV(4) + CON(2) + SB(1)


playoff = games[games["game_type"] != "REG"]
playoff_counts = playoff.groupby("season").size()

po_mismatches = []
for season in range(1970, games["season"].max() + 1):
    actual = int(playoff_counts.get(season, 0))
    expected = expected_playoff_games(season)
    if actual != expected:
        po_mismatches.append((season, actual, expected))

if po_mismatches:
    log(f"Seasons where playoff game count differs from expected ({len(po_mismatches)}):")
    for season, actual, expected in po_mismatches:
        log(f"  {season}: actual={actual} expected={expected}")
    log()
    log("NOTE: this check uses playoff-format history recalled from general knowledge and has")
    log("NOT been individually verified season by season against a primary source. Any")
    log("mismatch above should be checked against Wikipedia's per-season NFL playoffs page")
    log("or Pro Football Reference before being treated as a data error.")
else:
    log("All seasons match expected playoff game counts for their era. PASS.")
    log()
    log("CAVEAT: the expected-count table itself was recalled from general knowledge, not")
    log("verified season-by-season against a primary source. Treat this check as a first")
    log("pass, not a certification.")
log()

log("## Known open items (not fixed by this audit)")
log()
log("- Pre-1999 playoff games (FiveThirtyEight source) carry only a binary playoff flag,")
log("  not a round label (Wild Card / Divisional / Conference / Super Bowl). Round detail")
log("  needs a dedicated follow-up pass, e.g. reconstructing rounds from each season's")
log("  known bracket size and game dates, cross-checked against Wikipedia per-season")
log("  playoff articles.")
log("- No week number for 1970-1998 games (FiveThirtyEight has date only, no week field).")
log("- No team-season conference/division table yet (needed for Phase 5 Conference")
log("  Strength Index and for a more precise div_game check pre-1999).")

report_path = REPO / "docs" / "PHASE1_DATA_QUALITY_REPORT.md"
report_path.write_text("\n".join(lines) + "\n")
print(f"\nReport written to {report_path}")
