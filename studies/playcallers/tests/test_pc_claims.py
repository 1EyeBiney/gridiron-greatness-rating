"""
Pins the qualitative claims made in the Findings / What It Means /
Methodology prose to the tables. Numbers in the prose are injected from
`facts` at render time and can't drift; the claims built on them can, so
each one is asserted here - the same pattern as the sibling explosive-edge
study's test_xe_claims.py.
"""
import pytest

import pc_site


@pytest.fixture(scope="module")
def facts():
    return pc_site.build_facts(pc_site.load_tables())


def test_scope_counts_add_up(facts):
    assert facts["n_rated"] + facts["n_excluded"] == facts["n_unit_seasons"]
    assert facts["n_rated"] > 0 and facts["n_excluded"] > 0


def test_defensive_shrinkage_needs_more_seasons_than_offensive(facts):
    off = facts["variance_components"]["offense"]["seasons_for_half_weight"]
    dfn = facts["variance_components"]["defense"]["seasons_for_half_weight"]
    assert dfn > off  # "defense needs roughly twice as many seasons"
    assert dfn > 1.5 * off


def test_qb_adjusted_model_barely_beats_qb_only_but_beats_caller_only(facts):
    crossed = facts["qb_model_crossed_mse"]
    caller_only = facts["qb_model_caller_only_mse"]
    qb_only = facts["qb_model_qb_only_mse"]
    assert crossed < caller_only
    assert abs(crossed - qb_only) < 0.05 * qb_only + 0.02  # "about equal"


def test_ben_johnson_and_macdonald_ratings_are_shrunk_toward_the_mean(facts):
    bj = facts["ben_johnson"]
    mm = facts["mike_macdonald"]
    assert bj and mm
    assert abs(bj["rating"]) < abs(bj["mean_z_epa"])
    assert abs(mm["rating"]) < abs(mm["mean_z_epa"])
    assert bj["seasons"] == 4
    assert mm["seasons"] == 4


def test_offense_arrival_bump_is_smaller_than_the_bottom_tercile_baseline(facts):
    arrival = facts["moves_summary"][("offense", "arrival_change")]["mean"]
    baseline_low = facts["moves_summary"][("offense", "baseline_tercile_low")]["mean"]
    assert arrival < baseline_low  # bottom-tercile teams improve on average regardless of who they hire
    assert baseline_low > 0


def test_top10_lists_are_sorted_by_rank(facts):
    for key in ("top10_offense", "top10_defense"):
        ranks = [row["rank_in_unit"] for row in facts[key]]
        assert ranks == sorted(ranks)
        assert ranks[0] == 1
        assert len(facts[key]) == 10


def test_source_agreement_rate_is_high(facts):
    assert facts["source_agreement_rate"] is not None
    assert facts["source_agreement_rate"] > 0.9


def test_basis_counts_are_dominated_by_default_coordinator(facts):
    counts = facts["basis_counts"]
    total = sum(counts.values())
    assert counts.get("default_coordinator", 0) / total > 0.5


def test_scope_spans_1999_to_2025(facts):
    assert facts["first_season"] == 1999
    assert facts["last_season"] == 2025


# ---- claims made in the edited Findings and What It Means prose


def test_quarterback_only_model_is_about_as_good_as_the_crossed_model(facts):
    crossed, qb, caller = (facts["qb_model_crossed_mse"], facts["qb_model_qb_only_mse"],
                           facts["qb_model_caller_only_mse"])
    assert abs(qb - crossed) < 0.03          # "about as well"
    assert caller > qb + 0.05                # "clearly worse"


def test_top_of_both_lists_is_what_the_prose_names(facts):
    assert [r["person"] for r in facts["top10_offense"][:5]] == [
        "Tom Moore", "Al Saunders", "Josh McDaniels", "Sean Payton", "Andy Reid"]
    assert [r["person"] for r in facts["top10_defense"][:5]] == [
        "Rex Ryan", "Marvin Lewis", "Monte Kiffin", "Mike Macdonald", "Jim Johnson"]


def test_johnson_and_macdonald_claims(facts):
    bj, mm = facts["ben_johnson"], facts["mike_macdonald"]
    assert bj["seasons"] == 4 and mm["seasons"] == 4
    assert bj["n_franchises"] == 2 and mm["n_franchises"] == 2          # "two different teams"
    assert bj["mean_z_epa"] > 1 and mm["mean_z_epa"] > 1
    assert bj["rating"] < bj["mean_z_epa"] and mm["rating"] < mm["mean_z_epa"]
    assert bj["rank_in_unit"] <= 10 and mm["rank_in_unit"] <= 10


def test_moves_are_mostly_regression_to_the_mean(facts):
    ms = facts["moves_summary"]
    assert 0 < ms[("offense", "arrival_change")]["mean"] < ms[("offense", "baseline_tercile_low")]["mean"]
    assert ms[("offense", "baseline_tercile_high")]["mean"] < ms[("offense", "departure_change")]["mean"] < 0


def test_defense_needs_more_seasons_and_trees_tie_at_the_top(facts):
    vc = facts["variance_components"]
    assert vc["defense"]["seasons_for_half_weight"] > 1.5 * vc["offense"]["seasons_for_half_weight"]
    trees = facts["top_coaching_trees"]
    assert trees[0]["n_became_head_coach"] == trees[1]["n_became_head_coach"]      # "lead with N each"
    assert facts["bio_agree_n"] / facts["bio_checked_n"] > 0.98
