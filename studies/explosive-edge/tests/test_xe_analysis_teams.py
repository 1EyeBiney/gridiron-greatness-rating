"""Synthetic-data tests for xe_analysis_teams.py (analyses D, E, F)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import xe_analysis_teams as xat

REPO = Path(__file__).resolve().parents[1]
TEAM_GAME_CSV = REPO / "data" / "processed" / "team_game.csv"
TSR_CSV = xat.TSR_CSV


# ---------------------------------------------------------------- D: split


def _game_row(**kw):
    base = dict(
        game_id="g", season=2010, week=1, game_type="REG", team="AA", opponent="BB", is_home=True,
        plays=60, explosive_20_10=6, explosive_20_10_diff=1, turnovers=1, turnovers_diff=0,
        turnovers_ng=1, turnovers_ng_diff=0, explosive_20_10_ng=6, explosive_20_10_ng_diff=1,
        margin=3, win=1.0, yards=350, franchise="AA", points_for=24,
    )
    base.update(kw)
    return base


def test_split_half_uses_week_order_and_floor():
    # 5 games -> floor(5/2) = 2 in the first half, 3 in the second, in week order.
    games = pd.DataFrame([
        _game_row(week=3, plays=10),
        _game_row(week=1, plays=20),
        _game_row(week=5, plays=30),
        _game_row(week=2, plays=40),
        _game_row(week=4, plays=50),
    ])
    games = games.sort_values("week")
    split = xat.split_half(games)
    assert split["n_games"] == 5
    assert split["first"]["n_games"] == 2
    assert split["second"]["n_games"] == 3
    # first half = weeks 1,2 -> plays 20,40; second half = weeks 3,4,5 -> plays 10,50,30
    assert split["first"]["explosive_rate_per_play"] == pytest.approx(12 / 60)
    assert split["second"]["explosive_rate_per_play"] == pytest.approx(18 / 90)


def test_split_half_none_for_single_game():
    games = pd.DataFrame([_game_row()])
    assert xat.split_half(games) is None


def test_split_half_odd_n_second_half_gets_extra_game():
    games = pd.DataFrame([_game_row(week=w) for w in range(1, 8)])  # 7 games
    split = xat.split_half(games)
    assert split["first"]["n_games"] == 3
    assert split["second"]["n_games"] == 4


# ------------------------------------------------------- D: pearson/fisher


def test_pearson_ci_matches_hand_computation():
    rng = np.random.default_rng(0)
    x = rng.normal(size=40)
    y = 0.6 * x + rng.normal(size=40) * 0.5
    stats = xat.pearson_ci(x, y)
    hand_r = np.corrcoef(x, y)[0, 1]
    assert stats["n"] == 40
    assert stats["r"] == pytest.approx(hand_r, abs=1e-12)
    z = np.arctanh(hand_r)
    se = 1 / np.sqrt(40 - 3)
    lo_hand = np.tanh(z - 1.959963984540054 * se)
    hi_hand = np.tanh(z + 1.959963984540054 * se)
    assert stats["ci_lo"] == pytest.approx(lo_hand)
    assert stats["ci_hi"] == pytest.approx(hi_hand)
    assert stats["ci_lo"] < stats["r"] < stats["ci_hi"]


def test_pearson_ci_perfect_correlation_and_small_n():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = 2 * x + 1
    stats = xat.pearson_ci(x, y)
    assert stats["r"] == pytest.approx(1.0, abs=1e-9)
    # n=3 is below the n<4 CI cutoff
    stats_small = xat.pearson_ci(x[:3], y[:3])
    assert stats_small["n"] == 3
    assert np.isnan(stats_small["ci_lo"])


def test_persistence_table_by_group():
    rows = []
    rng = np.random.default_rng(1)
    for era, n in [("E1", 20), ("E2", 15)]:
        for i in range(n):
            first = rng.normal()
            row = {"era": era}
            for m in xat.PERSISTENCE_METRICS:
                row[f"{m}_first"] = first
                row[f"{m}_second"] = first + rng.normal() * 0.1
            rows.append(row)
    splits = pd.DataFrame(rows)
    table = xat.persistence_by_era(splits)
    assert set(table["era"]) == {"E1", "E2", "ALL"}
    assert len(table) == 3 * len(xat.PERSISTENCE_METRICS)
    for _, r in table.iterrows():
        assert r["r"] > 0.5  # strongly persistent by construction


# --------------------------------------------------------------------- E


def _h2h_game(game_id, exp_diff, tov_diff, win, season=2010):
    return _game_row(game_id=game_id, is_home=True, season=season,
                      explosive_20_10_diff=exp_diff, turnovers_diff=tov_diff, win=win)


def test_head_to_head_categories_partition_all_games():
    games = pd.DataFrame([
        _h2h_game("g1", 2, -1, win=1.0),    # home won explosive, won turnover battle (fewer giveaways) -> won_both
        _h2h_game("g2", 2, 1, win=1.0),     # home won explosive, lost turnover battle -> won_explosive_lost_turnover
        _h2h_game("g3", -2, -1, win=0.0),   # away won explosive; home turnovers_diff<0 -> home won turnover battle -> won_explosive_lost_turnover (away)
        _h2h_game("g4", 2, 0, win=1.0),     # explosive only
        _h2h_game("g5", 0, -1, win=1.0),    # turnover only (home fewer giveaways)
        _h2h_game("g6", 0, 0, win=0.5),     # both even
        _h2h_game("g7", -2, 1, win=0.0),    # away won explosive; home turnovers_diff>0 -> home lost turnover battle too -> won_both (away)
    ])
    classified = xat._classify_head_to_head(games, "explosive_20_10_diff", "turnovers_diff")
    assert len(classified) == 7  # one row per game, partitioned
    assert set(classified["game_id"]) == set(games["game_id"])
    cats = classified.set_index("game_id")["category"]
    assert cats["g1"] == "won_both"
    assert cats["g2"] == "won_explosive_lost_turnover"
    assert cats["g3"] == "won_explosive_lost_turnover"
    assert cats["g4"] == "explosive_only"
    assert cats["g5"] == "turnover_only"
    assert cats["g6"] == "both_even"
    assert cats["g7"] == "won_both"


def test_head_to_head_win_rates_from_one_row_per_game():
    # Duplicate the away-team row for each game to check dedupe-by-game_id
    # doesn't double count, and that win rate reflects the ONE team in
    # each asymmetric category.
    home_rows = [
        _h2h_game("g1", 2, 1, win=1.0),   # home wins explosive, loses turnover, home wins game
        _h2h_game("g2", 2, 1, win=0.0),   # same category, home loses game this time
        _h2h_game("g3", -2, -1, win=1.0),  # away wins explosive, loses turnover -> away is the team of interest; home wins so away lost
    ]
    away_dupes = [dict(r, is_home=False, team="opp", game_id=r["game_id"]) for r in home_rows]
    games = pd.DataFrame(home_rows + away_dupes)
    classified = xat._classify_head_to_head(games, "explosive_20_10_diff", "turnovers_diff")
    assert len(classified) == 3
    table = xat.head_to_head_table(classified, None)
    row = table[table["category"] == "won_explosive_lost_turnover"].iloc[0]
    assert row["n_games"] == 3
    # g1: home(team of interest) wins -> 1; g2: home(team of interest) loses -> 0; g3: away(team of interest), home wins -> away loses -> 0
    assert row["win_rate"] == pytest.approx(1 / 3)


def test_head_to_head_both_even_has_no_win_rate():
    games = pd.DataFrame([_h2h_game("g1", 0, 0, win=0.5)])
    classified = xat._classify_head_to_head(games, "explosive_20_10_diff", "turnovers_diff")
    table = xat.head_to_head_table(classified, None)
    row = table[table["category"] == "both_even"].iloc[0]
    assert row["n_games"] == 1
    assert np.isnan(row["win_rate"])


# --------------------------------------------------------------------- F


def _ts_row(franchise, season, **kw):
    base = _game_row(franchise=franchise, season=season, team=franchise)
    base.update(kw)
    return base


def test_leaderboard_merge_loses_no_matched_team_seasons():
    tg = pd.DataFrame([
        _ts_row("AA", 2010, game_id="1", week=1, explosive_20_10=8, explosive_20_10_diff=2, win=1.0),
        _ts_row("AA", 2010, game_id="2", week=2, explosive_20_10=6, explosive_20_10_diff=-1, win=0.0),
        _ts_row("BB", 2010, game_id="3", week=1, explosive_20_10=4, explosive_20_10_diff=-2, win=0.0),
        _ts_row("ZZ", 2010, game_id="4", week=1, explosive_20_10=5, explosive_20_10_diff=0, win=0.5),  # no TSR row
    ])
    tsr = pd.DataFrame({
        "season": [2010, 2010], "franchise": ["AA", "BB"],
        "bayes_rating_z": [1.5, -0.5], "won_super_bowl": [True, False], "reached_super_bowl": [True, False],
    })
    board, unmatched = xat.leaderboard(tg, tsr)
    assert len(board) == 3  # AA, BB, ZZ team-seasons all present
    assert unmatched == ["ZZ"]
    aa = board[board["franchise"] == "AA"].iloc[0]
    assert aa["games"] == 2
    assert aa["wins"] == 1 and aa["losses"] == 1
    assert aa["explosive_per_game"] == pytest.approx(7.0)
    assert aa["explosive_diff_per_game"] == pytest.approx(0.5)
    bb = board[board["franchise"] == "BB"].iloc[0]
    assert bb["bayes_rating_z"] == pytest.approx(-0.5)
    zz = board[board["franchise"] == "ZZ"].iloc[0]
    assert pd.isna(zz["bayes_rating_z"])


def test_leaderboard_sorted_by_explosive_diff_descending():
    tg = pd.DataFrame([
        _ts_row("AA", 2010, game_id="1", week=1, explosive_20_10_diff=5.0),
        _ts_row("BB", 2010, game_id="2", week=1, explosive_20_10_diff=-3.0),
        _ts_row("CC", 2010, game_id="3", week=1, explosive_20_10_diff=1.0),
    ])
    tsr = pd.DataFrame({"season": [], "franchise": [], "bayes_rating_z": [], "won_super_bowl": [], "reached_super_bowl": []})
    board, _ = xat.leaderboard(tg, tsr)
    assert list(board["franchise"]) == ["AA", "CC", "BB"]


def test_ols_r2_perfect_fit_is_one():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(50, 2))
    beta = np.array([1.5, -2.0])
    y = X @ beta + 3.0
    assert xat._ols_r2(X, y) == pytest.approx(1.0, abs=1e-9)


# --------------------------------------------------------- run() / outputs


@pytest.mark.skipif(not TEAM_GAME_CSV.exists(), reason="team_game.csv not built")
def test_run_produces_expected_row_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(xat, "OUT", tmp_path)
    res = xat.run()

    tg = xat.load_team_game()
    n_team_seasons = tg.groupby(["franchise", "season"]).ngroups
    assert len(res["leaderboard"]) == n_team_seasons

    n_eras = len(xat.ERAS)
    assert len(res["persistence_by_era"]) == (n_eras + 1) * len(xat.PERSISTENCE_METRICS)
    n_seasons = tg["season"].nunique()
    assert len(res["persistence_by_season"]) == n_seasons * len(xat.PERSISTENCE_METRICS)

    assert len(res["head_to_head_by_era"]) == (n_eras + 1) * 5  # 5 categories
    n_games = tg["game_id"].nunique()
    per_era_total = res["head_to_head_by_era"][res["head_to_head_by_era"]["era"] != "ALL"]["n_games"].sum()
    assert per_era_total == n_games
    all_total = res["head_to_head_by_era"][res["head_to_head_by_era"]["era"] == "ALL"]["n_games"].sum()
    assert all_total == n_games

    for name in ["persistence_by_era.csv", "persistence_by_season.csv", "persistence_year_to_year.csv",
                 "head_to_head_by_era.csv", "head_to_head_by_season.csv", "head_to_head_ng_by_era.csv",
                 "leaderboard_team_seasons.csv", "leaderboard_top_offenses.csv", "leaderboard_top_defenses.csv",
                 "leaderboard_correlations.csv", "leaderboard_unmatched.csv"]:
        assert (tmp_path / name).exists()

    assert len(res["leaderboard_correlations"]) == n_eras + 1
    assert len(pd.read_csv(tmp_path / "leaderboard_top_offenses.csv")) <= 25
    assert len(pd.read_csv(tmp_path / "leaderboard_top_defenses.csv")) <= 25
