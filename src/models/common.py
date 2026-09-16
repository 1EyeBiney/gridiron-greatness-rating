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


def home_win_prob_normal(rating_diff: np.ndarray, sigma: float) -> np.ndarray:
    """P(home team's margin > 0) under margin ~ Normal(rating_diff, sigma^2),
    used to turn a point-margin model (Massey, Bayesian) into a win
    probability for log-loss scoring against Bradley-Terry/Elo."""
    from scipy.stats import norm

    return norm.cdf(rating_diff / sigma)


def log_loss(y_true: np.ndarray, p_home_win: np.ndarray) -> float:
    """Binary log loss. Ties score against p as a 0.5 outcome (BUILD_PLAN
    section 6: ties are treated as a half-win where record matters)."""
    p = np.clip(p_home_win, 1e-9, 1 - 1e-9)
    return float(-np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p)))


def outcome_label(margin: np.ndarray) -> np.ndarray:
    """1.0 if home team won, 0.0 if home team lost, 0.5 for a tie."""
    return np.where(margin > 0, 1.0, np.where(margin < 0, 0.0, 0.5))
