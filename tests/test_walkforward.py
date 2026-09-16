from datetime import timedelta

import pandas as pd

from walkforward import walk_forward_season


def three_week_season() -> pd.DataFrame:
    """4 teams, A > B > C > D in true strength, round-robin across 3
    weeks (each team plays once per week, weeks 7 days apart so the
    date-gap week-clustering in schedule_weeks.py sees them as distinct),
    deterministic margins, neutral site throughout."""
    strengths = {"A": 12.0, "B": 4.0, "C": -4.0, "D": -12.0}
    matchups = [("A", "B"), ("C", "D")], [("A", "C"), ("B", "D")], [("A", "D"), ("B", "C")]
    start = pd.Timestamp("2000-09-01")
    rows = []
    for week, pairs in enumerate(matchups, start=1):
        date = (start + timedelta(days=7 * (week - 1))).strftime("%Y-%m-%d")
        for home, away in pairs:
            margin = strengths[home] - strengths[away]
            rows.append(
                {
                    "game_uid": f"W{week}-{home}-{away}",
                    "date": date,
                    "week": None,
                    "home_franchise": home,
                    "away_franchise": away,
                    "margin": margin,
                    "neutral_site": True,
                    "game_type": "REG",
                    "home_score": 20 + margin / 2,
                    "away_score": 20 - margin / 2,
                }
            )
    return pd.DataFrame(rows)


def test_no_predictions_for_week_one():
    g = three_week_season()
    out = walk_forward_season(g, bt_reg_strength=3.0)
    assert 1 not in set(out["week_idx"])


def test_predicts_weeks_two_and_three_for_every_model():
    g = three_week_season()
    out = walk_forward_season(g, bt_reg_strength=3.0)
    assert set(out["week_idx"]) == {2, 3}
    assert set(out["model"]) == {"massey", "bayesian_margin", "bradley_terry"}


def test_disconnected_week_one_gives_no_edge_at_week_two():
    """Week 1 is A-B and C-D: two separate games with no common opponent,
    so going into week 2 nothing yet connects the {A,B} and {C,D}
    components. A regularized model correctly has no basis to favor A
    over C here and should sit at (or very near) a toss-up, not guess
    confidently from strengths it has no evidence for yet."""
    g = three_week_season()
    out = walk_forward_season(g, bt_reg_strength=3.0)
    week2 = out[(out["week_idx"] == 2) & (out["game_uid"] == "W2-A-C")]
    assert (week2["p_home_win"] - 0.5).abs().max() < 0.05


def test_stronger_team_favored_once_schedule_graph_connects():
    g = three_week_season()
    out = walk_forward_season(g, bt_reg_strength=3.0)
    # By week 3, weeks 1-2 (A-B, C-D, A-C, B-D) connect every team, so A
    # (strongest) hosting D (weakest) should now be favored by all models.
    week3 = out[(out["week_idx"] == 3) & (out["game_uid"] == "W3-A-D")]
    assert (week3["p_home_win"] > 0.5).all()


def test_graph_connected_flag_matches_actual_connectivity():
    g = three_week_season()
    out = walk_forward_season(g, bt_reg_strength=3.0)
    # Week 2's training data is week 1 alone (A-B, C-D): disconnected.
    # Week 3's training data is weeks 1-2 (adds A-C, B-D): connected.
    assert not out[out["week_idx"] == 2]["graph_connected"].any()
    assert out[out["week_idx"] == 3]["graph_connected"].all()
