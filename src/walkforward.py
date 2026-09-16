"""
Phase 4's out-of-sample validation: genuinely no future leakage, unlike
Phase 2's within-season 5-fold cross-validation (which let a Week 15
result inform a prediction for a Week 3 game in the same fold-fit).

For every season, for every week w from the second onward, each batch
model (Massey, Bradley-Terry, Bayesian) is fit only on that season's
games from weeks before w, then used to predict week w's games -
including postseason weeks, which continue the same week index (see
schedule_weeks.py). Week 1 is never predicted: there is no within-season
history yet for any model to fit on, for any team.

Elo needs no special handling here - it already updates after every
single game with zero access to future results, which is a strictly
finer-grained (and equally leakage-free) walk-forward than the weekly
refits used for the other three. Its predictions are pulled from the
same run_elo() used in Phase 2, just restricted to week >= 2 so every
model is scored on the identical set of games.
"""
import numpy as np
import pandas as pd

from models.bayesian_margin import fit_bayesian_margin, predict as bayes_predict
from models.bradley_terry import fit_bradley_terry, predict_win_prob as bt_predict
from models.common import (
    home_win_prob_normal,
    is_schedule_connected,
    load_games,
    outcome_label,
    predictive_sigma,
    season_games,
)
from models.elo import run_elo
from models.massey import fit_massey, predict as massey_predict
from schedule_weeks import assign_week_index


def _known_teams_only(test: pd.DataFrame, rated_teams) -> pd.DataFrame:
    known = test["home_franchise"].isin(rated_teams) & test["away_franchise"].isin(rated_teams)
    return test[known]


def walk_forward_season(g: pd.DataFrame, bt_reg_strength: float) -> pd.DataFrame:
    g = g.copy()
    g["week_idx"] = assign_week_index(g)
    weeks = sorted(g["week_idx"].unique())

    rows = []
    for w in weeks[1:]:
        train = g[g["week_idx"] < w]
        test = g[g["week_idx"] == w]
        if train.empty or test.empty:
            continue
        graph_connected = is_schedule_connected(train)

        massey_fit = fit_massey(train)
        bayes_fit = fit_bayesian_margin(train)
        bt_fit = fit_bradley_terry(train, reg_strength=bt_reg_strength)

        for model_name, fit, margin_predict_fn in (
            ("massey", massey_fit, massey_predict),
            ("bayesian_margin", bayes_fit, bayes_predict),
        ):
            known = _known_teams_only(test, fit["ratings"].index)
            if known.empty:
                continue
            pred_margin = margin_predict_fn(known, fit["ratings"], fit["home_adv"])
            pred_sigma = predictive_sigma(known, fit["team_index"], fit["beta_cov_unscaled"], fit["sigma"])
            p_home = home_win_prob_normal(pred_margin, pred_sigma)
            rows.append(
                pd.DataFrame(
                    {
                        "game_uid": known["game_uid"].to_numpy(),
                        "week_idx": w,
                        "model": model_name,
                        "margin": known["margin"].to_numpy(),
                        "pred_margin": pred_margin,
                        "p_home_win": p_home,
                        "graph_connected": graph_connected,
                    }
                )
            )

        known = _known_teams_only(test, bt_fit["ratings"].index)
        if not known.empty:
            p_home = bt_predict(known, bt_fit["ratings"], bt_fit["home_adv"])
            rows.append(
                pd.DataFrame(
                    {
                        "game_uid": known["game_uid"].to_numpy(),
                        "week_idx": w,
                        "model": "bradley_terry",
                        "margin": known["margin"].to_numpy(),
                        "pred_margin": np.nan,
                        "p_home_win": p_home,
                        "graph_connected": graph_connected,
                    }
                )
            )

    if not rows:
        return pd.DataFrame(
            columns=["game_uid", "week_idx", "model", "margin", "pred_margin", "p_home_win", "graph_connected"]
        )
    return pd.concat(rows, ignore_index=True)


def bt_walk_forward_log_loss(seasons, reg_strength: float) -> float:
    """Bradley-Terry-only walk-forward log loss, for tuning reg_strength
    without paying for Massey/Bayesian refits at every candidate value."""
    games = load_games()
    label_list, p_list = [], []
    for season in seasons:
        g = season_games(games, season).copy()
        g["week_idx"] = assign_week_index(g)
        weeks = sorted(g["week_idx"].unique())
        for w in weeks[1:]:
            train = g[g["week_idx"] < w]
            test = g[g["week_idx"] == w]
            if train.empty or test.empty:
                continue
            fit = fit_bradley_terry(train, reg_strength=reg_strength)
            known = _known_teams_only(test, fit["ratings"].index)
            if known.empty:
                continue
            p_list.append(bt_predict(known, fit["ratings"], fit["home_adv"]))
            label_list.append(outcome_label(known["margin"].to_numpy()))
    label = np.concatenate(label_list)
    p = np.clip(np.concatenate(p_list), 1e-9, 1 - 1e-9)
    return float(-np.mean(label * np.log(p) + (1 - label) * np.log(1 - p)))


def elo_predictions_for_eval(g: pd.DataFrame) -> pd.DataFrame:
    g = g.copy()
    g["week_idx"] = assign_week_index(g)
    processed = run_elo(g)
    processed["week_idx"] = g["week_idx"]
    processed = processed[processed["week_idx"] >= 2]

    connected_by_week = {
        w: is_schedule_connected(g[g["week_idx"] < w]) for w in sorted(processed["week_idx"].unique())
    }
    return pd.DataFrame(
        {
            "game_uid": processed["game_uid"].to_numpy(),
            "week_idx": processed["week_idx"].to_numpy(),
            "model": "elo",
            "margin": processed["margin"].to_numpy(),
            "pred_margin": processed["pred_margin"].to_numpy(),
            "p_home_win": processed["p_home_win"].to_numpy(),
            "graph_connected": processed["week_idx"].map(connected_by_week).to_numpy(),
        }
    )


def walk_forward_all_seasons(seasons, bt_reg_strength: float) -> pd.DataFrame:
    games = load_games()
    frames = []
    for season in seasons:
        g = season_games(games, season)
        batch = walk_forward_season(g, bt_reg_strength)
        batch["season"] = season
        elo = elo_predictions_for_eval(g)
        elo["season"] = season
        frames.append(batch)
        frames.append(elo)
    return pd.concat(frames, ignore_index=True)
