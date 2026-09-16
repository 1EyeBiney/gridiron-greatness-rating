import pandas as pd
import pytest

from adversarial_audit import rating_vs_record_residuals, team_season_records


def test_team_season_records_win_pct_and_point_diff():
    games = pd.DataFrame(
        [
            {"season": 2000, "game_type": "REG", "home_franchise": "A", "away_franchise": "B", "margin": 20},
            {"season": 2000, "game_type": "REG", "home_franchise": "B", "away_franchise": "A", "margin": -3},
            {"season": 2000, "game_type": "REG", "home_franchise": "A", "away_franchise": "C", "margin": 0},
        ]
    )
    records = team_season_records(games).set_index("franchise")
    # A: won 20-0 at home, lost by 3 (won) on the road at B, tied C.
    assert records.loc["A", "wins"] == 2
    assert records.loc["A", "losses"] == 0
    assert records.loc["A", "ties"] == 1
    assert records.loc["A", "win_pct"] == pytest.approx((2 + 0.5) / 3)
    # point_diff for A: +20 (home win) + 3 (away win margin, B's home
    # margin was -3 so A won by 3) + 0 (tie) = 23
    assert records.loc["A", "point_diff"] == 23


def test_residual_flags_big_margin_few_wins_team():
    """Team X: 1 blowout win, 2 narrow losses (bad record, strong point
    diff) vs Team Y: 3 narrow wins (good record, weak point diff). X
    should show a positive rating-vs-record residual, Y negative."""
    ratings = pd.DataFrame(
        [
            {"season": 2000, "franchise": "X", "bayes_rating_z": 1.0},
            {"season": 2000, "franchise": "Y", "bayes_rating_z": -1.0},
        ]
    )
    records = pd.DataFrame(
        [
            {"season": 2000, "franchise": "X", "wins": 1, "losses": 2, "ties": 0, "win_pct": 1 / 3, "point_diff": 20, "point_diff_per_game": 20 / 3},
            {"season": 2000, "franchise": "Y", "wins": 2, "losses": 1, "ties": 0, "win_pct": 2 / 3, "point_diff": -20, "point_diff_per_game": -20 / 3},
        ]
    )
    merged = rating_vs_record_residuals(ratings, records)
    x = merged[merged["franchise"] == "X"].iloc[0]
    y = merged[merged["franchise"] == "Y"].iloc[0]
    assert x["residual"] > 0
    assert y["residual"] < 0
