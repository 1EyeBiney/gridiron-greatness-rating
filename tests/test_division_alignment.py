import pytest

from division_alignment import build_team_season_conference_table, division_for
from models.common import load_games


@pytest.mark.parametrize(
    "season,franchise,expected",
    [
        (1970, "IND", ("AFC", "East")),  # Baltimore Colts, one of the three 1970 switchers
        (1970, "TEN", ("AFC", "Central")),  # Houston Oilers
        (1976, "SEA", ("NFC", "West")),  # inaugural-season placement
        (1976, "TB", ("AFC", "West")),  # inaugural-season placement
        (1977, "SEA", ("AFC", "West")),  # post-swap
        (1977, "TB", ("NFC", "Central")),  # post-swap
        (1994, "SEA", ("AFC", "West")),  # stable through 2001
        (1995, "CAR", ("NFC", "West")),  # 1995 expansion
        (1995, "JAX", ("AFC", "Central")),  # 1995 expansion
        (1996, "BAL", ("AFC", "Central")),  # new Ravens franchise
        (1998, "CLE", None),  # Browns inactive 1996-1998
        (1999, "CLE", ("AFC", "Central")),  # Browns reactivated
        (2001, "ARI", ("NFC", "East")),  # pre-2002 realignment
        (2002, "ARI", ("NFC", "West")),  # 2002 realignment
        (2001, "IND", ("AFC", "East")),
        (2002, "IND", ("AFC", "South")),  # 2002 realignment
        (2002, "HOU", ("AFC", "South")),  # Texans expansion
        (2025, "SEA", ("NFC", "West")),
    ],
)
def test_division_for_known_milestones(season, franchise, expected):
    assert division_for(season, franchise) == expected


def test_every_team_season_in_games_resolves_and_counts_match_known_team_counts():
    games = load_games()
    table = build_team_season_conference_table(games)  # raises on any unresolved team-season
    counts = table.groupby("season").size()
    assert counts[1970] == 26
    assert counts[1976] == 28
    assert counts[1995] == 30
    assert counts[1999] == 31
    assert counts[2002] == 32
    assert counts[2025] == 32


def test_every_division_in_realigned_era_has_exactly_four_teams():
    games = load_games()
    table = build_team_season_conference_table(games)
    sizes = table[table["season"] == 2010].groupby(["conference", "division"]).size()
    assert (sizes == 4).all()
    assert len(sizes) == 8
