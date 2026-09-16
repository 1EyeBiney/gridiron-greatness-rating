"""
Season-restarted Elo: a sanity comparator only, per BUILD_PLAN section 5
("Elo (season-restarted) as a sanity comparator, not a candidate for the
headline"). Every team resets to 1500 at the start of each season and
ratings update game by game in the order actually played.

Constants (K-factor 20, home-field worth 48 Elo points, ~25 Elo points per
point of margin to translate a rating gap into a predicted score margin)
follow the values FiveThirtyEight published for its NFL Elo model - a
reasonable, documented starting point for a comparator that this project
does not intend to tune further.

Unlike the batch models (Massey, Bradley-Terry, Bayesian), which fit a
whole season at once, Elo's prediction for each game only ever uses
ratings updated from games earlier in that same season - it never has
access to same-season future results. See src/evaluate.py for how this
changes what "out-of-sample" means for Elo versus the batch models.
"""
import numpy as np
import pandas as pd

from .common import outcome_label

K_FACTOR = 20.0
HOME_FIELD_ELO = 48.0
ELO_POINTS_PER_MARGIN_POINT = 25.0
START_RATING = 1500.0


def _expected(diff: float) -> float:
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def run_elo(g: pd.DataFrame) -> pd.DataFrame:
    """Process one season's games in chronological order. Returns a frame
    aligned with g's row order, adding pre-game elo ratings, expected home
    win probability, and expected margin (for MAE comparison against the
    other models) for every game - each computed from only the games
    before it that season."""
    teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
    ratings = {t: START_RATING for t in teams}

    pre_home_elo = np.empty(len(g))
    pre_away_elo = np.empty(len(g))
    p_home_win = np.empty(len(g))
    pred_margin = np.empty(len(g))

    for i, row in enumerate(g.itertuples()):
        r_home = ratings[row.home_franchise]
        r_away = ratings[row.away_franchise]
        hf = 0.0 if row.neutral_site else HOME_FIELD_ELO
        diff = r_home - r_away + hf

        pre_home_elo[i] = r_home
        pre_away_elo[i] = r_away
        p_home_win[i] = _expected(diff)
        pred_margin[i] = diff / ELO_POINTS_PER_MARGIN_POINT

        actual = outcome_label(np.array([row.margin]))[0]
        delta = K_FACTOR * (actual - p_home_win[i])
        ratings[row.home_franchise] = r_home + delta
        ratings[row.away_franchise] = r_away - delta

    out = g.copy()
    out["pre_home_elo"] = pre_home_elo
    out["pre_away_elo"] = pre_away_elo
    out["p_home_win"] = p_home_win
    out["pred_margin"] = pred_margin
    return out


def final_ratings(processed: pd.DataFrame) -> pd.Series:
    """End-of-season Elo rating per team, derived from the last game each
    team played (post-update rating = pre-game rating +/- delta is not
    stored per game, so recompute the final state directly)."""
    teams = sorted(set(processed["home_franchise"]).union(processed["away_franchise"]))
    ratings = {t: START_RATING for t in teams}
    for row in processed.itertuples():
        hf = 0.0 if row.neutral_site else HOME_FIELD_ELO
        diff = ratings[row.home_franchise] - ratings[row.away_franchise] + hf
        p = _expected(diff)
        actual = outcome_label(np.array([row.margin]))[0]
        delta = K_FACTOR * (actual - p)
        ratings[row.home_franchise] += delta
        ratings[row.away_franchise] -= delta
    return pd.Series(ratings).sort_values(ascending=False)
