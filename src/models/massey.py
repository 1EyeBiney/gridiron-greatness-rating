"""
Massey-style least-squares rating: regress each game's (blowout-capped)
margin on a +1/-1 team design plus a shared home-field term, across every
game a team played that season (regular season and postseason). This
generalizes the Phase 1 SRS validation tool (src/srs.py) in exactly the
two ways BUILD_PLAN section 5 calls for: a fitted home-field advantage,
and margin damping (the Blowout rule).

r_home - r_away + home_adv * is_home_field = capped_margin

Solved by ordinary least squares. The team columns alone are rank-deficient
by one dimension (ratings are only identified up to a shared additive
constant), so a zero-sum constraint row pins the league-average team to 0,
matching the SRS convention.
"""
import numpy as np
import pandas as pd

from .common import (
    capped_margin,
    design_matrix,
    team_index,
    zero_sum_constraint,
)


def fit_massey(g: pd.DataFrame) -> dict:
    """Fit Massey ratings for one season's games.

    Returns a dict with:
      ratings: pd.Series of team ratings, league mean 0, higher is better.
      home_adv: fitted home-field advantage in points.
      sigma: residual standard deviation of capped margin vs. fitted value,
        used to convert a rating gap into a win probability elsewhere.
    """
    idx = team_index(g)
    n_teams = len(idx)
    X = design_matrix(g, idx)
    y = capped_margin(g["margin"].to_numpy())

    X_aug = np.vstack([X, zero_sum_constraint(n_teams)])
    y_aug = np.append(y, 0.0)

    beta, *_ = np.linalg.lstsq(X_aug, y_aug, rcond=None)
    ratings = pd.Series(beta[:n_teams], index=list(idx.keys()))
    home_adv = float(beta[n_teams])

    fitted = X @ beta
    resid = y - fitted
    dof = max(len(y) - (n_teams + 1), 1)
    sigma = float(np.sqrt(np.sum(resid**2) / dof))

    return {
        "ratings": ratings.sort_values(ascending=False),
        "home_adv": home_adv,
        "sigma": sigma,
    }


def predict(g: pd.DataFrame, ratings: pd.Series, home_adv: float) -> np.ndarray:
    """Predicted (capped-scale) margin for each game in g, home minus away."""
    home_r = g["home_franchise"].map(ratings).to_numpy()
    away_r = g["away_franchise"].map(ratings).to_numpy()
    hf = np.where(g["neutral_site"].to_numpy(), 0.0, home_adv)
    return home_r - away_r + hf
