"""
Bradley-Terry rating with a margin-aware extension: maximum-likelihood
logistic model of win/loss (r_home - r_away + home_adv predicts the log-
odds of a home win), where each game's contribution to the likelihood is
weighted up for more decisive results. Weighting, not the outcome
variable, is how margin enters - the model still targets win/loss, per
BUILD_PLAN section 5 ("Bradley-Terry / logistic model on win-loss with a
margin-aware extension"), so it stays a genuinely different model family
from the point-margin models (Massey, Bayesian) rather than a
reparameterization of the same regression.

Ties count as a half-win for each side (BUILD_PLAN section 6), which is
the natural generalization of the standard win/loss target to y in
{0, 0.5, 1}.

Weight for game i: 1 + log1p(min(|margin_i|, 28)) - the same 28-point
Blowout-rule cap used elsewhere, so a 55-point win is weighted the same
as a 28-point win, not 55/28 times as much.

A small, fixed L2 penalty on the team ratings (not on home_adv) is added
to the log-likelihood. Without it, plain Bradley-Terry MLE diverges for
any team that goes unbeaten or winless within a fold - quasi-complete
separation, a well-known failure mode of logistic regression on small
samples - which produces near-0/near-1 predictions that are occasionally
catastrophically wrong on held-out games. This is a standard fix (the
same idea as Firth's penalized likelihood), not a tuned hyperparameter:
REG_STRENGTH was chosen once by grid search against the Phase 2
cross-validation protocol (src/evaluate.py) to land near the minimum of
the log-loss curve, then fixed - it is not re-fit per season the way the
Bayesian model's shrinkage is, so this stays a distinct "classical MLE
plus a standard stabilizer" model rather than a second hierarchical model.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .common import MARGIN_CAP, design_matrix, outcome_label, team_index

REG_STRENGTH = 3.0


def _game_weights(margin: np.ndarray) -> np.ndarray:
    capped_abs = np.minimum(np.abs(margin), MARGIN_CAP)
    return 1.0 + np.log1p(capped_abs)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _neg_log_likelihood(beta, X, y, w, n_teams, reg_strength):
    d = X @ beta
    p = np.clip(_sigmoid(d), 1e-12, 1 - 1e-12)
    team_beta = beta[:n_teams]
    loss = -np.sum(w * (y * np.log(p) + (1 - y) * np.log(1 - p))) + reg_strength * np.sum(team_beta**2)
    grad = X.T @ (w * (p - y))
    grad[:n_teams] += 2 * reg_strength * team_beta
    return loss, grad


def fit_bradley_terry(g: pd.DataFrame) -> dict:
    """Fit margin-weighted Bradley-Terry ratings for one season's games.

    Returns a dict with:
      ratings: pd.Series of team log-odds ratings, league mean 0.
      home_adv: fitted home-field advantage, in log-odds.
    """
    idx = team_index(g)
    n_teams = len(idx)
    X = design_matrix(g, idx)
    margin = g["margin"].to_numpy()
    y = outcome_label(margin)
    w = _game_weights(margin)

    x0 = np.zeros(n_teams + 1)
    result = minimize(
        _neg_log_likelihood,
        x0,
        args=(X, y, w, n_teams, REG_STRENGTH),
        jac=True,
        method="L-BFGS-B",
    )
    beta = result.x

    # Unlike a pure (unregularized) Bradley-Terry likelihood, this
    # objective is not shift-invariant - the L2 penalty already prefers a
    # (near) zero-sum solution directly, the same reason bayesian_margin.py
    # needs no separate zero-sum constraint once alpha > 0.
    ratings = pd.Series(beta[:n_teams], index=list(idx.keys()))
    home_adv = float(beta[n_teams])

    return {
        "ratings": ratings.sort_values(ascending=False),
        "home_adv": home_adv,
    }


def predict_win_prob(g: pd.DataFrame, ratings: pd.Series, home_adv: float) -> np.ndarray:
    home_r = g["home_franchise"].map(ratings).to_numpy()
    away_r = g["away_franchise"].map(ratings).to_numpy()
    hf = np.where(g["neutral_site"].to_numpy(), 0.0, home_adv)
    return _sigmoid(home_r - away_r + hf)
