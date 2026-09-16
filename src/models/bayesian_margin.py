"""
Bayesian hierarchical margin model: (blowout-capped) margin ~
Normal(r_home - r_away + home_adv, sigma^2), with team ratings
r_k ~ Normal(0, tau^2) shrinking every team toward the league mean and
home_adv left unregularized (flat prior). This is a Gaussian-Gaussian
conjugate model, so the posterior mean is exactly ridge regression and the
posterior covariance is available in closed form - the "uncertainty for
free" that BUILD_PLAN section 5 names as this family's advantage over
Massey and Bradley-Terry, and the reason it is the preferred candidate if
it validates.

tau^2 (equivalently the ridge penalty alpha = sigma^2 / tau^2) is chosen
by empirical Bayes: grid search minimizing leave-one-out squared error,
computed in closed form from the ridge hat matrix (the standard
generalized-cross-validation trick) rather than by literally refitting
the model once per held-out game.

Unlike Massey, no explicit zero-sum constraint row is needed: for any
alpha > 0 the ridge penalty on the team columns alone makes X^T X + Lambda
invertible (the shared-shift null vector of X becomes an eigenvector of
Lambda with eigenvalue alpha), so the posterior mode is already uniquely
identified as the actual Bayesian answer, not an imposed convention.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from .common import capped_margin, design_matrix, team_index


def _ridge_fit(X: np.ndarray, y: np.ndarray, alpha: float, n_teams: int):
    penalty = np.zeros(X.shape[1])
    penalty[:n_teams] = alpha
    A = X.T @ X + np.diag(penalty)
    # pinv (not inv): the home-field column is only regularized by data, so
    # a slate with no on-site games at all (e.g. an all-neutral synthetic
    # test) leaves A exactly singular in that direction. pinv falls back to
    # the minimum-norm solution there, matching lstsq's behavior in massey.py,
    # instead of raising.
    A_inv = np.linalg.pinv(A)
    beta = A_inv @ (X.T @ y)
    h_diag = np.einsum("ij,jk,ik->i", X, A_inv, X)
    return beta, A_inv, h_diag


def _loo_sse(X: np.ndarray, y: np.ndarray, alpha: float, n_teams: int) -> float:
    beta, _, h_diag = _ridge_fit(X, y, alpha, n_teams)
    resid = y - X @ beta
    h_diag = np.clip(h_diag, 0, 1 - 1e-6)
    return float(np.sum((resid / (1 - h_diag)) ** 2))


def fit_bayesian_margin(g: pd.DataFrame, alpha_grid=None) -> dict:
    """Fit the hierarchical margin model for one season's games.

    Returns a dict with:
      ratings: pd.Series of posterior mean team ratings, points scale.
      ratings_se: pd.Series of posterior standard deviations (same order).
      home_adv, sigma (residual sd), tau (prior sd across teams), alpha
      (the selected ridge penalty sigma^2/tau^2).
    """
    idx = team_index(g)
    n_teams = len(idx)
    X = design_matrix(g, idx)
    y = capped_margin(g["margin"].to_numpy())

    if alpha_grid is None:
        alpha_grid = np.logspace(-2, 3, 40)

    # Coarse grid to bracket the minimum, then a bounded 1-D search on
    # log(alpha) between the bracketing grid points. The grid alone
    # quantized alpha to ~34% steps (only 7 distinct values across 56
    # seasons in the first Phase 2 run), which quantized tau and every
    # reported standard error with it.
    sse = [_loo_sse(X, y, a, n_teams) for a in alpha_grid]
    i = int(np.argmin(sse))
    lo = alpha_grid[max(i - 1, 0)]
    hi = alpha_grid[min(i + 1, len(alpha_grid) - 1)]
    if hi > lo:
        res = minimize_scalar(
            lambda log_a: _loo_sse(X, y, float(np.exp(log_a)), n_teams),
            bounds=(np.log(lo), np.log(hi)),
            method="bounded",
        )
        best_alpha = float(np.exp(res.x))
    else:
        best_alpha = float(alpha_grid[i])

    beta, A_inv, h_diag = _ridge_fit(X, y, best_alpha, n_teams)
    resid = y - X @ beta
    eff_df = float(np.sum(h_diag))
    dof = max(len(y) - eff_df, 1.0)
    sigma2 = float(np.sum(resid**2) / dof)
    tau2 = sigma2 / best_alpha if best_alpha > 0 else float("inf")

    se = np.sqrt(np.clip(np.diag(sigma2 * A_inv), 0, None))

    ratings = pd.Series(beta[:n_teams], index=list(idx.keys()))
    ratings_se = pd.Series(se[:n_teams], index=list(idx.keys()))

    return {
        "ratings": ratings.sort_values(ascending=False),
        "ratings_se": ratings_se.loc[ratings.sort_values(ascending=False).index],
        "home_adv": float(beta[n_teams]),
        "sigma": float(np.sqrt(sigma2)),
        "tau": float(np.sqrt(tau2)) if np.isfinite(tau2) else float("inf"),
        "alpha": best_alpha,
    }


def predict(g: pd.DataFrame, ratings: pd.Series, home_adv: float) -> np.ndarray:
    home_r = g["home_franchise"].map(ratings).to_numpy()
    away_r = g["away_franchise"].map(ratings).to_numpy()
    hf = np.where(g["neutral_site"].to_numpy(), 0.0, home_adv)
    return home_r - away_r + hf
