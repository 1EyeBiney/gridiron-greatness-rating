"""
Pins the qualitative claims made in the Findings and What It Means prose
to the tables. Numbers in the prose are injected at render time and can't
drift; the claims built on them can, so each one is asserted here.
"""
import pytest

import xe_site


@pytest.fixture(scope="module")
def facts():
    return xe_site.build_facts(xe_site.load_tables())


def test_turnovers_predict_the_winner_better_in_every_era(facts):
    for era in facts["eras"]:
        s = facts["shift_by_era"][era]
        assert s["tod_only_log_loss"] < s["epd_only_log_loss"]
        assert s["tod_only_accuracy"] > s["epd_only_accuracy"]
        assert abs(s["both_b_tod"]) > abs(s["both_b_epd"])


def test_explosive_coefficient_is_flat_and_turnover_coefficient_eases(facts):
    s1, s3 = facts["shift_by_era"][facts["eras"][0]], facts["shift_by_era"][facts["eras"][2]]
    assert abs(s3["both_b_epd"] - s1["both_b_epd"]) < 0.1
    assert abs(s3["both_b_tod"]) < abs(s1["both_b_tod"])  # eased toward zero
    t = facts["trend"]["tod_std_coef"]
    assert t["slope_per_season"] > 0                       # direction Simms describes...
    assert t["slope_per_season"] < 2 * t["slope_se"]       # ...not significant on its own


def test_exchange_rate_is_a_little_over_two_and_stable(facts):
    ratios = [-facts["exchange_by_era"][e]["exchange_ratio_turnover_to_explosive"] for e in facts["eras"]]
    assert all(2.0 < r < 2.6 for r in ratios)
    assert max(ratios) - min(ratios) < 0.4
    x3 = facts["exchange_by_era"][facts["eras"][2]]
    assert 3.5 < -x3["points_per_turnover"] < 4.7 and 1.5 < x3["points_per_explosive"] < 2.1


def test_winning_explosives_but_losing_turnovers_is_a_losing_proposition(facts):
    for era in facts["eras"] + ["ALL"]:
        h = facts["head_to_head_by_era"][era]
        assert h["won_explosive_lost_turnover"]["win_rate"] < 0.5
        assert h["won_both"]["win_rate"] > 0.85
        assert h["turnover_only"]["win_rate"] > h["explosive_only"]["win_rate"]
    h1 = facts["head_to_head_by_era"][facts["eras"][0]]["won_explosive_lost_turnover"]["win_rate"]
    h3 = facts["head_to_head_by_era"][facts["eras"][2]]["won_explosive_lost_turnover"]["win_rate"]
    assert h3 > h1  # "a little better than it was"
    # garbage-time filter: big-play team does a few points better, still below 50%
    for era, g in facts["garbage_time_comparison"].items():
        assert g["no_garbage"] > g["all_plays"] and g["no_garbage"] < 0.5


def test_explosive_differential_is_far_more_persistent_than_turnover_differential(facts):
    for era in facts["eras"]:
        p = facts["persistence_by_era"][era]
        e, t, m = p["explosive_diff_per_game"], p["turnover_diff_per_game"], p["margin_per_game"]
        assert e["r"] > 1.7 * t["r"]           # "about twice"
        assert e["r"] > t["ci_hi"] and t["r"] < e["ci_lo"]   # each point estimate outside the other's interval
        assert m["r"] > e["r"]                 # margin is the benchmark
    # holds year to year as well
    for era in facts["eras"]:
        y = facts["persistence_year_to_year"][era]
        assert y["explosive_diff_per_game"]["r"] > y["turnover_diff_per_game"]["r"]


def test_mechanism_runs_against_the_shorter_drive_story(facts):
    m0, m1 = facts["mechanism_1999"], facts["mechanism_2025"]
    assert m1["plays_per_drive"] > m0["plays_per_drive"]
    assert m1["seconds_per_drive"] > m0["seconds_per_drive"]
    assert m1["def_play_rate_per_snap"] < m0["def_play_rate_per_snap"]
    assert m1["turnovers_per_game"] < 0.65 * m0["turnovers_per_game"]   # "about forty percent" drop
    assert abs(m1["pass_rate"] - m0["pass_rate"]) < 0.03                # flat
    for era in facts["eras"]:
        assert facts["strategy_by_era"][era]["correlation"] > 0        # explosive teams run slightly LONGER drives


def test_tsr_correlations_are_equal_and_top_five_are_remembered_teams(facts):
    c = facts["tsr_corr_all"]
    assert abs(c["r_explosive_diff"] - (-c["r_turnover_diff"])) < 0.05
    top = facts["leaderboard_top5"]
    assert [(t["franchise"], t["season"]) for t in top] == [("SEA", 2014), ("SF", 2012), ("SF", 2023), ("BAL", 2019), ("PIT", 2001)]
    assert sum(t["reached_super_bowl"] for t in top) == 3
