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


def test_competitive_time_shrinks_the_gap_by_about_two_thirds(facts):
    for era in facts["eras"]:
        c = facts["competitive_time_by_era"][era]
        assert abs(c["ng_epd_minus_tod_gap"]) < 0.5 * abs(c["all_epd_minus_tod_gap"])
        assert abs(c["ng_b_tod"]) > c["ng_b_epd"]            # "the turnover still leads"
        assert abs(c["ng_b_tod"]) < abs(c["all_b_tod"]) and c["ng_b_epd"] > c["all_b_epd"]


def test_regular_season_explosive_edge_predicts_playoff_wins_and_turnover_edge_does_not(facts):
    assert facts["playoff_prediction_b_epd"] > 1.5 * facts["playoff_prediction_se_epd"]
    assert abs(facts["playoff_prediction_b_tod"]) < facts["playoff_prediction_se_tod"]
    assert facts["playoff_prediction_n"] > 250
    assert facts["postseason_won_explosive_lost_turnover_win_rate"] < 0.4
    assert abs(facts["super_bowl_median_epd_rank"] - facts["super_bowl_median_tod_rank"]) <= 2  # "a tie"


def test_explosive_passing_persists_more_with_the_same_quarterback(facts):
    # "persists more when the same quarterback returns" - an association, stated as such
    assert facts["qb_continuity_same_qb_r"] > facts["qb_continuity_changed_qb_r"]
    assert facts["qb_continuity_same_qb_n"] > 400 and facts["qb_continuity_changed_qb_n"] > 250
    assert isinstance(facts["qb_continuity_ci_overlap"], bool)
    # the corrected measure is a pass-only rate: explosive completions per own dropback, well under 20%
    assert all(0.05 < q["rate"] < 0.2 for q in facts["qb_career_top3"])
    assert 0.05 < facts["qb_top_season"]["rate"] < 0.25
    # the join now covers every regular-season team-game
    assert facts["qb_join_unmatched"] == 0 and facts["qb_join_team_games"] > 13000


def test_rarity_explains_part_but_not_all_of_the_persistence_gap(facts):
    # counting noise alone would leave turnovers repeating well above what is observed
    assert facts["rel_turnover_implied"] > facts["rel_turnover_observed"] + 0.1
    # explosive differential sits close to its noise-only ceiling
    assert abs(facts["rel_explosive_implied"] - facts["rel_explosive_observed"]) < 0.08
    # "roughly N percent of the gap": between a quarter and three quarters
    assert 0.25 < facts["rel_gap_share_from_rarity"] < 0.75


def test_turnover_playoff_coefficient_range_straddles_zero(facts):
    assert facts["playoff_prediction_tod_lower"] < 0 < facts["playoff_prediction_tod_upper"]


def test_where_the_big_plays_went(facts):
    assert facts["decomposition_to_rate"] < facts["decomposition_from_rate"]
    assert facts["decomposition_share_rate_effect"] > 0.8          # "about 90%"
    assert abs(facts["drive_position_play1_last_era"] - facts["drive_position_play1_first_era"]) < 0.015
    assert 0.13 < facts["garbage_share_mean"] < 0.18


def test_defensive_play_risk_flattens_after_play_three(facts):
    for suffix in ("first_era", "last_era"):
        p1, p3, p8 = (facts[f"def_play_rate_play{k}_{suffix}"] for k in ("1", "3", "8plus"))
        assert p3 > p1 and abs(p8 - p3) < 0.015
    assert facts["def_play_rate_play1_last_era"] < facts["def_play_rate_play1_first_era"]  # curve shifted down
    assert facts["points_per_drive_last_era"] > facts["points_per_drive_first_era"]
    assert abs(facts["p_def_play_per_drive_last_era"] - facts["p_def_play_per_drive_first_era"]) < 0.02
