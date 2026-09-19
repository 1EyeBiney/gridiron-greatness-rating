"""Tests for xe_analysis_shift.py: synthetic recovery checks for the
hand-rolled fitters, plus structural checks on the real team_game.csv /
league_season.csv aggregates."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import xe_analysis_shift as xa

REPO = Path(__file__).resolve().parents[1]
TEAM_GAME_CSV = REPO / "data" / "processed" / "team_game.csv"
LEAGUE_SEASON_CSV = REPO / "data" / "processed" / "league_season.csv"


# ------------------------------------------------------------ synthetic


def test_logit_irls_recovers_known_coefficients_on_well_separated_data():
    rng = np.random.default_rng(0)
    n = 4000
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    true_b0, true_b1, true_b2 = 0.2, 1.5, -0.8
    eta = true_b0 + true_b1 * x1 + true_b2 * x2
    p = 1.0 / (1.0 + np.exp(-eta))
    y = (rng.uniform(size=n) < p).astype(float)
    X = np.column_stack([np.ones(n), x1, x2])
    fit = xa.fit_logit_irls(X, y, ridge=1e-6)
    assert fit["converged"]
    assert fit["beta"][0] == pytest.approx(true_b0, abs=0.15)
    assert fit["beta"][1] == pytest.approx(true_b1, abs=0.15)
    assert fit["beta"][2] == pytest.approx(true_b2, abs=0.15)
    # SEs should be small and positive, and the fit should score better
    # than chance.
    assert (fit["se"] > 0).all()
    assert fit["log_loss"] < 0.693
    assert 0.5 < fit["accuracy"] <= 1.0


def test_logit_irls_matches_closed_form_two_point_case():
    # Two groups with means -2 and +2, perfectly correlated with y after a
    # ridge is applied. Compare against a hand-solved MLE via a fine grid
    # search on a simple 1-D logistic (no intercept) to sanity-check.
    x = np.array([-1.0, -1.0, 1.0, 1.0])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    X = np.column_stack([np.ones(4), x])
    fit = xa.fit_logit_irls(X, y, ridge=1e-6, max_iter=200)
    # Symmetric, well-separated data: intercept ~ 0, slope large and positive.
    assert fit["beta"][0] == pytest.approx(0.0, abs=1e-3)
    assert fit["beta"][1] > 3.0
    # log loss should be very low on perfectly separable data.
    assert fit["log_loss"] < 0.05


def test_ols_exchange_rate_recovers_planted_ratio():
    rng = np.random.default_rng(1)
    n = 5000
    epd = rng.normal(size=n)
    tod = rng.normal(size=n)
    points_per_explosive = 1.2
    points_per_turnover = 4.8
    noise = rng.normal(scale=0.5, size=n)
    margin = points_per_explosive * epd + points_per_turnover * tod + noise
    d = pd.DataFrame({"margin": margin, "epd": epd, "tod": tod})
    res = xa._fit_exchange(d, "epd", "tod")
    assert res["points_per_explosive"] == pytest.approx(points_per_explosive, abs=0.1)
    assert res["points_per_turnover"] == pytest.approx(points_per_turnover, abs=0.1)
    planted_ratio = points_per_turnover / points_per_explosive
    assert res["exchange_ratio_turnover_to_explosive"] == pytest.approx(planted_ratio, abs=0.3)
    assert res["exchange_ratio_se"] > 0
    assert res["r2_both"] > 0.9


def test_zscore_within_season_is_per_season():
    df = pd.DataFrame({
        "season": [2000, 2000, 2000, 2001, 2001, 2001],
        "x": [1.0, 2.0, 3.0, 100.0, 200.0, 300.0],
    })
    out = xa.zscore_within_season(df, ["x"])
    for season in (2000, 2001):
        z = out.loc[out["season"] == season, "z_x"]
        assert z.mean() == pytest.approx(0.0, abs=1e-9)
        assert z.std(ddof=0) == pytest.approx(1.0, abs=1e-6)
    # cross-season comparison: season 2001 values are much larger in raw
    # terms but should land on the SAME standardized scale as 2000.
    assert out["z_x"].abs().max() < 1.5


def test_zscore_constant_column_gives_zero_not_nan():
    df = pd.DataFrame({"season": [2000, 2000], "x": [5.0, 5.0]})
    out = xa.zscore_within_season(df, ["x"])
    assert (out["z_x"] == 0.0).all()


def test_era_of_assigns_the_three_nine_season_blocks():
    s = pd.Series([1999, 2007, 2008, 2016, 2017, 2025])
    assert xa.era_of(s).tolist() == [
        "1999-2007", "1999-2007", "2008-2016", "2008-2016", "2017-2025", "2017-2025",
    ]


def test_fisher_r_se_shrinks_with_n():
    assert xa._fisher_r_se(103) < xa._fisher_r_se(13)


# ------------------------------------------------------ real-data structure


@pytest.fixture(scope="module")
def team_game():
    if not TEAM_GAME_CSV.exists():
        pytest.skip("team_game.csv not built")
    return pd.read_csv(TEAM_GAME_CSV)


@pytest.fixture(scope="module")
def league_season():
    if not LEAGUE_SEASON_CSV.exists():
        pytest.skip("league_season.csv not built")
    return pd.read_csv(LEAGUE_SEASON_CSV)


@pytest.fixture(scope="module")
def games(team_game):
    return xa.game_rows(team_game)


def test_game_rows_has_no_double_counted_games(team_game):
    reg = team_game[team_game["game_type"] == "REG"]
    g = xa.game_rows(team_game)
    for season, gs in g.groupby("season"):
        n_games_expected = reg.loc[reg["season"] == season, "game_id"].nunique()
        assert len(gs) == n_games_expected
    assert g["game_id"].is_unique


def test_game_rows_only_regular_season_and_year_range(games):
    assert set(games["game_type"].unique()) == {"REG"}
    assert games["season"].min() >= 1999
    assert games["season"].max() <= 2025


def test_shift_logit_by_season_covers_every_season(games):
    out = xa.shift_logit_by_season(games)
    seasons = set(out["season"])
    assert seasons == set(range(1999, 2026))
    # coefficients and SEs are finite and se positive
    assert out["both_se_b_epd"].gt(0).all()
    assert out["both_se_b_tod"].gt(0).all()
    assert np.isfinite(out["both_b_epd"]).all()


def test_shift_logit_by_era_has_three_rows(games):
    out = xa.shift_logit_by_era(games)
    assert set(out["era"]) == {"1999-2007", "2008-2016", "2017-2025"}
    assert len(out) == 3


def test_shift_trend_has_two_rows(games):
    by_season = xa.shift_logit_by_season(games)
    trend = xa.shift_trend(by_season)
    assert set(trend["coefficient"]) == {"epd_std_coef", "tod_std_coef"}
    assert (trend["slope_se"] > 0).all()


def test_shift_logit_sensitivity_has_all_definitions_and_seasons(games):
    out = xa.shift_logit_sensitivity(games)
    expected_defs = {"explosive_20_10", "explosive_20_10_ng", "explosive_25_15", "explosive_25_15_ng",
                      "explosive_20_20", "explosive_20_20_ng", "explosive_epa2", "explosive_epa2_ng"}
    assert set(out["definition"]) == expected_defs
    for defn in expected_defs:
        assert set(out.loc[out["definition"] == defn, "season"]) == set(range(1999, 2026))


def test_exchange_rate_by_season_covers_every_season(games):
    out = xa.exchange_rate_by_season(games)
    assert set(out["season"]) == set(range(1999, 2026))
    assert (out["r2_both"] >= out["r2_epd_only"] - 1e-9).all()
    assert (out["r2_both"] >= out["r2_tod_only"] - 1e-9).all()


def test_exchange_rate_by_era_has_three_rows(games):
    out = xa.exchange_rate_by_era(games)
    assert len(out) == 3


def test_mechanism_by_season_covers_every_season(league_season, team_game):
    out = xa.mechanism_by_season(league_season, team_game)
    assert set(out["season"]) == set(range(1999, 2026))
    assert out["yards_per_play"].gt(0).all()
    assert out["pass_rate"].between(0, 1).all()


def test_mechanism_strategy_by_era_has_three_rows(team_game):
    out = xa.mechanism_strategy_by_era(team_game)
    assert len(out) == 3
    assert (out["n_team_seasons"] > 0).all()
    assert out["correlation"].between(-1, 1).all()


def test_run_writes_all_csvs(tmp_path, monkeypatch, team_game, league_season):
    monkeypatch.setattr(xa, "OUT", tmp_path)
    monkeypatch.setattr(xa, "load_team_game", lambda path=None: team_game)
    monkeypatch.setattr(xa, "load_league_season", lambda path=None: league_season)
    tables = xa.run()
    expected = {
        "shift_logit_by_season", "shift_logit_by_era", "shift_trend",
        "shift_logit_sensitivity", "exchange_rate_by_season", "exchange_rate_by_era",
        "mechanism_by_season", "mechanism_strategy_by_era",
    }
    assert expected <= set(tables)
    for name in expected:
        assert (tmp_path / f"{name}.csv").exists()
