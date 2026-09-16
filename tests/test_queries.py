import pandas as pd
import pytest

from queries import best_decade, greatest_champions, largest_mismatches, weakest_champions

PROFILE = pd.DataFrame(
    [
        {"season": 1985, "franchise": "CHI", "bayes_rating_z": 2.8, "won_super_bowl": True, "reached_super_bowl": True},
        {"season": 1985, "franchise": "NE", "bayes_rating_z": -0.5, "won_super_bowl": False, "reached_super_bowl": True},
        {"season": 2000, "franchise": "BAL", "bayes_rating_z": 1.9, "won_super_bowl": True, "reached_super_bowl": True},
        {"season": 2000, "franchise": "NYG", "bayes_rating_z": 0.1, "won_super_bowl": False, "reached_super_bowl": True},
        {"season": 2011, "franchise": "NYG", "bayes_rating_z": 0.8, "won_super_bowl": True, "reached_super_bowl": True},
        {"season": 2011, "franchise": "NE", "bayes_rating_z": 1.5, "won_super_bowl": False, "reached_super_bowl": True},
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
