"""Unit tests on a synthetic play-by-play fixture (known-by-hand answers),
plus structural checks on the real 1999-2025 aggregate."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import xe_ingest
import xe_metrics

REPO = Path(__file__).resolve().parents[1]
MAIN = REPO.parents[1]
TEAM_GAME_CSV = REPO / "data" / "processed" / "team_game.csv"
PBP_2023 = xe_ingest.RAW / "play_by_play_2023.parquet"


# ------------------------------------------------------------- the fixture
#
# One game, two teams (TA home, TB away), season 2021 week 1, REG.
# TA: 25-yard pass (explosive, garbage-time wp=0.97), 8-yard run (not
#     explosive), 12-yard run (explosive 20/10 only), a pass intercepted,
#     a sack, a penalty no-play, a kneel.
# TB: a punt return where TB fumbles and loses it to TA, a 5-yard pass, a
#     -2-yard run (negative/TFL-free), a 15-yard run (explosive 20/10 and
#     25/15), a -3-yard run stuffed for a tackle for loss.
# All non-INT plays sit at wp=0.5 (comfortably in [0.05, 0.95]); the 25-yard
# pass sits at wp=0.97 (garbage time) so the _ng counters can be checked
# against the plain ones.


def _row(**kw):
    base = dict(
        game_id="TEST_2021_01_TA_TB", season=2021, week=1, game_type="REG",
        home_team="TA", away_team="TB", home_score=20, away_score=10,
        interception=0, fumble_lost=0, sack=0, tackled_for_loss=0,
        qb_dropback=0, qb_kneel=0, qb_spike=0, play=1, wp=0.5,
    )
    base.update(kw)
    return base


PLAYS = [
    _row(posteam="TA", defteam="TB", play_type="pass", yards_gained=25, epa=1.0, wp=0.97,
         qb_dropback=1, drive=1, drive_play_count=4, drive_time_of_possession="2:10"),
    _row(posteam="TA", defteam="TB", play_type="run", yards_gained=8, epa=0.3,
         drive=1, drive_play_count=4, drive_time_of_possession="2:10"),
    _row(posteam="TA", defteam="TB", play_type="run", yards_gained=12, epa=0.5,
         drive=1, drive_play_count=4, drive_time_of_possession="2:10"),
    _row(posteam="TA", defteam="TB", play_type="pass", yards_gained=-3, epa=-2.0,
         interception=1, qb_dropback=1, drive=1, drive_play_count=4, drive_time_of_possession="2:10"),
    # TB punts (posteam=TB, the punting team); TA returns and fumbles it
    # away, recovered by TB. fumbled_1_team=TA records who actually lost
    # the ball - the turnover must be charged to TA (the returner), not to
    # posteam=TB (the punter), and TB's defense/special-teams gets credit
    # for forcing it.
    _row(posteam="TB", defteam="TA", play_type="punt", yards_gained=5, epa=-0.5,
         fumble_lost=1, fumbled_1_team="TA", drive=2, drive_play_count=1, drive_time_of_possession="0:08"),
    _row(posteam="TA", defteam="TB", play_type="pass", yards_gained=-7, epa=-1.5,
         sack=1, qb_dropback=1, drive=4, drive_play_count=2, drive_time_of_possession="0:45"),
    _row(posteam="TA", defteam="TB", play_type="no_play", yards_gained=0, epa=0.0, play=0,
         drive=4, drive_play_count=2, drive_time_of_possession="0:45"),
    _row(posteam="TA", defteam="TB", play_type="run", yards_gained=-1, epa=-0.2, qb_kneel=1,
         drive=5, drive_play_count=1, drive_time_of_possession="0:40"),
    _row(posteam="TB", defteam="TA", play_type="pass", yards_gained=5, epa=0.2, qb_dropback=1,
         drive=6, drive_play_count=4, drive_time_of_possession="1:30"),
    _row(posteam="TB", defteam="TA", play_type="run", yards_gained=-2, epa=-0.3,
         drive=6, drive_play_count=4, drive_time_of_possession="1:30"),
    _row(posteam="TB", defteam="TA", play_type="run", yards_gained=15, epa=0.6,
         drive=6, drive_play_count=4, drive_time_of_possession="1:30"),
    _row(posteam="TB", defteam="TA", play_type="run", yards_gained=-3, epa=-0.4, tackled_for_loss=1,
         drive=6, drive_play_count=4, drive_time_of_possession="1:30"),
]


@pytest.fixture(scope="module")
def tg():
    pbp = pd.DataFrame(PLAYS)
    out = xe_metrics.team_game(pbp)
    return out.set_index("team")


# TA's turnovers include BOTH the interception it threw (play 4) and the
# punt-return fumble it lost (play 5, charged via fumbled_1_team, not to
# punter TB). TB's def_plays_made is 3: the sack (play 6), forcing TA's
# interception (play 4), AND recovering/forcing TA's punt-return fumble
# (play 5) - three distinct plays, no double-counting. TA's def_plays_made
# is 1: only the tackle for loss on TB (play 12); TA gets no defensive
# credit for play 5 even though it's "defteam" there, since TA is the side
# that fumbled, not the side that forced/recovered it.
EXPECTED = {
    "TA": dict(
        plays=5, pass_plays=3, rush_plays=2, dropbacks=3,
        turnovers=2, turnovers_ng=2, turnovers_scrimmage=1, turnovers_scrimmage_ng=1,
        sacks_taken=1, negative_plays=2, yards=35, epa_total=pytest.approx(-1.7),
        explosive_20_10=2, explosive_20_10_ng=1,
        explosive_25_15=1, explosive_25_15_ng=0,
        explosive_20_20=1, explosive_20_20_ng=0,
        explosive_epa2=0, explosive_epa2_ng=0,
        def_plays_made=1, drives=3, drive_plays_total=7, drive_seconds_total=215,
        points_for=20, points_against=10, margin=10, win=1.0, is_home=True,
    ),
    "TB": dict(
        plays=4, pass_plays=1, rush_plays=3, dropbacks=1,
        turnovers=0, turnovers_ng=0, turnovers_scrimmage=0, turnovers_scrimmage_ng=0,
        sacks_taken=0, negative_plays=2, yards=15, epa_total=pytest.approx(0.1),
        explosive_20_10=1, explosive_20_10_ng=1,
        explosive_25_15=1, explosive_25_15_ng=1,
        explosive_20_20=0, explosive_20_20_ng=0,
        explosive_epa2=0, explosive_epa2_ng=0,
        def_plays_made=3, drives=2, drive_plays_total=5, drive_seconds_total=98,
        points_for=10, points_against=20, margin=-10, win=0.0, is_home=False,
    ),
}


@pytest.mark.parametrize("team", ["TA", "TB"])
def test_synthetic_counters_match_hand_computation(tg, team):
    row = tg.loc[team]
    for col, expected in EXPECTED[team].items():
        assert row[col] == expected, f"{team}.{col}: got {row[col]!r}, expected {expected!r}"


def test_two_rows_one_per_team(tg):
    assert set(tg.index) == {"TA", "TB"}
    assert len(tg) == 2


DIFF_COLS = [
    "explosive_20_10", "explosive_20_10_ng", "explosive_25_15", "explosive_25_15_ng",
    "explosive_20_20", "explosive_20_20_ng", "explosive_epa2", "explosive_epa2_ng",
    "turnovers", "turnovers_ng", "turnovers_scrimmage", "turnovers_scrimmage_ng", "yards",
]


@pytest.mark.parametrize("col", DIFF_COLS)
def test_differentials_are_antisymmetric(tg, col):
    diff_col = f"{col}_diff"
    assert tg.loc["TA", diff_col] == -tg.loc["TB", diff_col]


def test_yards_diff_matches_hand_computation(tg):
    assert tg.loc["TA", "yards_diff"] == 20
    assert tg.loc["TB", "yards_diff"] == -20


def test_franchise_of_untracked_codes_is_itself(tg):
    assert tg.loc["TA", "franchise"] == "TA"
    assert tg.loc["TA", "opp_franchise"] == "TB"


def test_punt_return_fumble_charged_to_returner_not_punter(tg):
    """Play 5 has posteam=TB (the punting team) but fumbled_1_team=TA (the
    returner who actually lost it). The turnover must land on TA, not on
    posteam TB, and TB's defense/special-teams gets the forced-turnover
    credit even though TA (not TB) is `defteam` on that play row."""
    assert tg.loc["TA", "turnovers"] >= 1  # includes the interception too (play 4)
    assert tg.loc["TB", "turnovers"] == 0
    assert tg.loc["TB", "def_plays_made"] == 3  # sack + 2 forced turnovers (INT and the punt fumble)
    assert tg.loc["TA", "def_plays_made"] == 1  # only the TFL; no credit for fumbling it away


# ---------------------------------------------------------------- crosswalk


def test_crosswalk_maps_stl_2005_to_lar_and_leaves_kc_alone():
    codes = pd.Series(["STL", "KC"])
    seasons = pd.Series([2005, 2005])
    out = xe_metrics.to_franchise(codes, seasons)
    assert out.iloc[0] == "LAR"
    assert out.iloc[1] == "KC"


@pytest.mark.skipif(not PBP_2023.exists(), reason="run xe_ingest.py first")
def test_2023_punt_fumbles_are_fully_and_correctly_charged():
    """Every punt row with fumble_lost==1 must end up charged to SOME team
    (via fumbled_1_team, falling back to posteam only when that's null),
    and per the coordinator's own 2023 check, none of them should equal
    posteam == fumbled_1_team (the punting team is never the team that
    fumbled on a punt)."""
    pbp = xe_ingest.load_season(2023)
    punts = pbp[pbp["play_type"] == "punt"]
    fumbled = punts[punts["fumble_lost"] == 1]
    assert len(fumbled) > 0
    fumbled_1_team = fumbled["fumbled_1_team"]
    charged_team = fumbled_1_team.where(fumbled_1_team.notna(), fumbled["posteam"])
    assert charged_team.notna().sum() == len(fumbled)
    assert (fumbled_1_team == fumbled["posteam"]).sum() == 0


# ------------------------------------------------------------- real table


needs_real_data = pytest.mark.skipif(not TEAM_GAME_CSV.exists(), reason="run xe_metrics.py to build team_game.csv first")


@pytest.fixture(scope="module")
def real_team_game():
    return pd.read_csv(TEAM_GAME_CSV)


@needs_real_data
def test_every_regular_season_game_has_two_rows_and_antisymmetric_margins(real_team_game):
    reg = real_team_game[real_team_game["game_type"] == "REG"]
    counts = reg.groupby("game_id").size()
    assert (counts == 2).all(), counts[counts != 2]
    for game_id, gg in reg.groupby("game_id"):
        margins = gg["margin"].to_numpy()
        assert margins[0] == -margins[1]


# A handful of real REG games are simply absent from nflverse's
# play_by_play release entirely (zero rows for that game_id, confirmed
# against nflverse's own games.csv game_id list, not a bug in our
# aggregation): 1999 week 1 BAL@STL, 2000 week 3 SD@KC, 2000 week 6 BUF@MIA.
# These three seasons are allowed to be one game short of the main repo's
# games.csv count; every other season must match exactly.
KNOWN_PBP_GAPS_BY_SEASON = {1999: 1, 2000: 2}


@needs_real_data
def test_games_per_season_matches_main_repo_games_csv(real_team_game):
    reg = real_team_game[real_team_game["game_type"] == "REG"]
    ours = (reg.groupby("season").size() / 2).astype(int)

    main_games = pd.read_csv(MAIN / "data" / "processed" / "games.csv")
    main_reg = main_games[(main_games["game_type"] == "REG") & (main_games["season"] >= 1999)]
    theirs = main_reg.groupby("season").size()

    for season in theirs.index:
        if season == 2026:
            continue  # in-progress season may be absent from our pbp aggregate
        if season not in ours.index:
            continue
        expected = theirs[season] - KNOWN_PBP_GAPS_BY_SEASON.get(season, 0)
        assert ours[season] == expected, f"season {season}: ours={ours[season]} theirs={theirs[season]}"
