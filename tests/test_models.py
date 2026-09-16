"""
Sanity tests for the Phase 2 rating models. These check known properties
on small synthetic datasets (exact recovery of a deterministic linear
system, correct rank ordering, shrinkage shrinking with more data) - they
are not a substitute for Phase 4's real-data validation, just a check
that each implementation does what its docstring claims.
"""
import numpy as np
import pandas as pd
import pytest

from models import bayesian_margin, bradley_terry, elo, massey
from models.common import capped_margin, log_loss, outcome_label


def round_robin_games(strengths: dict, rounds: int, noise_sd: float = 0.0, seed: int = 0) -> pd.DataFrame:
    """Every pair of teams plays once per round, alternating home/away by
    round parity, with margin = home_strength - away_strength (+ noise).
    Always neutral-site so home-field advantage plays no role, keeping the
    synthetic ground truth exactly the input strengths."""
    teams = list(strengths)
    rng = np.random.default_rng(seed)
    rows = []
    for rnd in range(rounds):
        for i, a in enumerate(teams):
            for b in teams[i + 1 :]:
                home, away = (a, b) if rnd % 2 == 0 else (b, a)
                margin = strengths[home] - strengths[away] + rng.normal(0, noise_sd)
                rows.append(
                    {
                        "home_franchise": home,
                        "away_franchise": away,
                        "margin": margin,
                        "neutral_site": True,
                        "home_score": 20 + margin / 2,
                        "away_score": 20 - margin / 2,
                    }
                )
    return pd.DataFrame(rows)


TRUE_STRENGTHS = {"A": 10.0, "B": 0.0, "C": -5.0, "D": -10.0}


# --- common.py -----------------------------------------------------------


def test_capped_margin_clips_at_28():
    result = capped_margin([50, -50, 10, -10, 0])
    assert list(result) == [28, -28, 10, -10, 0]


def test_outcome_label():
    labels = outcome_label(np.array([7, -3, 0]))
    assert list(labels) == [1.0, 0.0, 0.5]


def test_log_loss_confident_and_correct_beats_confident_and_wrong():
    y = np.array([1.0, 0.0])
    good = log_loss(y, np.array([0.99, 0.01]))
    bad = log_loss(y, np.array([0.01, 0.99]))
    assert good < bad


# --- Massey ----------------------------------------------------------------


def test_massey_recovers_exact_strengths_on_noiseless_data():
    g = round_robin_games(TRUE_STRENGTHS, rounds=4, noise_sd=0.0)
    fit = massey.fit_massey(g)
    ratings = fit["ratings"]

    assert ratings["A"] - ratings["B"] == pytest.approx(10.0, abs=1e-6)
    assert ratings["B"] - ratings["C"] == pytest.approx(5.0, abs=1e-6)
    assert ratings["C"] - ratings["D"] == pytest.approx(5.0, abs=1e-6)
    assert fit["home_adv"] == pytest.approx(0.0, abs=1e-6)
    assert fit["sigma"] == pytest.approx(0.0, abs=1e-6)


def test_massey_predict_matches_fit_on_training_data():
    g = round_robin_games(TRUE_STRENGTHS, rounds=4, noise_sd=0.0)
    fit = massey.fit_massey(g)
    pred = massey.predict(g, fit["ratings"], fit["home_adv"])
    np.testing.assert_allclose(pred, g["margin"].to_numpy(), atol=1e-6)


# --- Bradley-Terry -----------------------------------------------------------


def test_bradley_terry_ranks_teams_by_true_strength():
    g = round_robin_games(TRUE_STRENGTHS, rounds=6, noise_sd=0.0)
    fit = bradley_terry.fit_bradley_terry(g)
    ordered = fit["ratings"].sort_values(ascending=False).index.tolist()
    assert ordered == ["A", "B", "C", "D"]


def test_bradley_terry_win_prob_favors_stronger_team():
    g = round_robin_games(TRUE_STRENGTHS, rounds=6, noise_sd=0.0)
    fit = bradley_terry.fit_bradley_terry(g)
    matchup = pd.DataFrame(
        [{"home_franchise": "A", "away_franchise": "D", "neutral_site": True}]
    )
    p = bradley_terry.predict_win_prob(matchup, fit["ratings"], fit["home_adv"])[0]
    assert p > 0.5


# --- Bayesian hierarchical margin --------------------------------------------


def test_bayesian_shrinks_more_with_less_data():
    small = round_robin_games(TRUE_STRENGTHS, rounds=1, noise_sd=5.0, seed=1)
    large = round_robin_games(TRUE_STRENGTHS, rounds=20, noise_sd=5.0, seed=1)

    fit_small = bayesian_margin.fit_bayesian_margin(small)
    fit_large = bayesian_margin.fit_bayesian_margin(large)

    assert fit_large["ratings_se"].mean() < fit_small["ratings_se"].mean()


def test_bayesian_converges_toward_massey_with_lots_of_data():
    g = round_robin_games(TRUE_STRENGTHS, rounds=40, noise_sd=1.0, seed=2)
    bayes = bayesian_margin.fit_bayesian_margin(g)
    ols = massey.fit_massey(g)

    diff = (bayes["ratings"] - ols["ratings"]).abs().max()
    assert diff < 1.0


# --- Elo -----------------------------------------------------------------


def test_elo_equal_ratings_neutral_site_is_toss_up():
    g = pd.DataFrame(
        [{"home_franchise": "A", "away_franchise": "B", "margin": 7, "neutral_site": True}]
    )
    processed = elo.run_elo(g)
    assert processed["p_home_win"].iloc[0] == pytest.approx(0.5)


def test_elo_repeated_winner_ends_above_repeated_loser():
    rows = [
        {"home_franchise": "W", "away_franchise": "L", "margin": 14, "neutral_site": True}
        for _ in range(10)
    ]
    g = pd.DataFrame(rows)
    final = elo.final_ratings(elo.run_elo(g))
    assert final["W"] > elo.START_RATING > final["L"]
