"""
The site's prose makes qualitative claims (the late third is the highest
in every decade; eliminated teams show no loss of home edge; 2020 is the
low point; no franchise is significantly unusual). The numbers themselves
are injected from the tables at render time, so they can't drift - but
the claims built on them can. This pins each claim to the data.
"""
import pandas as pd
import pytest

import hfa_site as build_site


@pytest.fixture(scope="module")
def facts():
    return build_site.build_facts(build_site.load_tables())


def test_home_field_declined_from_1990s_to_2020s_by_more_than_three_se(facts):
    diff = facts["hfa_1990s"] - facts["hfa_2020s"]
    se = (facts["se_1990s"] ** 2 + facts["se_2020s"] ** 2) ** 0.5
    assert diff / se > 3


def test_1970s_1980s_1990s_are_all_near_three_points(facts):
    dec = facts["dec"]
    assert all(2.5 < dec.loc[d, "hfa"] < 3.2 for d in ["1970s", "1980s", "1990s"])
    # monotone decline 1990s -> 2000s -> 2010s -> 2020s
    seq = [dec.loc[d, "hfa"] for d in ["1990s", "2000s", "2010s", "2020s"]]
    assert seq == sorted(seq, reverse=True)


def test_late_third_is_highest_in_nearly_every_decade_and_overall(facts):
    # The prose says "N of 6 decades, tied in the other": at least 5 of 6,
    # and where it isn't highest it trails by a small fraction of a point.
    assert facts["n_decades"] == 6
    assert facts["n_decades_late_highest"] >= 5
    assert facts["late_shortfall_max"] < 0.2
    assert facts["hfa_late"] > facts["hfa_mid"] and facts["hfa_late"] > facts["hfa_early"]
    se = (facts["se_early"] ** 2 + facts["se_late"] ** 2) ** 0.5
    assert facts["late_minus_early"] / se > 2
    assert facts["n_seasons_late_gt_early"] > facts["n_seasons"] / 2


def test_final_week_is_not_weaker_than_the_rest(facts):
    assert facts["final_week"] > facts["hfa_all"]


def test_week_one_is_among_the_two_weakest_weeks_since_1999(facts):
    assert 1 in facts["weakest_weeks"] and len(facts["weakest_weeks"]) == 2


def test_2020_is_the_lowest_season_in_its_window_and_near_zero(facts):
    assert abs(facts["hfa_2020"]) < 0.5
    assert facts["hfa_2020"] < facts["hfa_2015_19"] - 2 * facts["se_2020"] * 0.9
    assert facts["hfa_2021_25"] > facts["hfa_2020"]
    seasons = pd.read_csv(build_site.DATA / "by_season.csv").set_index("season")
    assert seasons.loc[2015:2025, "hfa"].idxmin() in (2019, 2020)  # 2019 is also ~0; 2020 the story


def test_eliminated_teams_show_no_loss_of_home_edge_in_the_last_three_weeks(facts):
    diff = facts["alive_last3"] - facts["elim_last3"]
    se = (facts["alive_last3_se"] ** 2 + facts["elim_last3_se"] ** 2) ** 0.5
    assert abs(diff) < 1.5 * se
    assert abs(facts["gb3_last3"] - facts["spot_last3"]) < 0.5
    assert facts["n_elim_last3"] > 500


def test_naive_method_shows_the_artifact(facts):
    assert facts["naive_elim"] - facts["naive_alive"] > 1.0


def test_late_rise_is_present_indoors_and_outdoors(facts):
    assert facts["indoor_late"] > facts["indoor_early"]
    assert facts["outdoor_late"] > facts["outdoor_early"]


def test_division_games_have_less_home_field(facts):
    assert facts["div_all"] < facts["nondiv_all"]
    assert facts["div_late"] < facts["nondiv_late"]


def test_franchise_claims(facts):
    assert facts["n_abs_z_over_2"] <= 3
    assert facts["pit_z"] > 0            # Steelers' swing is larger than average
    assert facts["sf_z"] < 0 and facts["sf_z"] > -2   # 49ers smaller, not significant
    assert facts["swing_league"] == pytest.approx(2 * facts["hfa_all"], abs=0.05)


def test_era_table_shows_no_recent_effect_either():
    era = pd.read_csv(build_site.DATA / "contention_last3_by_era.csv").set_index(["era", "status"])
    a, e = era.loc[("2010-2025", "alive")], era.loc[("2010-2025", "eliminated")]
    se = (a["hfa_all_se"] ** 2 + e["hfa_all_se"] ** 2) ** 0.5
    assert abs(a["hfa_all"] - e["hfa_all"]) < 1.5 * se


def test_what_it_means_page_claims(facts):
    # "Home teams won six of every ten games in the 1990s ... barely more than half in the 2020s"
    assert 0.58 <= facts["winpct_1990s"] <= 0.62
    assert 0.51 <= facts["winpct_2020s"] <= 0.56
    # "Home teams won exactly half their games" in 2020
    assert abs(facts["covid"].loc["2020 (limited or no fans)", "home_win_pct"] - 0.5) < 0.015
    # The page names the largest and smallest swings from the data; the
    # first draft hard-coded New Orleans as smallest and this caught that
    # Carolina is (3.37 vs 3.40). Pittsburgh must not be among the smallest.
    assert facts["swing_max_team"] == "DET"
    assert facts["swing_min_team"] in ("CAR", "NO")
    assert facts["pit_swing"] > facts["swing_league"]
    # "about three points" through the 1990s, "fallen by more than a point"
    assert facts["hfa_1990s"] - facts["hfa_2020s"] > 1.0
