"""Unit tests for the analysis pieces, on synthetic data where the right
answer is known, plus structural checks on the real game table."""
import numpy as np
import pandas as pd
import pytest

import hfa


def _games(rows):
    df = pd.DataFrame(rows, columns=["home_franchise", "away_franchise", "home_score", "away_score"])
    df["neutral_site"] = False
    df["margin"] = df["home_score"] - df["away_score"]
    return df


def test_fit_season_recovers_known_ratings_and_home_field():
    # Truth: A=+6, B=0, C=-6, home field +3, no noise. Round robin home and away.
    truth = {"A": 6.0, "B": 0.0, "C": -6.0}
    rows = []
    for h in truth:
        for a in truth:
            if h != a:
                rows.append((h, a, 20 + truth[h] - truth[a] + 3, 20))
    f = hfa.fit_season(_games(rows))
    assert f["home_adv"] == pytest.approx(3.0, abs=1e-9)
    for t, r in truth.items():
        assert f["ratings"][t] == pytest.approx(r, abs=1e-9)
    assert f["ratings"].sum() == pytest.approx(0.0, abs=1e-9)


def test_adjusted_margin_is_zero_at_neutral_site():
    g = _games([("A", "B", 24, 20), ("B", "A", 17, 27)])
    g.loc[1, "neutral_site"] = True
    adj = hfa.adjusted_margin(g, pd.Series({"A": 2.0, "B": -2.0}))
    assert adj.iloc[0] == pytest.approx(4 - 4)
    assert np.isnan(adj.iloc[1])


def test_week_index_from_calendar_groups_a_thursday_to_monday_slate():
    g = pd.DataFrame({
        "week": [np.nan] * 5,
        "date": ["1975-09-21", "1975-09-22", "1975-09-25", "1975-09-28", "1975-10-05"],
    })
    # Sun 9/21 and Mon 9/22 are week 1; Thu 9/25 and Sun 9/28 week 2; Sun 10/5 week 3
    assert hfa._assign_week_index(g).tolist() == [1, 1, 2, 2, 3]


def test_week_index_uses_source_week_when_present():
    g = pd.DataFrame({"week": [3, 1, 1, 2], "date": ["x"] * 4})
    assert hfa._assign_week_index(g).tolist() == [3, 1, 1, 2]


def test_playoff_spots_follow_the_real_formats():
    assert hfa.playoff_spots_per_conference(1975) == 4
    assert hfa.playoff_spots_per_conference(1985) == 5
    assert hfa.playoff_spots_per_conference(2019) == 6
    assert hfa.playoff_spots_per_conference(2020) == 7


def test_playoff_race_status_marks_eliminated_and_clinched():
    # One conference, 4 teams, 1 playoff spot (patch spots), 3 rounds.
    # A wins its first two, D loses its first two -> entering week 3, A has
    # 2 pts, D has 0 with 1 game left: D eliminated (0+1 < 2). A: only
    # B/C could still reach 2 (they have 1 each)... so A is not clinched
    # with spots=1 unless nobody can catch it. Make B and C 0-2 too by
    # having them lose to A and to D? Simplify: A beats B, A beats C;
    # D loses to B and to C -> B,C at 1-1 (1 pt), can reach 2 = A's total.
    rows = [
        (1, "A", "B", 20, 10), (1, "D", "C", 10, 20),
        (2, "A", "C", 20, 10), (2, "B", "D", 20, 10),
        (3, "A", "D", 20, 10), (3, "B", "C", 20, 10),
    ]
    g = pd.DataFrame(rows, columns=["week_index", "home_franchise", "away_franchise", "home_score", "away_score"])
    g["season"] = 2000
    g["margin"] = g["home_score"] - g["away_score"]
    g["home_conf"] = "X"
    g["away_conf"] = "X"
    orig = hfa.playoff_spots_per_conference
    hfa.playoff_spots_per_conference = lambda s: 1
    try:
        out = hfa.playoff_race_status(g)
    finally:
        hfa.playoff_spots_per_conference = orig
    wk3 = out[out["week_index"] == 3].set_index("home_franchise")
    assert wk3.loc["A", "away_status"] == "eliminated"  # D
    assert wk3.loc["A", "home_status"] == "alive"        # A can still be caught by B or C
    assert (out[out["week_index"] == 1][["home_status", "away_status"]] == "alive").all().all()


def test_playoff_race_status_clinch_when_nobody_can_catch():
    rows = [(1, "A", "B", 20, 10), (2, "A", "B", 20, 10), (3, "A", "B", 20, 10)]
    g = pd.DataFrame(rows, columns=["week_index", "home_franchise", "away_franchise", "home_score", "away_score"])
    g["season"] = 2000
    g["margin"] = g["home_score"] - g["away_score"]
    g["home_conf"] = "X"
    g["away_conf"] = "X"
    orig = hfa.playoff_spots_per_conference
    hfa.playoff_spots_per_conference = lambda s: 1
    try:
        out = hfa.playoff_race_status(g)
    finally:
        hfa.playoff_spots_per_conference = orig
    wk3 = out[out["week_index"] == 3].iloc[0]
    assert wk3["home_status"] == "clinched"   # A 2-0, B 0-2 with one left: B can reach 1 < 2
    assert wk3["away_status"] == "eliminated"


@pytest.fixture(scope="module")
def games():
    return hfa.load_games()


def test_real_schedule_lengths_are_reproduced(games):
    n_weeks = games.groupby("season")["n_weeks"].first()
    assert (n_weeks.loc[1970:1977] == 14).all()
    assert (n_weeks.loc[1978:1989].drop(1982, errors="ignore") == 16).all()
    assert n_weeks.loc[1993] == 18
    assert (n_weeks.loc[[1990, 1991, 1992] + list(range(1994, 2021))] == 17).all()
    assert (n_weeks.loc[2021:2025] == 18).all()
    assert 1982 not in n_weeks.index


def test_every_game_has_a_conference_for_both_sides(games):
    assert games["home_conf"].notna().all() and games["away_conf"].notna().all()


def test_roof_and_division_flags_cover_nearly_all_modern_games(games):
    modern = games[games["season"] >= 1999]
    assert modern["indoor"].notna().all()
    assert modern["div_game"].notna().all()
    assert games[games["season"] < 1999]["indoor"].isna().all()


def test_summarize_matches_direct_mean(games):
    g, _ = hfa.add_adjusted_margins(games[games["season"] == 2010])
    s = hfa.summarize(g, ["season"]).iloc[0]
    direct = g["adj_margin"].dropna()
    assert s["hfa"] == pytest.approx(direct.mean())
    assert s["hfa_se"] == pytest.approx(direct.std() / np.sqrt(len(direct)))
    assert s["n"] == len(direct)


def test_late_window_freezes_status_at_window_start(games):
    g, _ = hfa.add_adjusted_margins(games[games["season"] == 2015])
    g = hfa.playoff_race_status(g)
    w = hfa.late_window(g, last_weeks=3)
    # Frozen status is constant per team across the window
    per_team = pd.concat([
        w[["home_franchise", "home_status_frozen"]].rename(columns={"home_franchise": "t", "home_status_frozen": "s"}),
        w[["away_franchise", "away_status_frozen"]].rename(columns={"away_franchise": "t", "away_status_frozen": "s"}),
    ])
    assert (per_team.groupby("t")["s"].nunique() == 1).all()
    assert w["week_index"].min() == w["n_weeks"].iloc[0] - 2
    # ratings fit on the window only: the residuals sum to ~0 over the window
    assert w["adj_margin_late"].dropna().mean() == pytest.approx(
        hfa.fit_season(w)["home_adv"], abs=1e-6)
