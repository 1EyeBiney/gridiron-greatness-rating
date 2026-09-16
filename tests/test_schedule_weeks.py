import pandas as pd

from models.common import load_games, season_games
from schedule_weeks import assign_week_index


def test_1999_plus_uses_source_week_column_order_preserved():
    games = load_games()
    g = season_games(games, 2023)
    idx = assign_week_index(g)
    # nflverse week 1 games should map to index 1, week 19 (WC) to a later
    # index than every regular-season week.
    reg_max_idx = idx[g["game_type"] == "REG"].max()
    playoff_min_idx = idx[g["game_type"] != "REG"].min()
    assert playoff_min_idx > reg_max_idx
    assert idx.min() == 1


def test_pre_1999_derives_monotonic_weeks_from_date_gaps():
    games = load_games()
    g = season_games(games, 1985)
    idx = assign_week_index(g)
    assert idx.min() == 1
    # every game's index should be non-decreasing in date order
    order = pd.to_datetime(g["date"]).argsort()
    assert (idx.iloc[order].diff().fillna(0) >= 0).all()


def test_pre_1999_week_index_never_decreases_with_date():
    games = load_games()
    g = season_games(games, 1970)
    dates = pd.to_datetime(g["date"])
    idx = assign_week_index(g)
    combined = pd.DataFrame({"date": dates, "idx": idx}).sort_values("date")
    assert combined["idx"].is_monotonic_increasing
