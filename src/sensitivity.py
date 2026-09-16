"""
Phase 3 sensitivity checks, per BUILD_PLAN section 6:

- 1987: "three replacement-player weeks... default proposal: include but
  flag; test sensitivity." This refits 1987 with vs. without the 42
  flagged games and measures how much team ratings and rankings move.
- 1982: no with/without variant exists (the whole season was played as a
  9-game, 16-team tournament - there's nothing to exclude), so its
  "wider uncertainty" requirement is checked instead by confirming the
  Bayesian model's posterior standard error (which shrinks with more
  games, by construction - see src/models/bayesian_margin.py) is in fact
  wider for 1982 than for its neighboring seasons.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from era import flag_1987_replacement_games
from models.bayesian_margin import fit_bayesian_margin
from models.common import season_games
from models.massey import fit_massey


def compare_1987_with_and_without_replacement_games(games: pd.DataFrame) -> dict:
    g = season_games(games, 1987)
    is_replacement = flag_1987_replacement_games(g)
    g_without = g[~is_replacement]

    results = {}
    for model_name, fit_fn in (("massey", fit_massey), ("bayesian_margin", fit_bayesian_margin)):
        with_all = fit_fn(g)["ratings"]
        without = fit_fn(g_without)["ratings"]
        common_teams = with_all.index.intersection(without.index)
        with_all, without = with_all.loc[common_teams], without.loc[common_teams]

        rho, _ = spearmanr(with_all, without)
        diff = (with_all - without).abs()
        table = pd.DataFrame(
            {
                "rating_with_replacement_games": with_all,
                "rating_without_replacement_games": without,
                "abs_change": diff,
            }
        ).sort_values("abs_change", ascending=False)

        results[model_name] = {
            "spearman_rank_correlation": float(rho),
            "mean_abs_change": float(diff.mean()),
            "max_abs_change": float(diff.max()),
            "most_affected_team": diff.idxmax(),
            "table": table,
        }
    return results


def replacement_game_records_1987(games: pd.DataFrame) -> pd.DataFrame:
    """Each team's W-L and point differential in the 42 replacement-player
    games alone, from our own data - so the report's historical framing of
    who the replacement weeks helped and hurt is grounded, not recalled."""
    g = season_games(games, 1987)
    rep = g[flag_1987_replacement_games(g)]
    rows = []
    for team in sorted(set(rep["home_franchise"]).union(rep["away_franchise"])):
        home = rep[rep["home_franchise"] == team]
        away = rep[rep["away_franchise"] == team]
        wins = int((home["margin"] > 0).sum() + (away["margin"] < 0).sum())
        losses = int((home["margin"] < 0).sum() + (away["margin"] > 0).sum())
        rows.append(
            {
                "team": team,
                "wins": wins,
                "losses": losses,
                "point_diff": int(home["margin"].sum() - away["margin"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("point_diff").reset_index(drop=True)


def check_1982_uncertainty_is_wider(team_season_ratings: pd.DataFrame) -> pd.DataFrame:
    se_by_season = team_season_ratings.groupby("season")["bayes_rating_se"].mean()
    window = se_by_season.loc[1978:1986]
    return pd.DataFrame(
        {
            "season": window.index,
            "mean_bayes_rating_se": window.values,
            "is_1982": window.index == 1982,
        }
    )
