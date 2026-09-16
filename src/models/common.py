"""
Shared utilities for Phase 2 candidate rating models (Massey, Bradley-Terry,
Bayesian hierarchical margin, Elo). Unlike the Phase 1 SRS validation tool
(src/srs.py), which deliberately matched Pro Football Reference's
regular-season-only, no-home-field convention, every model here is fit on
every game a team played that season - regular season and postseason -
per BUILD_PLAN section 2.
"""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]

MARGIN_CAP = 28  # BUILD_PLAN section 4, Blowout rule.


def load_games() -> pd.DataFrame:
    return pd.read_csv(REPO / "data" / "processed" / "games.csv")


def season_games(games: pd.DataFrame, season: int) -> pd.DataFrame:
    """All games for one season, sorted chronologically so sequential
    models (Elo) process them in the order actually played."""
    g = games[games["season"] == season].copy()
    return g.sort_values(["date", "game_uid"]).reset_index(drop=True)


def capped_margin(margin) -> np.ndarray:
    """Blowout rule: cap each game's margin at +/-28 points so one
    lopsided game cannot dominate a season's rating."""
    return np.clip(np.asarray(margin, dtype=float), -MARGIN_CAP, MARGIN_CAP)


def team_index(g: pd.DataFrame) -> dict:
    teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
    return {t: i for i, t in enumerate(teams)}


def design_matrix(g: pd.DataFrame, idx: dict) -> np.ndarray:
    """+1 at the home team's column, -1 at the away team's column, and a
    trailing home-field column that is 1 at the home team's own stadium
    and 0 for a designated neutral site (BUILD_PLAN section 6: neutral
    sites get no home-field term)."""
    n_teams = len(idx)
    X = np.zeros((len(g), n_teams + 1))
    home_cols = g["home_franchise"].map(idx).to_numpy()
    away_cols = g["away_franchise"].map(idx).to_numpy()
    rows = np.arange(len(g))
    X[rows, home_cols] = 1.0
    X[rows, away_cols] = -1.0
    X[rows, n_teams] = np.where(g["neutral_site"].to_numpy(), 0.0, 1.0)
    return X


def zero_sum_constraint(n_teams: int) -> np.ndarray:
    """A single row pinning the team ratings to sum to zero (league-average
    team is 0), needed because a home/away difference design is only
    identified up to a shared additive constant on team columns; the
    trailing home-field column is left unconstrained."""
    row = np.zeros(n_teams + 1)
    row[:n_teams] = 1.0
    return row


MIN_SIGMA = 1.0  # points; real season-long sigmas run 10-13 (see model_params.csv)


def home_win_prob_normal(rating_diff: np.ndarray, sigma) -> np.ndarray:
    """P(home team's margin > 0) under margin ~ Normal(rating_diff, sigma^2),
    used to turn a point-margin model (Massey, Bayesian) into a win
    probability for log-loss scoring against Bradley-Terry/Elo. sigma may
    be a scalar or a per-game array (see predictive_sigma).

    sigma is floored at MIN_SIGMA as a last-resort safety net: a
    perfectly-fit system (more free parameters than informative games)
    can return a residual sigma of ~1e-15, pure floating-point noise
    rather than a real uncertainty estimate, and dividing by that turns
    floating-point noise in rating_diff into an arbitrary-looking,
    unstable probability. The floor is far below any real value here
    (full-season sigmas run 10-13, see model_params.csv), so it never
    affects a well-determined fit - use predictive_sigma() for the actual
    fix to small-sample overconfidence, not a larger floor.
    """
    from scipy.stats import norm

    return norm.cdf(rating_diff / np.maximum(sigma, MIN_SIGMA))


def is_schedule_connected(g: pd.DataFrame) -> bool:
    """True if every team that has appeared in g is linked to every other
    by some chain of shared opponents. A disconnected schedule graph means
    at least two teams' relative rating gap isn't just uncertain - it is
    completely unconstrained by the data (e.g. the entire league after
    week 1 of a season, which is just N/2 isolated pairs). Regularized
    models (Bayesian, Bradley-Terry) handle this gracefully by construction
    (shrinking toward a neutral prediction); plain least squares (Massey)
    does not - its minimum-norm solution silently asserts zero uncertainty
    in exactly the directions the data says nothing about. See
    src/walkforward.py and docs/PHASE4_WALKFORWARD_VALIDATION.md.
    """
    teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
    if len(teams) <= 1:
        return True
    parent = {t: t for t in teams}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for row in g.itertuples():
        ra, rb = find(row.home_franchise), find(row.away_franchise)
        if ra != rb:
            parent[ra] = rb

    return len({find(t) for t in teams}) == 1


def predictive_sigma(g: pd.DataFrame, team_index_map: dict, beta_cov_unscaled: np.ndarray, sigma: float) -> np.ndarray:
    """Per-game predictive standard deviation for a linear rating model's
    margin: sigma * sqrt(1 + x^T Cov_unscaled x), the standard OLS/ridge
    prediction-interval formula (residual/game-to-game noise PLUS
    uncertainty in the fitted ratings themselves).

    Using the flat in-sample sigma alone (residual noise only) badly
    understates true predictive uncertainty early in a walk-forward
    season: with few games played, a model can fit that small, weakly-
    identified sample almost exactly, making its own residual sigma
    spuriously small - and then a perfectly ordinary predicted rating gap
    of 10 points, divided by a residual sigma of 1, looks like a near-
    certain outcome instead of the coin flip it actually is. This
    quadratic term is exactly what's missing: with little data, x^T
    Cov_unscaled x is large (the fitted ratings are barely determined),
    which correctly widens the predictive interval back out.
    """
    X_new = design_matrix(g, team_index_map)
    quad = np.einsum("ij,jk,ik->i", X_new, beta_cov_unscaled, X_new)
    return sigma * np.sqrt(np.maximum(1.0 + quad, 1e-12))


def log_loss(y_true: np.ndarray, p_home_win: np.ndarray) -> float:
    """Binary log loss. Ties score against p as a 0.5 outcome (BUILD_PLAN
    section 6: ties are treated as a half-win where record matters)."""
    p = np.clip(p_home_win, 1e-9, 1 - 1e-9)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def outcome_label(margin: np.ndarray) -> np.ndarray:
    """1.0 if home team won, 0.0 if home team lost, 0.5 for a tie."""
    return np.where(margin > 0, 1.0, np.where(margin < 0, 0.0, 0.5))
