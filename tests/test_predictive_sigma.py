import pandas as pd

from models.bayesian_margin import fit_bayesian_margin
from models.common import is_schedule_connected, predictive_sigma


def test_disconnected_pairs_are_not_connected():
    g = pd.DataFrame(
        [
            {"home_franchise": "A", "away_franchise": "B", "margin": 8.0, "neutral_site": True},
            {"home_franchise": "C", "away_franchise": "D", "margin": 8.0, "neutral_site": True},
        ]
    )
    assert not is_schedule_connected(g)


def test_a_chain_of_shared_opponents_is_connected():
    g = pd.DataFrame(
        [
            {"home_franchise": "A", "away_franchise": "B", "margin": 8.0, "neutral_site": True},
            {"home_franchise": "B", "away_franchise": "C", "margin": 3.0, "neutral_site": True},
            {"home_franchise": "C", "away_franchise": "D", "margin": -2.0, "neutral_site": True},
        ]
    )
    assert is_schedule_connected(g)


def test_predictive_sigma_is_wider_for_a_disconnected_matchup():
    """A and C never played and share no opponent in this training set,
    so predicting A vs C should carry more uncertainty than predicting
    A vs B, a pairing the training data actually informs directly. This
    is the Bayesian model specifically: its ridge regularization keeps
    the fit well-posed and correctly widens predictive_sigma for a
    matchup the data says nothing about. Plain Massey does the opposite
    here (see docs/PHASE4_WALKFORWARD_VALIDATION.md) - its minimum-norm
    solution reports *zero* extra uncertainty for exactly this matchup,
    which is the structural finding that report documents, not a bug this
    test should expect fixed in Massey."""
    train = pd.DataFrame(
        [
            {"home_franchise": "A", "away_franchise": "B", "margin": 8.0, "neutral_site": True},
            {"home_franchise": "C", "away_franchise": "D", "margin": 8.0, "neutral_site": True},
        ]
    )
    fit = fit_bayesian_margin(train)
    a_vs_b = pd.DataFrame([{"home_franchise": "A", "away_franchise": "B", "neutral_site": True}])
    a_vs_c = pd.DataFrame([{"home_franchise": "A", "away_franchise": "C", "neutral_site": True}])
    sigma_ab = predictive_sigma(a_vs_b, fit["team_index"], fit["beta_cov_unscaled"], fit["sigma"])[0]
    sigma_ac = predictive_sigma(a_vs_c, fit["team_index"], fit["beta_cov_unscaled"], fit["sigma"])[0]
    assert sigma_ac > sigma_ab
