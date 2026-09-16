"""
Phase 2 model comparison: out-of-sample predictive accuracy for the three
batch candidate models (Massey, Bradley-Terry, Bayesian hierarchical
margin) via k-fold cross-validation within each season, plus Elo's
natural walk-forward (prequential) evaluation as an informal sanity
comparison.

This is Phase 2's first look at predictive accuracy, per BUILD_PLAN
section 5's selection criterion. The full validation - out-of-sample
results across every season, spread comparison, and the adversarial
audit that locks the model family - is Phase 4's job, not this script's.

Cross-validation splits games, not teams: each fold holds out ~1/k of a
season's games (across all teams) and refits the model on the rest. For a
network rating model this is a meaningfully weaker out-of-sample test
than Phase 4's will be (it doesn't test predicting a future week from
only past weeks), but it is enough to see whether one model family is
obviously and consistently more accurate than another, which is what
Phase 2 needs.

Elo's evaluation is not k-fold at all - every prediction uses only
ratings built from that same season's earlier games, with zero
in-season future leakage. That is a genuinely different (and in one
sense stricter) protocol than the other three get, so Elo's numbers here
are informative but not an apples-to-apples ranking against the batch
models.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from models.bayesian_margin import fit_bayesian_margin, predict as bayes_predict
from models.bradley_terry import fit_bradley_terry, predict_win_prob as bt_predict
from models.common import load_games, log_loss, outcome_label, season_games
from models.elo import run_elo
from models.massey import fit_massey, predict as massey_predict

N_FOLDS = 5
SEED = 42


def _fold_indices(n: int, k: int, seed: int):
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    folds = np.array_split(order, k)
    for i in range(k):
        test_idx = folds[i]
        train_idx = np.concatenate([folds[j] for j in range(k) if j != i])
        yield train_idx, test_idx


def _margin_mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def _accuracy(actual_label: np.ndarray, p_home_win: np.ndarray) -> float:
    predicted_home_win = p_home_win > 0.5
    decided = actual_label != 0.5
    if not decided.any():
        return float("nan")
    return float(np.mean(predicted_home_win[decided] == (actual_label[decided] == 1.0)))


def _known_teams_only(test: pd.DataFrame, rated_teams) -> pd.DataFrame:
    known = test["home_franchise"].isin(rated_teams) & test["away_franchise"].isin(rated_teams)
    return test[known]


def _weighted_average(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "log_loss": np.nan, "margin_mae": np.nan, "accuracy": np.nan}
    n = sum(r["n"] for r in rows)
    out = {"n": n}
    for key in ("log_loss", "margin_mae", "accuracy"):
        vals = np.array([r[key] for r in rows], dtype=float)
        weights = np.array([r["n"] for r in rows], dtype=float)
        valid = ~np.isnan(vals)
        out[key] = float(np.average(vals[valid], weights=weights[valid])) if valid.any() else np.nan
    return out


def cv_massey(g: pd.DataFrame, k: int = N_FOLDS, seed: int = SEED) -> dict:
    rows = []
    for train_idx, test_idx in _fold_indices(len(g), k, seed):
        fit = fit_massey(g.iloc[train_idx])
        test = _known_teams_only(g.iloc[test_idx], fit["ratings"].index)
        if test.empty:
            continue
        pred_margin = massey_predict(test, fit["ratings"], fit["home_adv"])
        actual_margin = test["margin"].to_numpy()
        p_home = norm.cdf(pred_margin / fit["sigma"])
        label = outcome_label(actual_margin)
        rows.append(
            {
                "n": len(test),
                "log_loss": log_loss(label, p_home),
                "margin_mae": _margin_mae(actual_margin, pred_margin),
                "accuracy": _accuracy(label, p_home),
            }
        )
    return _weighted_average(rows)


def cv_bradley_terry(g: pd.DataFrame, k: int = N_FOLDS, seed: int = SEED) -> dict:
    rows = []
    for train_idx, test_idx in _fold_indices(len(g), k, seed):
        fit = fit_bradley_terry(g.iloc[train_idx])
        test = _known_teams_only(g.iloc[test_idx], fit["ratings"].index)
        if test.empty:
            continue
        p_home = bt_predict(test, fit["ratings"], fit["home_adv"])
        actual_margin = test["margin"].to_numpy()
        label = outcome_label(actual_margin)
        rows.append(
            {
                "n": len(test),
                "log_loss": log_loss(label, p_home),
                "margin_mae": np.nan,
                "accuracy": _accuracy(label, p_home),
            }
        )
    return _weighted_average(rows)


def cv_bayesian(g: pd.DataFrame, k: int = N_FOLDS, seed: int = SEED) -> dict:
    rows = []
    for train_idx, test_idx in _fold_indices(len(g), k, seed):
        fit = fit_bayesian_margin(g.iloc[train_idx])
        test = _known_teams_only(g.iloc[test_idx], fit["ratings"].index)
        if test.empty:
            continue
        pred_margin = bayes_predict(test, fit["ratings"], fit["home_adv"])
        actual_margin = test["margin"].to_numpy()
        p_home = norm.cdf(pred_margin / fit["sigma"])
        label = outcome_label(actual_margin)
        rows.append(
            {
                "n": len(test),
                "log_loss": log_loss(label, p_home),
                "margin_mae": _margin_mae(actual_margin, pred_margin),
                "accuracy": _accuracy(label, p_home),
            }
        )
    return _weighted_average(rows)


def prequential_elo(g: pd.DataFrame) -> dict:
    processed = run_elo(g)
    actual_margin = processed["margin"].to_numpy()
    p_home = processed["p_home_win"].to_numpy()
    pred_margin = processed["pred_margin"].to_numpy()
    label = outcome_label(actual_margin)
    return {
        "n": len(processed),
        "log_loss": log_loss(label, p_home),
        "margin_mae": _margin_mae(actual_margin, pred_margin),
        "accuracy": _accuracy(label, p_home),
    }


def evaluate_all_seasons(seasons) -> pd.DataFrame:
    games = load_games()
    records = []
    for season in seasons:
        g = season_games(games, season)
        for model_name, cv_fn in (
            ("massey", cv_massey),
            ("bradley_terry", cv_bradley_terry),
            ("bayesian_margin", cv_bayesian),
        ):
            metrics = cv_fn(g)
            metrics.update({"season": season, "model": model_name})
            records.append(metrics)
        metrics = prequential_elo(g)
        metrics.update({"season": season, "model": "elo"})
        records.append(metrics)
    return pd.DataFrame.from_records(records)
