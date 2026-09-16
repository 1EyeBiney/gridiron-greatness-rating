import pandas as pd
import pytest

from queries import (
    best_decade,
    greatest_champions,
    greatest_conference_imbalance,
    largest_mismatches,
    records_that_most_overstated_strength,
    weakest_champions,
)

PROFILE = pd.DataFrame(
    [
        {"season": 1985, "franchise": "CHI", "bayes_rating_z": 2.8, "won_super_bowl": True, "reached_super_bowl": True, "conference": "NFC", "acc": 27.0},
        {"season": 1985, "franchise": "NE", "bayes_rating_z": -0.5, "won_super_bowl": False, "reached_super_bowl": True, "conference": "AFC", "acc": 15.0},
        {"season": 2000, "franchise": "BAL", "bayes_rating_z": 1.9, "won_super_bowl": True, "reached_super_bowl": True, "conference": "AFC", "acc": 24.5},
        {"season": 2000, "franchise": "NYG", "bayes_rating_z": 0.1, "won_super_bowl": False, "reached_super_bowl": True, "conference": "NFC", "acc": 12.0},
        {"season": 2011, "franchise": "NYG", "bayes_rating_z": 0.8, "won_super_bowl": True, "reached_super_bowl": True, "conference": "NFC", "acc": 24.6},
        {"season": 2011, "franchise": "NE", "bayes_rating_z": 1.5, "won_super_bowl": False, "reached_super_bowl": True, "conference": "AFC", "acc": 20.0},
    ]
)

GAMES = pd.DataFrame(
    [
        {"season": 1985, "date": "1986-01-26", "game_type": "SB", "home_franchise": "CHI", "away_franchise": "NE", "home_score": 46, "away_score": 10, "margin": 36},
        {"season": 2000, "date": "2001-01-28", "game_type": "SB", "home_franchise": "NYG", "away_franchise": "BAL", "home_score": 7, "away_score": 34, "margin": -27},
        {"season": 2011, "date": "2012-02-05", "game_type": "SB", "home_franchise": "NYG", "away_franchise": "NE", "home_score": 21, "away_score": 17, "margin": 4},
    ]
)


def test_greatest_and_weakest_champions_are_opposite_ends():
    top = greatest_champions(PROFILE)
    bottom = weakest_champions(PROFILE)
    assert top.iloc[0]["franchise"] == "CHI"  # highest z among winners (2.8)
    assert bottom.iloc[0]["franchise"] == "NYG" and bottom.iloc[0]["season"] == 2011  # lowest z among winners (0.8)


def test_largest_mismatch_is_the_biggest_z_gap_regardless_of_who_won():
    result = largest_mismatches(PROFILE, GAMES)
    # 1985 CHI (2.8) vs NE (-0.5): gap 3.3, the largest of the three.
    top = result.iloc[0]
    assert top["season"] == 1985
    assert top["z_gap"] == pytest.approx(3.3)
    assert not top["upset"]


def test_upset_flagged_when_the_less_strong_team_won():
    result = largest_mismatches(PROFILE, GAMES)
    row_2011 = result[result["season"] == 2011].iloc[0]
    # 2011 NYG (0.8) beat NE (1.5) - NYG was the weaker team by TSR.
    assert row_2011["upset"]


def test_best_decade_uses_top_teams_not_full_season_average():
    result = best_decade(PROFILE)
    decades = dict(zip(result["decade"], result["mean_top10_tsr_z"]))
    assert "1980s" in decades and "2000s" in decades and "2010s" in decades
    # 1980s here only has CHI (2.8) and NE (-0.5); top10 = both -> mean = 1.15
    assert decades["1980s"] == pytest.approx((2.8 - 0.5) / 2)


def test_best_decade_counts_elite_and_weak_seasons():
    result = best_decade(PROFILE).set_index("decade")
    # 1980s: CHI (2.8) is elite (>=1.0), NE (-0.5) is neither elite nor weak (<=-1.0).
    assert result.loc["1980s", "n_elite_seasons"] == 1
    assert result.loc["1980s", "n_weak_seasons"] == 0
    assert "CHI" in result.loc["1980s", "top3_team_seasons"]


def test_largest_mismatches_carries_full_profile_for_both_sides():
    result = largest_mismatches(PROFILE, GAMES)
    top = result.iloc[0]  # 1985: CHI won, NE lost
    assert top["winner_acc"] == pytest.approx(27.0)
    assert top["loser_acc"] == pytest.approx(15.0)


def test_greatest_conference_imbalance_names_the_best_team_per_conference():
    csi = pd.DataFrame([{"season": 1985, "csi": -2.0, "ci95_lower": -4.0, "ci95_upper": 0.0}])
    result = greatest_conference_imbalance(csi, PROFILE)
    row = result.iloc[0]
    assert row["stronger_conference"] == "NFC"
    assert "CHI" in row["best_nfc"]
    assert "NE" in row["best_afc"]


def test_records_that_most_overstated_strength_is_enriched_with_full_profile():
    games = pd.DataFrame(
        [
            {"season": 2000, "game_type": "REG", "home_franchise": "BAL", "away_franchise": "NYG", "home_score": 20, "away_score": 17, "margin": 3},
            {"season": 2000, "game_type": "REG", "home_franchise": "NYG", "away_franchise": "BAL", "home_score": 10, "away_score": 30, "margin": -20},
        ]
    )
    result = records_that_most_overstated_strength(PROFILE, games)
    assert "acc" in result.columns
    assert "conference" in result.columns
