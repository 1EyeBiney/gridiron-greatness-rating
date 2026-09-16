import pandas as pd
import pytest

from team_profile import (
    dominance,
    offense_defense,
    postseason_evidence,
    record_vs_elite,
    schedule_difficulty,
)

GAMES = pd.DataFrame(
    [
        # Regular season: A beats B 30-10 at home, A beats C 20-17 on the road.
        {"season": 2000, "game_type": "REG", "home_franchise": "A", "away_franchise": "B", "home_score": 30, "away_score": 10, "margin": 20},
        {"season": 2000, "game_type": "REG", "home_franchise": "C", "away_franchise": "A", "home_score": 17, "away_score": 20, "margin": -3},
        # Postseason: A loses to B by 7.
        {"season": 2000, "game_type": "WC", "home_franchise": "B", "away_franchise": "A", "home_score": 24, "away_score": 17, "margin": 7},
    ]
)

RATINGS = pd.DataFrame(
    [
        {"season": 2000, "franchise": "A", "bayes_rating_z": 2.0},
        {"season": 2000, "franchise": "B", "bayes_rating_z": -1.0},
        {"season": 2000, "franchise": "C", "bayes_rating_z": 1.5},  # elite (>= 1.0)
    ]
)


def test_dominance_avg_margin():
    d = dominance(GAMES).set_index("franchise")
    # A: +20 (home) then, as visitor at C, margin is home_margin negated -> A's margin = +3
    assert d.loc["A", "avg_margin"] == pytest.approx((20 + 3) / 2)


def test_offense_defense_points_per_game():
    od = offense_defense(GAMES).set_index("franchise")
    assert od.loc["A", "points_for_per_game"] == pytest.approx((30 + 20) / 2)
    assert od.loc["A", "points_against_per_game"] == pytest.approx((10 + 17) / 2)


def test_schedule_difficulty_averages_opponent_z():
    sd = schedule_difficulty(GAMES, RATINGS).set_index("franchise")
    # A's regular-season opponents: B (z=-1.0), C (z=1.5)
    assert sd.loc["A", "schedule_difficulty"] == pytest.approx((-1.0 + 1.5) / 2)


def test_record_vs_elite_only_counts_elite_opponents():
    rve = record_vs_elite(GAMES, RATINGS).set_index("franchise")
    # A's only elite (z>=1.0) regular-season opponent is C, and A won that game.
    assert rve.loc["A", "elite_opponents_played"] == 1
    assert rve.loc["A", "record_vs_elite_win_pct"] == pytest.approx(1.0)


def test_postseason_evidence_excludes_regular_season():
    pe = postseason_evidence(GAMES).set_index("franchise")
    assert pe.loc["A", "playoff_games"] == 1
    assert pe.loc["A", "playoff_avg_margin"] == pytest.approx(-7.0)
