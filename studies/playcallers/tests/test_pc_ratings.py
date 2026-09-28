"""Tests for Phases 2-4: unit ratings, play-caller ratings, coaching trees."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STUDY = Path(__file__).resolve().parents[1]
PROCESSED = STUDY / "data" / "processed"

import pc_unit_ratings as ur
import pc_playcaller_ratings as pr
import pc_coaching_trees as ct


# ----------------------------------------------------------------- Phase 2


def _synthetic_round_robin():
    """4 teams, round robin home-and-away, one season, with a known OFF/DEF
    and a home effect baked in, so the model should recover them."""
    teams = ["AAA", "BBB", "CCC", "DDD"]
    true_off = {"AAA": 0.10, "BBB": 0.00, "CCC": -0.05, "DDD": 0.15}
    true_def = {"AAA": 0.05, "BBB": -0.10, "CCC": 0.00, "DDD": 0.02}
    home_effect = 0.03
    rng = np.random.default_rng(0)
    rows = []
    for a in teams:
        for b in teams:
            if a == b:
                continue
            for is_home_a in (True, False):
                plays = 60
                mu = 0.0
                y_a = mu + true_off[a] - true_def[b] + home_effect * is_home_a + rng.normal(0, 0.01)
                epa_total = y_a * plays
                rows.append({
                    "season": 2020, "game_type": "REG", "franchise": a, "opp_franchise": b,
                    "is_home": is_home_a, "plays": plays, "epa_total": epa_total,
                    "explosive_20_10": max(0, y_a + 0.1) * plays * 0.1, "yards": (y_a + 5) * plays,
                })
    return pd.DataFrame(rows)


def test_unit_ratings_recover_known_off_def():
    games = _synthetic_round_robin()
    coefs = ur.fit_season_metric(games, "epa_total", "plays")
    coefs = coefs.set_index("franchise")
    # centered comparison: differences between teams should track the truth
    off = coefs["off_raw_coef"]
    true_off = pd.Series({"AAA": 0.10, "BBB": 0.00, "CCC": -0.05, "DDD": 0.15})
    off_c = off - off.mean()
    true_c = true_off - true_off.mean()
    corr = np.corrcoef(off_c, true_c)[0, 1]
    assert corr > 0.9
    # DDD should rate above CCC (true_off DDD=0.15 > CCC=-0.05)
    assert off["DDD"] > off["CCC"]


def test_defense_sign_positive_for_good_defense():
    games = _synthetic_round_robin()
    coefs = ur.fit_season_metric(games, "epa_total", "plays").set_index("franchise")
    # BBB has true_def=-0.10 (allows MORE than average -> bad defense -> should be low/negative)
    # AAA has true_def=0.05 (allows less -> good defense -> higher DEF coef)
    assert coefs.loc["AAA", "def_raw_coef"] > coefs.loc["BBB", "def_raw_coef"]


# ----------------------------------------------------------------- Phase 3: shrinkage


def test_shrinkage_more_seasons_less_shrinkage():
    # person A: 1 season with a big z; person B: 6 seasons with the same mean z
    rows = []
    rows.append({"person": "A", "z_epa": 2.0, "season": 2020})
    for s in range(2015, 2021):
        rows.append({"person": "B", "z_epa": 2.0, "season": s})
    # add a few other people with noise around 0 to estimate variance components
    rng = np.random.default_rng(1)
    for i in range(20):
        for s in range(2015, 2021):
            rows.append({"person": f"P{i}", "z_epa": rng.normal(0, 1.0), "season": s})
    df = pd.DataFrame(rows)
    sigma2, tau2 = pr.anova_variance_components(df, "z_epa", "person")
    shrunk = pr.shrink_ratings(df, "z_epa", "person", sigma2, tau2).set_index("person")

    # both start at raw mean 2.0; B (6 seasons) should be shrunk less than A (1 season)
    assert shrunk.loc["B", "rating"] > shrunk.loc["A", "rating"]
    # rating magnitude never exceeds raw mean magnitude
    assert shrunk.loc["A", "rating"] <= shrunk.loc["A", "raw_mean"] + 1e-9
    assert shrunk.loc["B", "rating"] <= shrunk.loc["B", "raw_mean"] + 1e-9


# ----------------------------------------------------------------- Phase 3: exclusions


def test_exclusion_rules():
    draft = pd.DataFrame([
        {"season": 2020, "franchise": "AAA", "unit": "offense", "head_coach": "X", "coordinator": "Y",
         "default_playcaller": "Y", "proposed_playcaller": "Y", "basis": "default_coordinator",
         "confidence": "medium", "evidence_ids": None, "midseason_change": False, "note": None},
        {"season": 2020, "franchise": "BBB", "unit": "offense", "head_coach": "X", "coordinator": "Y",
         "default_playcaller": "Y", "proposed_playcaller": "Y", "basis": "default_coordinator",
         "confidence": "medium", "evidence_ids": None, "midseason_change": True, "note": None},
        {"season": 2020, "franchise": "CCC", "unit": "offense", "head_coach": "X", "coordinator": "Y",
         "default_playcaller": "Y", "proposed_playcaller": "Y | Z", "basis": "default_coordinator",
         "confidence": "medium", "evidence_ids": None, "midseason_change": False, "note": None},
        {"season": 2020, "franchise": "DDD", "unit": "offense", "head_coach": "X", "coordinator": None,
         "default_playcaller": None, "proposed_playcaller": None, "basis": "default_coordinator",
         "confidence": "medium", "evidence_ids": None, "midseason_change": False, "note": None},
    ])
    kept, excluded = pr.apply_exclusions(draft)
    assert list(kept["franchise"]) == ["AAA"]
    assert set(excluded["franchise"]) == {"BBB", "CCC", "DDD"}
    reasons = excluded.set_index("franchise")["reason"]
    assert "midseason_change" in reasons["BBB"]
    assert "multiple_playcallers" in reasons["CCC"]
    assert "no_proposed_playcaller" in reasons["DDD"]


# ----------------------------------------------------------------- Phase 3: QB-adjusted model


def test_qb_adjusted_model_recovers_planted_effects_and_flags_nonseparable():
    rng = np.random.default_rng(2)
    callers = ["C1", "C2", "C3"]
    qbs = ["Q1", "Q2", "Q3"]
    true_caller = {"C1": 0.8, "C2": -0.3, "C3": 0.1}
    true_qb = {"Q1": 0.5, "Q2": -0.6, "Q3": 0.05}

    rows = []
    season = 2015
    # C1 always with Q1 (non-separable pair; Q1 never plays for anyone else)
    for _ in range(5):
        rows.append({"season": season, "unit": "offense", "person": "C1", "primary_qb_id": "Q1",
                     "z_epa": true_caller["C1"] + true_qb["Q1"] + rng.normal(0, 0.05)})
        season += 1
    season = 2015
    # C2 and C3 both play with Q2 and Q3 in a crossed design (separable)
    for i in range(6):
        c = "C2" if i % 2 == 0 else "C3"
        q = "Q2" if i < 3 else "Q3"
        rows.append({"season": season, "unit": "offense", "person": c, "primary_qb_id": q,
                     "z_epa": true_caller[c] + true_qb[q] + rng.normal(0, 0.05)})
        season += 1
    df = pd.DataFrame(rows)

    caller_out, qb_out, cv_summary = pr.build_qb_adjusted(df)
    caller_out = caller_out.set_index("person")
    qb_out_idx = qb_out.set_index("primary_qb_id")

    # true_caller: C3 (0.1) > C2 (-0.3); the recovered ratings should preserve that order
    assert caller_out.loc["C3", "rating_qb_adjusted"] > caller_out.loc["C2", "rating_qb_adjusted"]
    # true_qb: Q3 (0.05) > Q2 (-0.6)
    assert qb_out_idx.loc["Q3", "qb_effect"] > qb_out_idx.loc["Q2", "qb_effect"]
    # C1/Q1 pair is non-separable
    assert caller_out.loc["C1", "separable"] == False
    assert caller_out.loc["C2", "separable"] == True
    assert caller_out.loc["C3", "separable"] == True


# ----------------------------------------------------------------- Phase 3: moves


def test_moves_builder_four_quantities():
    seasons = pd.DataFrame([
        {"season": 2018, "franchise": "AAA", "unit": "offense", "person": "Mover", "z_epa": 1.0},
        {"season": 2019, "franchise": "AAA", "unit": "offense", "person": "Successor", "z_epa": -0.5},
        {"season": 2018, "franchise": "BBB", "unit": "offense", "person": "Incumbent", "z_epa": -0.2},
        {"season": 2019, "franchise": "BBB", "unit": "offense", "person": "Mover", "z_epa": 0.8},
    ])
    moves = pr.build_moves(seasons)
    assert len(moves) == 1
    row = moves.iloc[0]
    assert row["person"] == "Mover"
    assert row["old_team_with"] == 1.0
    assert row["old_team_after"] == -0.5
    assert row["new_team_before"] == -0.2
    assert row["new_team_with"] == 0.8
    assert row["departure_change"] == pytest.approx(-0.5 - 1.0)
    assert row["arrival_change"] == pytest.approx(0.8 - (-0.2))


# ----------------------------------------------------------------- Phase 4: coaching trees


def test_coaching_tree_edges_inline_example():
    stints = pd.DataFrame([
        {"season": 2015, "franchise": "AAA", "role": "HC", "person": "Mentor"},
        {"season": 2015, "franchise": "AAA", "role": "OC", "person": "Protege1"},
        {"season": 2016, "franchise": "AAA", "role": "HC", "person": "Mentor"},
        {"season": 2016, "franchise": "AAA", "role": "OC", "person": "Protege1"},
        {"season": 2017, "franchise": "BBB", "role": "HC", "person": "Protege1"},
    ])
    edges = ct.build_edges(stints)
    assert len(edges) == 1
    e = edges.iloc[0]
    assert e["mentor"] == "Mentor"
    assert e["protege"] == "Protege1"
    assert e["first_season"] == 2015
    assert e["last_season"] == 2016

    summary = ct.build_summary(edges, stints)
    s = summary[summary["mentor"] == "Mentor"].iloc[0]
    assert s["n_distinct_coordinators"] == 1
    assert s["n_became_head_coach"] == 1


# ----------------------------------------------------------------- real-file checks


@pytest.mark.skipif(not (PROCESSED / "playcaller_seasons.csv").exists(), reason="processed outputs not built")
def test_real_playcaller_seasons_have_z_and_rank_rules():
    seasons = pd.read_csv(PROCESSED / "playcaller_seasons.csv")
    assert seasons["z_epa"].notna().all()

    careers = pd.read_csv(PROCESSED / "playcaller_careers.csv")
    ranked = careers[careers["rank_in_unit"].notna()]
    assert (ranked["seasons"] >= 3).all()
    unranked = careers[careers["rank_in_unit"].isna()]
    assert (unranked["seasons"] < 3).all()


@pytest.mark.skipif(not (PROCESSED / "playcaller_seasons.csv").exists(), reason="processed outputs not built")
def test_ben_johnson_and_mike_macdonald_known_anchors():
    seasons = pd.read_csv(PROCESSED / "playcaller_seasons.csv")
    bj = seasons[(seasons["person"] == "Ben Johnson") & (seasons["unit"] == "offense")]
    assert set(bj["franchise"]).issuperset({"DET"})
    assert set(bj[bj["franchise"] == "DET"]["season"]).issuperset({2022, 2023, 2024})

    mm = seasons[(seasons["person"] == "Mike Macdonald") & (seasons["unit"] == "defense")]
    bal_seasons = set(mm[mm["franchise"] == "BAL"]["season"])
    sea_seasons = set(mm[mm["franchise"] == "SEA"]["season"])
    assert bal_seasons.issuperset({2022, 2023})
    assert sea_seasons.issuperset({2024, 2025})


def test_coaching_tree_does_not_count_men_who_were_already_head_coaches():
    stints = pd.DataFrame([
        {"season": 2012, "franchise": "AA", "role": "HC", "person": "Old Hand"},      # head coach first...
        {"season": 2015, "franchise": "BB", "role": "HC", "person": "Mentor"},
        {"season": 2015, "franchise": "BB", "role": "DC", "person": "Old Hand"},      # ...coordinator later
        {"season": 2015, "franchise": "BB", "role": "OC", "person": "Young Gun"},
        {"season": 2017, "franchise": "CC", "role": "HC", "person": "Young Gun"},     # a true branch
    ])
    summary = ct.build_summary(ct.build_edges(stints), stints).set_index("mentor").loc["Mentor"]
    assert summary["n_became_head_coach"] == 1 and "Young Gun" in summary["became_head_coach_detail"]
    assert summary["n_already_head_coach"] == 1 and summary["already_head_coach_detail"] == "Old Hand"
