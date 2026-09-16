"""
Team-season conference/division table - the item carried forward from
Phase 1 ("no team-season conference/division table yet") and needed by
Phase 5 for both the Conference Strength Index and the Accomplishment
score's division-title component.

Division alignment changed six times in this project's 1970-2025 window,
each verified against multiple independent sources (Wikipedia, Pro
Football Hall of Fame, team history pages) via web search rather than
taken from memory alone, given how easy it would be to get a detail
wrong across 56 seasons of realignment:

1970-1975 (26 teams): the merger alignment. Three "old NFL" teams (the
  Baltimore Colts [franchise_id IND], Cleveland Browns [CLE], and
  Pittsburgh Steelers [PIT]) joined the ten AFL teams to balance the
  conferences at 13 each.
1976 (28 teams, one season only): expansion Tampa Bay and Seattle were
  placed apart (TB in the AFC, SEA in the NFC) specifically so each new
  team's inaugural schedule touched every existing franchise once.
1977-1994 (28 teams): TB and SEA swap conferences to their geographically
  sensible homes (TB to NFC Central, SEA to AFC West) and stay there
  until 2002.
1995 (30 teams): expansion Carolina (NFC West) and Jacksonville
  (AFC Central) fill the two divisions that had only four teams.
1996-1998 (30 teams): Cleveland's original Browns franchise is inactive
  (see data/reference/franchise_crosswalk_README.md); the new Baltimore
  Ravens [BAL] occupy the Browns' old AFC Central slot.
1999-2001 (31 teams): the reactivated Cleveland Browns [CLE] rejoin the
  AFC Central alongside Baltimore, Cincinnati, Jacksonville, Pittsburgh,
  and Tennessee.
2002-2025 (32 teams): full realignment from three divisions per
  conference (a 5+4+4 / 5+4+4 split) to four divisions of four
  (East/North/South/West in both conferences), driven by expansion
  Houston [HOU] filling the 32nd slot. This moved several existing teams,
  not just the new team - notably Seattle to the NFC, Arizona to the NFC
  West, and Indianapolis to the AFC South.

Sources consulted: en.wikipedia.org/wiki/{1970,2002}_NFL_season,
profootballhof.com's 1976 expansion retrospective, and team history pages
for the 1976/1977 Tampa Bay-Seattle swap, 1995 expansion, and the 1996-99
Browns/Ravens split - cross-checked against each other, not relied on
individually.
"""
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]

_AFC_EAST_CORE = {"IND": "Baltimore/Indianapolis Colts", "NE": "New England Patriots", "BUF": "Buffalo Bills", "MIA": "Miami Dolphins", "NYJ": "New York Jets"}
_AFC_CENTRAL_CORE = {"CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "TEN": "Houston Oilers/Tennessee Titans", "PIT": "Pittsburgh Steelers"}
_AFC_WEST_CORE = {"DEN": "Denver Broncos", "KC": "Kansas City Chiefs", "OAK": "Oakland/LA/Las Vegas Raiders", "LAC": "San Diego/LA Chargers"}
_NFC_EAST_CORE = {"DAL": "Dallas Cowboys", "NYG": "New York Giants", "PHI": "Philadelphia Eagles", "ARI": "St. Louis/Arizona Cardinals", "WSH": "Washington"}
_NFC_CENTRAL_CORE = {"CHI": "Chicago Bears", "DET": "Detroit Lions", "GB": "Green Bay Packers", "MIN": "Minnesota Vikings"}
_NFC_WEST_CORE = {"ATL": "Atlanta Falcons", "LAR": "LA/St. Louis/LA Rams", "NO": "New Orleans Saints", "SF": "San Francisco 49ers"}

# Each entry: (first_season, last_season_inclusive_or_None, {franchise_id: (conference, division)})
_ERAS = []


def _era(teams_by_slot: dict) -> dict:
    out = {}
    for (conf, div), teams in teams_by_slot.items():
        for t in teams:
            out[t] = (conf, div)
    return out


_ERAS.append(
    (
        1970,
        1975,
        _era(
            {
                ("AFC", "East"): _AFC_EAST_CORE,
                ("AFC", "Central"): _AFC_CENTRAL_CORE,
                ("AFC", "West"): _AFC_WEST_CORE,
                ("NFC", "East"): _NFC_EAST_CORE,
                ("NFC", "Central"): _NFC_CENTRAL_CORE,
                ("NFC", "West"): _NFC_WEST_CORE,
            }
        ),
    )
)

_ERAS.append(
    (
        1976,
        1976,
        _era(
            {
                ("AFC", "East"): _AFC_EAST_CORE,
                ("AFC", "Central"): _AFC_CENTRAL_CORE,
                ("AFC", "West"): {**_AFC_WEST_CORE, "TB": "Tampa Bay Buccaneers (inaugural season only)"},
                ("NFC", "East"): _NFC_EAST_CORE,
                ("NFC", "Central"): _NFC_CENTRAL_CORE,
                ("NFC", "West"): {**_NFC_WEST_CORE, "SEA": "Seattle Seahawks (inaugural season only)"},
            }
        ),
    )
)

_ERAS.append(
    (
        1977,
        1994,
        _era(
            {
                ("AFC", "East"): _AFC_EAST_CORE,
                ("AFC", "Central"): _AFC_CENTRAL_CORE,
                ("AFC", "West"): {**_AFC_WEST_CORE, "SEA": "Seattle Seahawks"},
                ("NFC", "East"): _NFC_EAST_CORE,
                ("NFC", "Central"): {**_NFC_CENTRAL_CORE, "TB": "Tampa Bay Buccaneers"},
                ("NFC", "West"): _NFC_WEST_CORE,
            }
        ),
    )
)

_ERAS.append(
    (
        1995,
        1995,
        _era(
            {
                ("AFC", "East"): _AFC_EAST_CORE,
                ("AFC", "Central"): {**_AFC_CENTRAL_CORE, "JAX": "Jacksonville Jaguars (expansion)"},
                ("AFC", "West"): {**_AFC_WEST_CORE, "SEA": "Seattle Seahawks"},
                ("NFC", "East"): _NFC_EAST_CORE,
                ("NFC", "Central"): {**_NFC_CENTRAL_CORE, "TB": "Tampa Bay Buccaneers"},
                ("NFC", "West"): {**_NFC_WEST_CORE, "CAR": "Carolina Panthers (expansion)"},
            }
        ),
    )
)

_ERAS.append(
    (
        1996,
        1998,
        _era(
            {
                ("AFC", "East"): _AFC_EAST_CORE,
                # CLE inactive 1996-1998; BAL (Ravens, new franchise) takes the slot.
                ("AFC", "Central"): {k: v for k, v in _AFC_CENTRAL_CORE.items() if k != "CLE"} | {"BAL": "Baltimore Ravens", "JAX": "Jacksonville Jaguars"},
                ("AFC", "West"): {**_AFC_WEST_CORE, "SEA": "Seattle Seahawks"},
                ("NFC", "East"): _NFC_EAST_CORE,
                ("NFC", "Central"): {**_NFC_CENTRAL_CORE, "TB": "Tampa Bay Buccaneers"},
                ("NFC", "West"): {**_NFC_WEST_CORE, "CAR": "Carolina Panthers"},
            }
        ),
    )
)

_ERAS.append(
    (
        1999,
        2001,
        _era(
            {
                ("AFC", "East"): _AFC_EAST_CORE,
                ("AFC", "Central"): {**_AFC_CENTRAL_CORE, "BAL": "Baltimore Ravens", "JAX": "Jacksonville Jaguars"},
                ("AFC", "West"): {**_AFC_WEST_CORE, "SEA": "Seattle Seahawks"},
                ("NFC", "East"): _NFC_EAST_CORE,
                ("NFC", "Central"): {**_NFC_CENTRAL_CORE, "TB": "Tampa Bay Buccaneers"},
                ("NFC", "West"): {**_NFC_WEST_CORE, "CAR": "Carolina Panthers"},
            }
        ),
    )
)

_ERAS.append(
    (
        2002,
        None,
        _era(
            {
                ("AFC", "East"): {"BUF": "Buffalo Bills", "MIA": "Miami Dolphins", "NE": "New England Patriots", "NYJ": "New York Jets"},
                ("AFC", "North"): {"BAL": "Baltimore Ravens", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "PIT": "Pittsburgh Steelers"},
                ("AFC", "South"): {"HOU": "Houston Texans (expansion)", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "TEN": "Tennessee Titans"},
                ("AFC", "West"): {"DEN": "Denver Broncos", "KC": "Kansas City Chiefs", "OAK": "Oakland/LV Raiders", "LAC": "San Diego/LA Chargers"},
                ("NFC", "East"): {"DAL": "Dallas Cowboys", "NYG": "New York Giants", "PHI": "Philadelphia Eagles", "WSH": "Washington"},
                ("NFC", "North"): {"CHI": "Chicago Bears", "DET": "Detroit Lions", "GB": "Green Bay Packers", "MIN": "Minnesota Vikings"},
                ("NFC", "South"): {"ATL": "Atlanta Falcons", "CAR": "Carolina Panthers", "NO": "New Orleans Saints", "TB": "Tampa Bay Buccaneers"},
                ("NFC", "West"): {"ARI": "Arizona Cardinals", "LAR": "St. Louis/LA Rams", "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks"},
            }
        ),
    )
)


def division_for(season: int, franchise_id: str):
    for start, end, mapping in _ERAS:
        if season >= start and (end is None or season <= end):
            if franchise_id in mapping:
                return mapping[franchise_id]
            return None
    return None


def build_team_season_conference_table(games: pd.DataFrame) -> pd.DataFrame:
    """One row per team-season actually present in the game log, with
    its conference and division. Raises if any team-season can't be
    resolved, rather than silently dropping it - a gap here would mean
    an era boundary above is wrong."""
    rows = []
    missing = []
    for season, g in games.groupby("season"):
        teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
        for team in teams:
            result = division_for(int(season), team)
            if result is None:
                missing.append((int(season), team))
                continue
            conf, div = result
            rows.append({"season": int(season), "franchise": team, "conference": conf, "division": div})

    if missing:
        raise ValueError(f"No division mapping for {len(missing)} team-seasons, e.g. {missing[:10]}")

    return pd.DataFrame(rows).sort_values(["season", "conference", "division", "franchise"]).reset_index(drop=True)


if __name__ == "__main__":
    from models.common import load_games

    table = build_team_season_conference_table(load_games())
    out_path = REPO / "data" / "reference" / "team_season_conference.csv"
    table.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(table)} rows)")
