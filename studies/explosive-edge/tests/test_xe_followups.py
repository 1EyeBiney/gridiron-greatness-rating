"""Tests for xe_analysis_followups.py: synthetic checks on the
decomposition math, drive-position bucketing, the QB join, and the Super
Bowl rank sign convention, plus structural checks on the real generated
outputs."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import xe_analysis_followups as xf

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "processed"


# ------------------------------------------------------------ 1: decomposition


def test_decomposition_recovers_planted_rate_and_mix_effects():
    # Plant a pass rate that falls (mix effect should be negative-ish, since
    # rushes explode less than passes here) and a within-type rate change
    # for both pass and rush. Use round numbers we can hand-verify.
    by_season = pd.DataFrame([
        {"season": 2018, "pass_rate": 0.60, "explosive_pass_rate_per_dropback": 0.10,
         "explosive_rush_rate_per_attempt": 0.10},
        {"season": 2025, "pass_rate": 0.50, "explosive_pass_rate_per_dropback": 0.08,
         "explosive_rush_rate_per_attempt": 0.10},
    ])
    out = xf.pass_run_decomposition(by_season, y0=2018, y1=2025).iloc[0]

    tot0 = 0.60 * 0.10 + 0.40 * 0.10  # = 0.10
    tot1 = 0.50 * 0.08 + 0.50 * 0.10  # = 0.09
    assert out["total_rate_per_play_from"] == pytest.approx(tot0)
    assert out["total_rate_per_play_to"] == pytest.approx(tot1)
    assert out["total_change"] == pytest.approx(tot1 - tot0)

    # Rush rate never changes (0.10 -> 0.10), so ALL of the change must be
    # attributed to the pass rate falling and/or the pass rate itself
    # falling -- here rate_effect comes entirely from the pass rate change
    # (rush contributes 0), and mix_effect comes from the pass/rush GAP
    # (which is initially 0, ends at -0.02) times the change in pass rate.
    pr_bar = (0.60 + 0.50) / 2
    rp_bar_minus_rr_bar = ((0.10 - 0.10) + (0.08 - 0.10)) / 2
    expected_mix = (0.50 - 0.60) * rp_bar_minus_rr_bar
    expected_rate = pr_bar * (0.08 - 0.10) + (1 - pr_bar) * (0.10 - 0.10)
    assert out["mix_effect_pass_rate"] == pytest.approx(expected_mix)
    assert out["rate_effect_within_type"] == pytest.approx(expected_rate)
    # The two effects must sum exactly to the total change.
    assert out["sum_check"] == pytest.approx(out["total_change"])
    assert (out["mix_effect_pass_rate"] + out["rate_effect_within_type"]) == pytest.approx(out["total_change"])


def test_decomposition_all_rate_effect_when_pass_rate_constant():
    # Pass rate held fixed -> mix effect must be exactly zero, entire
    # change is the rate effect.
    by_season = pd.DataFrame([
        {"season": 2018, "pass_rate": 0.55, "explosive_pass_rate_per_dropback": 0.09,
         "explosive_rush_rate_per_attempt": 0.12},
        {"season": 2025, "pass_rate": 0.55, "explosive_pass_rate_per_dropback": 0.08,
         "explosive_rush_rate_per_attempt": 0.11},
    ])
    out = xf.pass_run_decomposition(by_season, y0=2018, y1=2025).iloc[0]
    assert out["mix_effect_pass_rate"] == pytest.approx(0.0)
    assert out["rate_effect_within_type"] == pytest.approx(out["total_change"])
    assert out["share_of_change_that_is_rate_effect"] == pytest.approx(1.0)


# ------------------------------------------------------------ 2: drive-position bucketing


def _play(game_id, posteam, drive, order, scrim=True, drive_col=None):
    return {
        "game_id": game_id, "posteam": posteam, "drive": drive if drive_col is None else drive_col,
        "order_sequence": order, "play_id": order,
    }


def test_drive_play_number_orders_within_drive_and_restarts_per_drive():
    # Two drives for the same team in the same game: 3 plays then 2 plays.
    # Also include a non-scrimmage play (should not get a play number) and
    # a play with a missing drive (should be dropped).
    pbp = pd.DataFrame([
        {"game_id": "g1", "posteam": "AA", "drive": 1, "order_sequence": 30, "play_id": 30},
        {"game_id": "g1", "posteam": "AA", "drive": 1, "order_sequence": 10, "play_id": 10},
        {"game_id": "g1", "posteam": "AA", "drive": 1, "order_sequence": 20, "play_id": 20},
        {"game_id": "g1", "posteam": "AA", "drive": 2, "order_sequence": 50, "play_id": 50},
        {"game_id": "g1", "posteam": "AA", "drive": 2, "order_sequence": 40, "play_id": 40},
        {"game_id": "g1", "posteam": "AA", "drive": np.nan, "order_sequence": 60, "play_id": 60},
    ])
    scrim = pd.Series([True, True, True, True, True, True], index=pbp.index)
    n = xf._drive_play_number(pbp, scrim)
    # Sorted by order_sequence within (game, team, drive): 10,20,30 -> 1,2,3
    assert n.loc[pbp["order_sequence"] == 10].iloc[0] == 1
    assert n.loc[pbp["order_sequence"] == 20].iloc[0] == 2
    assert n.loc[pbp["order_sequence"] == 30].iloc[0] == 3
    # Second drive restarts numbering at 1.
    assert n.loc[pbp["order_sequence"] == 40].iloc[0] == 1
    assert n.loc[pbp["order_sequence"] == 50].iloc[0] == 2
    # Missing-drive row has no play number.
    assert pd.isna(n.loc[pbp["order_sequence"] == 60].iloc[0])


def test_bucket4_and_bucket8_edges():
    n = pd.Series([1, 2, 3, 4, 7, 8, 9])
    b4 = xf._bucket4(n)
    assert list(b4) == ["1", "2", "3", "4+", "4+", "4+", "4+"]
    b8 = xf._bucket8(n)
    assert list(b8) == ["1", "2", "3", "4", "7", "8+", "8+"]


# ------------------------------------------------------------ 3: QB join


def test_qb_join_attaches_the_starter_and_uses_pass_only_counts():
    # Two REG games for team AA: same QB starts both.
    team_game = pd.DataFrame([
        {"game_id": "g1", "season": 2020, "week": 1, "game_type": "REG", "team": "AA", "franchise": "AA",
         "dropbacks": 30, "explosive_20_10": 3},
        {"game_id": "g2", "season": 2020, "week": 2, "game_type": "REG", "team": "AA", "franchise": "AA",
         "dropbacks": 40, "explosive_20_10": 5},
        # a POST game should be excluded by build_qb_team_game's REG filter
        {"game_id": "g3", "season": 2020, "week": 20, "game_type": "POST", "team": "AA", "franchise": "AA",
         "dropbacks": 999, "explosive_20_10": 999},
    ])
    games = pd.DataFrame([
        {"game_id": "g1", "season": 2020, "week": 1, "game_type": "REG",
         "home_team": "AA", "away_team": "BB", "home_qb_id": "QB1", "away_qb_id": "QBX",
         "home_qb_name": "Quinn One", "away_qb_name": "Quinn X"},
        {"game_id": "g2", "season": 2020, "week": 2, "game_type": "REG",
         "home_team": "BB", "away_team": "AA", "home_qb_id": "QBY", "away_qb_id": "QB1",
         "home_qb_name": "Quinn Y", "away_qb_name": "Quinn One"},
    ])
    team_pass = pd.DataFrame([
        {"season": 2020, "game_id": "g1", "franchise": "AA", "explosive_pass": 2, "passer_dropbacks": 30},
        {"season": 2020, "game_id": "g2", "franchise": "AA", "explosive_pass": 4, "passer_dropbacks": 40},
    ])
    qtg = xf.build_qb_team_game(team_game, games, team_pass)
    aa_rows = qtg[qtg["team"] == "AA"]
    assert set(aa_rows["qb_id"]) == {"QB1"}
    assert len(aa_rows) == 2  # POST game dropped
    # the rate is explosive COMPLETIONS per dropback, not the mixed pass/rush count
    assert aa_rows["explosive_pass"].tolist() == [2, 4]
    assert aa_rows["explosive_pass_rate"].tolist() == pytest.approx([2 / 30, 4 / 40])


def test_qb_join_matches_on_franchise_not_team_code():
    # The schedule file says STL / SD / OAK; the play-by-play (and team_game) say LA / LAC / LV.
    import xe_metrics as xm
    rams = xm.to_franchise(pd.Series(["LA"]), pd.Series([2001])).iloc[0]     # the franchise id team_game carries
    team_game = pd.DataFrame([
        {"game_id": "2001_01_STL_PHI", "season": 2001, "week": 1, "game_type": "REG", "team": "LA",
         "franchise": rams, "dropbacks": 30, "explosive_20_10": 3},
    ])
    games = pd.DataFrame([
        {"game_id": "2001_01_STL_PHI", "season": 2001, "week": 1, "game_type": "REG",
         "home_team": "PHI", "away_team": "STL", "home_qb_id": "QBP", "away_qb_id": "QBW",
         "home_qb_name": "Donovan", "away_qb_name": "Kurt"},
    ])
    qtg = xf.build_qb_team_game(team_game, games)
    assert qtg["qb_id"].tolist() == ["QBW"]


def test_passer_plays_credits_the_passer_on_the_field_not_the_starter():
    pbp = pd.DataFrame([
        # starter throws a 25-yard completion (air 22), then is sacked; backup throws 30-yard screen (air -2);
        # a running back's 15-yard run; starter scrambles 12 yards
        {"game_id": "g", "season": 2020, "season_type": "REG", "game_type": "REG", "posteam": "AA",
         "play_type": "pass", "play": 1, "qb_kneel": 0, "qb_spike": 0, "yards_gained": 25, "qb_dropback": 1,
         "qb_scramble": 0, "sack": 0, "complete_pass": 1, "rush_attempt": 0, "air_yards": 22,
         "passer_player_id": "S", "passer_player_name": "Starter", "rusher_player_id": None, "rusher_player_name": None},
        {"game_id": "g", "season": 2020, "season_type": "REG", "game_type": "REG", "posteam": "AA",
         "play_type": "pass", "play": 1, "qb_kneel": 0, "qb_spike": 0, "yards_gained": -7, "qb_dropback": 1,
         "qb_scramble": 0, "sack": 1, "complete_pass": 0, "rush_attempt": 0, "air_yards": None,
         "passer_player_id": "S", "passer_player_name": "Starter", "rusher_player_id": None, "rusher_player_name": None},
        {"game_id": "g", "season": 2020, "season_type": "REG", "game_type": "REG", "posteam": "AA",
         "play_type": "pass", "play": 1, "qb_kneel": 0, "qb_spike": 0, "yards_gained": 30, "qb_dropback": 1,
         "qb_scramble": 0, "sack": 0, "complete_pass": 1, "rush_attempt": 0, "air_yards": -2,
         "passer_player_id": "B", "passer_player_name": "Backup", "rusher_player_id": None, "rusher_player_name": None},
        {"game_id": "g", "season": 2020, "season_type": "REG", "game_type": "REG", "posteam": "AA",
         "play_type": "run", "play": 1, "qb_kneel": 0, "qb_spike": 0, "yards_gained": 15, "qb_dropback": 0,
         "qb_scramble": 0, "sack": 0, "complete_pass": 0, "rush_attempt": 1, "air_yards": None,
         "passer_player_id": None, "passer_player_name": None, "rusher_player_id": "RB", "rusher_player_name": "Back"},
        {"game_id": "g", "season": 2020, "season_type": "REG", "game_type": "REG", "posteam": "AA",
         "play_type": "run", "play": 1, "qb_kneel": 0, "qb_spike": 0, "yards_gained": 12, "qb_dropback": 1,
         "qb_scramble": 1, "sack": 0, "complete_pass": 0, "rush_attempt": 1, "air_yards": None,
         "passer_player_id": None, "passer_player_name": None, "rusher_player_id": "S", "rusher_player_name": "Starter"},
    ])
    out = xf.passer_plays(pbp).set_index("qb_id")
    s, b = out.loc["S"], out.loc["B"]
    assert s["dropbacks"] == 3 and s["explosive_pass"] == 1 and s["explosive_pass_air"] == 1
    assert s["qb_rushes"] == 1 and s["explosive_rush"] == 1          # the scramble, not the RB's run
    assert b["dropbacks"] == 1 and b["explosive_pass"] == 1 and b["explosive_pass_air"] == 0
    assert "RB" not in out.index                                      # a back is not a quarterback
    team = xf.team_pass_from_passer_plays(out.reset_index())
    assert team["explosive_pass"].tolist() == [2]                    # the RB's 15-yard run is not a pass
    career = xf.qb_career_explosive_leaders(out.reset_index(), min_dropbacks=1, top=5).set_index("qb_name")
    assert career.loc["Starter", "rate"] == pytest.approx(1 / 3)
    assert career.loc["Backup", "air_share"] == 0


def test_reliability_decomposition_recovers_a_pure_noise_world():
    # Fixed league-average rates, Poisson counts for and against: the true variance should be ~0
    rng = np.random.default_rng(0)
    rows = []
    for season in (2018, 2019, 2020, 2021, 2022, 2023):
        for f in range(32):
            for week in range(1, 17):
                ef, ea = rng.poisson(6.0), rng.poisson(6.0)
                tf, ta = rng.poisson(1.3), rng.poisson(1.3)
                rows.append({"game_id": f"{season}_{week}_{f}", "season": season, "week": week, "game_type": "REG",
                             "franchise": f"T{f}", "plays": 60, "explosive_20_10": ef, "explosive_20_10_diff": ef - ea,
                             "turnovers": tf, "turnovers_diff": tf - ta, "margin": 0, "yards": 300})
    out = xf.reliability_decomposition(pd.DataFrame(rows)).set_index(["era", "metric"])
    for metric in ("explosive_diff_per_game", "turnover_diff_per_game"):
        r = out.loc[("2017-2025", metric)]
        assert r["implied_reliability"] < 0.15                        # nothing repeatable to find
        assert abs(r["observed_split_half_r"]) < 0.15


def test_qb_join_covers_every_real_regular_season_team_game():
    if not xf.GAMES_CSV.exists() or not (OUT / "team_game.csv").exists():
        pytest.skip("real inputs not present")
    qtg = xf.build_qb_team_game(xf.load_team_game(), xf.load_games())
    assert qtg["qb_id"].isna().sum() == 0          # v1.0 dropped 894 LA / LAC / LV team-games here


def test_qb_join_leaves_qb_id_nan_when_no_games_match():
    team_game = pd.DataFrame([
        {"game_id": "g_unmatched", "season": 2020, "week": 1, "game_type": "REG", "team": "AA", "franchise": "AA",
         "dropbacks": 30, "explosive_20_10": 3},
    ])
    games = pd.DataFrame([], columns=["game_id", "season", "week", "game_type", "home_team", "away_team",
                                       "home_qb_id", "away_qb_id", "home_qb_name", "away_qb_name"])
    qtg = xf.build_qb_team_game(team_game, games)
    assert qtg["qb_id"].isna().all()


# ------------------------------------------------------------ 4: Super Bowl rank sign convention


def test_super_bowl_rank_sign_convention_lower_turnover_diff_ranks_better():
    # Three teams, season 2020: team A has the LOWEST (best) turnover_diff_pg
    # and should rank 1st on turnovers; team C has the highest (worst) and
    # should rank last. Explosive diff ranks descending (higher = rank 1).
    team_season = pd.DataFrame([
        {"franchise": "A", "season": 2020, "explosive_diff_pg": 0.5, "turnover_diff_pg": -1.0},
        {"franchise": "B", "season": 2020, "explosive_diff_pg": 1.0, "turnover_diff_pg": 0.0},
        {"franchise": "C", "season": 2020, "explosive_diff_pg": -0.5, "turnover_diff_pg": 1.0},
    ])
    team_game = pd.DataFrame([
        {"game_id": "sb1", "season": 2020, "week": 22, "game_type": "POST",
         "franchise": "A", "win": 1.0},
    ])
    out = xf.super_bowl_ranks(team_game, team_season)
    champ_row = out[out["champion"] == "A"].iloc[0]
    # Team A has the lowest (best) turnover_diff_pg (-1.0) -> rank 1.
    assert champ_row["tod_rank"] == 1
    # Team A has the middle explosive_diff_pg (0.5, vs B's 1.0 and C's -0.5)
    # -> rank 2 (descending: B=1, A=2, C=3).
    assert champ_row["epd_rank"] == 2

    # Sanity: team C (worst turnover_diff_pg) should rank last among the
    # three on turnovers, confirming the direction is not accidentally
    # flipped by re-deriving the full ranking from the same table.
    ts = team_season.copy()
    ts["tod_rank"] = ts.groupby("season")["turnover_diff_pg"].rank(ascending=True, method="min")
    assert ts.set_index("franchise").loc["C", "tod_rank"] == 3
    assert ts.set_index("franchise").loc["A", "tod_rank"] == 1


# ------------------------------------------------------------ 5: structural, real outputs


REQUIRED_FILES = [
    "competitive_time_logit_by_era.csv",
    "playoff_prediction.csv",
    "playoff_head_to_head.csv",
    "super_bowl_ranks.csv",
    "qb_continuity_persistence.csv",
    "qb_career_explosive_leaders.csv",
    "qb_season_explosive_leaders.csv",
    "qb_join_coverage.csv",
    "reliability_decomposition.csv",
    "pass_run_explosives_by_season.csv",
    "pass_run_decomposition.csv",
    "drive_position_explosive_rate.csv",
    "garbage_share_by_season.csv",
    "defensive_play_by_drive_position.csv",
    "drive_outcomes_by_era.csv",
]


@pytest.fixture(scope="module")
def real_tables():
    missing = [f for f in REQUIRED_FILES if not (OUT / f).exists()]
    if missing:
        pytest.skip(f"data/processed missing {missing}; run xe_analysis_followups.run() first")
    return {f: pd.read_csv(OUT / f) for f in REQUIRED_FILES}


def test_all_output_files_exist(real_tables):
    for f in REQUIRED_FILES:
        assert f in real_tables


def test_competitive_time_by_era_has_all_eras_and_pooled(real_tables):
    df = real_tables["competitive_time_logit_by_era.csv"]
    eras = set(df["era"])
    assert {"1999-2007", "2008-2016", "2017-2025", "ALL"}.issubset(eras)
    key_cols = ["ng_b_epd", "ng_b_tod", "all_b_epd", "all_b_tod",
                "ng_epd_minus_tod_gap", "all_epd_minus_tod_gap"]
    assert not df[key_cols].isna().any().any()


def test_playoff_prediction_has_pooled_and_era_rows(real_tables):
    df = real_tables["playoff_prediction.csv"]
    assert "ALL" in set(df["era"])
    assert not df[["b_epd", "se_epd", "b_tod", "se_tod", "n_games"]].isna().any().any()
    assert (df["n_games"] > 0).all()


def test_playoff_head_to_head_categories_present(real_tables):
    df = real_tables["playoff_head_to_head.csv"]
    assert set(df["category"]) == {"won_both", "won_explosive_lost_turnover", "explosive_only",
                                    "turnover_only", "both_even"}
    assert (df["n_games"] >= 0).all()


def test_super_bowl_ranks_covers_expected_span_and_has_median_summary(real_tables):
    df = real_tables["super_bowl_ranks.csv"]
    per_champ = df[df["season"] != "median"]
    assert len(per_champ) >= 20  # most of 1999-2025 has a resolvable champion
    assert not per_champ[["epd_rank", "tod_rank"]].isna().any().any()
    assert (df["season"] == "median").sum() == 1


def test_qb_continuity_has_both_groups_with_positive_n(real_tables):
    df = real_tables["qb_continuity_persistence.csv"]
    assert set(df["qb_continuity"]) == {"same_qb", "changed_qb"}
    assert (df["n_team_seasons"] > 0).all()


def test_qb_career_leaders_meet_minimum_dropbacks(real_tables):
    df = real_tables["qb_career_explosive_leaders.csv"]
    assert len(df) > 0
    assert (df["dropbacks"] >= 1500).all()
    assert not df[["rate"]].isna().any().any()
    # sorted descending by rate
    assert (df["rate"].diff().dropna() <= 1e-9).all()
    # pass-only measure: explosive completions cannot exceed dropbacks, and air share is a share
    assert (df["explosive_pass"] <= df["dropbacks"]).all()
    assert df["air_share"].between(0, 1).all()
    assert (df["rate"] < 0.25).all()


def test_qb_join_coverage_is_complete(real_tables):
    df = real_tables["qb_join_coverage.csv"].iloc[0]
    assert df["unmatched"] == 0 and df["matched"] == df["team_games"]


def test_reliability_table_has_both_metrics_for_every_era(real_tables):
    df = real_tables["reliability_decomposition.csv"]
    assert set(df["metric"]) == {"explosive_diff_per_game", "turnover_diff_per_game"}
    assert df["era"].nunique() == 3
    assert df["implied_reliability"].between(0, 1).all()


def test_pass_run_by_season_no_nan_in_key_numeric_columns(real_tables):
    df = real_tables["pass_run_explosives_by_season.csv"]
    key_cols = ["pass_rate", "explosive_pass_rate_per_dropback", "explosive_rush_rate_per_attempt"]
    assert not df[key_cols].isna().any().any()
    assert df["season"].min() <= 2000 and df["season"].max() >= 2024


def test_drive_position_table_has_both_eras_and_all_buckets(real_tables):
    df = real_tables["drive_position_explosive_rate.csv"]
    assert set(df["era"]) == {"2010-2017", "2018-2025"}
    assert set(df["bucket"]) == {"1", "2", "3", "4+"}
    assert not df["explosive_rate"].isna().any()


def test_defensive_play_by_drive_position_has_all_eras_and_buckets(real_tables):
    df = real_tables["defensive_play_by_drive_position.csv"]
    assert set(df["era"]) == {"1999-2007", "2008-2016", "2017-2025"}
    assert set(df["bucket"]) == {str(i) for i in range(1, 8)} | {"8+"}
    assert not df["def_play_rate"].isna().any()
    assert (df["plays"] > 0).all()


def test_drive_outcomes_by_era_no_nan(real_tables):
    df = real_tables["drive_outcomes_by_era.csv"]
    assert len(df) == 3
    assert not df[["p_at_least_one_def_play_per_drive", "points_per_drive", "plays_per_drive"]].isna().any().any()
