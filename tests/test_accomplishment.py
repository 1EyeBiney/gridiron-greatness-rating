import pandas as pd
import pytest

from accomplishment import compute_acc, playoff_win_counts

# A tiny two-division, two-conference league: AFC {A, B}, NFC {C, D}.
# A goes 3-0 (undefeated), wins the Super Bowl over C (from NFC).
# B goes 0-3. C goes 2-1, loses the Super Bowl. D goes 1-2.
GAMES = pd.DataFrame(
    [
        {"season": 2000, "date": "2000-09-10", "game_type": "REG", "home_franchise": "A", "away_franchise": "B", "home_score": 20, "away_score": 10, "margin": 10, "neutral_site": False},
        {"season": 2000, "date": "2000-09-17", "game_type": "REG", "home_franchise": "C", "away_franchise": "D", "home_score": 24, "away_score": 20, "margin": 4, "neutral_site": False},
        {"season": 2000, "date": "2000-09-24", "game_type": "REG", "home_franchise": "A", "away_franchise": "C", "home_score": 17, "away_score": 10, "margin": 7, "neutral_site": False},
        {"season": 2000, "date": "2000-10-01", "game_type": "REG", "home_franchise": "D", "away_franchise": "C", "home_score": 14, "away_score": 21, "margin": -7, "neutral_site": False},
        {"season": 2000, "date": "2000-10-08", "game_type": "REG", "home_franchise": "B", "away_franchise": "A", "home_score": 10, "away_score": 24, "margin": -14, "neutral_site": False},
        {"season": 2000, "date": "2000-10-15", "game_type": "REG", "home_franchise": "D", "away_franchise": "B", "home_score": 17, "away_score": 20, "margin": -3, "neutral_site": False},
        {"season": 2000, "date": "2001-01-14", "game_type": "PLAYOFF", "home_franchise": "A", "away_franchise": "D", "home_score": 28, "away_score": 7, "margin": 21, "neutral_site": False},
        {"season": 2000, "date": "2001-01-21", "game_type": "PLAYOFF", "home_franchise": "C", "away_franchise": "D", "home_score": 10, "away_score": 3, "margin": 7, "neutral_site": False},
        {"season": 2000, "date": "2001-02-04", "game_type": "SB", "home_franchise": "A", "away_franchise": "C", "home_score": 31, "away_score": 14, "margin": 17, "neutral_site": True},
    ]
)
DIVISIONS = {"A": ("AFC", "East"), "B": ("AFC", "West"), "C": ("NFC", "East"), "D": ("NFC", "West")}


def _patch_divisions(monkeypatch):
    monkeypatch.setattr(
        "accomplishment.build_team_season_conference_table",
        lambda games: pd.DataFrame(
            [{"season": 2000, "franchise": f, "conference": c, "division": d} for f, (c, d) in DIVISIONS.items()]
        ),
    )


def test_super_bowl_winner_and_appearance_identified_correctly(monkeypatch):
    _patch_divisions(monkeypatch)
    playoff = playoff_win_counts(GAMES)
    a = playoff[playoff["franchise"] == "A"].iloc[0]
    c = playoff[playoff["franchise"] == "C"].iloc[0]
    assert a["won_super_bowl"] and a["reached_super_bowl"]
    assert c["reached_super_bowl"] and not c["won_super_bowl"]


def test_undefeated_team_gets_the_bonus_and_highest_score(monkeypatch):
    _patch_divisions(monkeypatch)
    acc = compute_acc(GAMES).set_index("franchise")
    assert acc.loc["A", "acc_undefeated"] == pytest.approx(3.0)
    assert acc.loc["A", "acc"] == acc["acc"].max()


def test_super_bowl_win_not_double_counted_as_a_playoff_win():
    playoff = playoff_win_counts(GAMES)
    a = playoff[playoff["franchise"] == "A"].iloc[0]
    # A won 2 playoff games total (beat D, then beat C in the SB).
    assert a["playoff_wins"] == 2


def test_division_and_conference_titles_go_to_the_right_teams(monkeypatch):
    _patch_divisions(monkeypatch)
    acc = compute_acc(GAMES).set_index("franchise")
    # A is alone in AFC East and 3-0 -> division title by default.
    assert acc.loc["A", "division_title"]
    # B is alone in AFC West and 0-3 -> still "wins" its (single-team) division.
    assert acc.loc["B", "division_title"]
    # A has the best overall win_pct in the AFC.
    assert acc.loc["A", "conference_best_record"]
    assert not acc.loc["B", "conference_best_record"]
