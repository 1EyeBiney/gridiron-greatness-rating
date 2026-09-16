import pandas as pd
import pytest

from era import STRIKE_SEASONS, flag_1987_replacement_games, season_metadata
from models.common import load_games
from standardize import display_scale, zscore_within_season


def test_exactly_42_games_flagged_as_1987_replacement_games():
    games = load_games()
    flags = flag_1987_replacement_games(games)
    assert flags.sum() == 42
    assert set(games.loc[flags, "season"].unique()) == {1987}


def test_flagged_games_are_all_regular_season():
    games = load_games()
    flags = flag_1987_replacement_games(games)
    assert (games.loc[flags, "game_type"] == "REG").all()


def test_season_metadata_flags_strike_seasons_only():
    games = load_games()
    meta = season_metadata(games)
    flagged = set(meta.loc[meta["strike_season"], "season"])
    assert flagged == set(STRIKE_SEASONS)


def test_season_metadata_schedule_length_matches_known_eras():
    games = load_games()
    meta = season_metadata(games).set_index("season")
    assert meta.loc[1975, "schedule_length"] == 14
    assert meta.loc[1985, "schedule_length"] == 16
    assert meta.loc[2023, "schedule_length"] == 17
    assert meta.loc[1982, "schedule_length"] == 9


def test_zscore_within_season_has_mean_zero_sd_one_per_season():
    df = pd.DataFrame(
        {
            "season": [2000, 2000, 2000, 2001, 2001, 2001],
            "massey_rating": [10, 0, -10, 4, 5, 6],
            "bt_rating": [1, 0, -1, 2, 3, 4],
            "bayes_rating": [1, 0, -1, 2, 3, 4],
            "elo_rating": [1, 0, -1, 2, 3, 4],
        }
    )
    out = zscore_within_season(df)
    for season in (2000, 2001):
        sub = out[out["season"] == season]
        assert sub["massey_rating_z"].mean() == pytest.approx(0.0, abs=1e-9)
        assert sub["massey_rating_z"].std(ddof=0) == pytest.approx(1.0, abs=1e-9)


def test_display_scale_clips_to_0_100():
    z = pd.Series([-100.0, -1.0, 0.0, 1.0, 100.0])
    scaled = display_scale(z)
    assert scaled.iloc[0] == 0
    assert scaled.iloc[-1] == 100
    assert scaled.iloc[2] == 50
