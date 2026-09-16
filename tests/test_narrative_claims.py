"""
The two narrative pages (src/site_templates/why.html and
what_it_means.html) state specific numbers in prose - all-time ranks,
ratings, in-season ranks. Prose can't be regenerated from data the way
a table can, so this pins the load-bearing claims to the data. If the
pipeline ever changes a rating enough to move one of these, this fails
and the prose gets updated deliberately instead of silently going stale.
"""
import pandas as pd
import pytest

from models.common import REPO


@pytest.fixture(scope="module")
def profile():
    p = pd.read_csv(REPO / "data" / "processed" / "team_season_full_profile.csv")
    p["rank_in_season"] = p.groupby("season")["bayes_rating_z"].rank(ascending=False).astype(int)
    p["alltime_rank"] = p["bayes_rating_z"].rank(ascending=False).astype(int)
    return p.set_index(["season", "franchise"])


@pytest.mark.parametrize(
    "season,team,alltime_rank",
    [
        (1996, "GB", 1),
        (1985, "CHI", 2),
        (1994, "SF", 3),
        (1978, "PIT", 4),
        (1989, "SF", 5),
        (1978, "DAL", 6),
        (2001, "LAR", 7),
        (2007, "NE", 8),
        (1983, "WSH", 11),
        (2004, "NE", 14),
        (1992, "DAL", 18),
        (1995, "SF", 19),
        (1998, "MIN", 21),
        (1994, "DAL", 23),
        (1993, "DAL", 24),
        (1995, "DAL", 27),
        (1970, "MIN", 34),
        (1973, "MIA", 40),
        (1972, "MIA", 99),
    ],
)
def test_alltime_ranks_cited_in_prose(profile, season, team, alltime_rank):
    assert profile.loc[(season, team), "alltime_rank"] == alltime_rank


@pytest.mark.parametrize(
    "season,team,rank_in_season",
    [
        (2025, "NE", 5),
        (2025, "SEA", 1),
        (2007, "NYG", 8),
        (2011, "NYG", 9),
        (2001, "NE", 6),
        (1970, "IND", 7),
    ],
)
def test_in_season_ranks_cited_in_prose(profile, season, team, rank_in_season):
    assert profile.loc[(season, team), "rank_in_season"] == rank_in_season


def test_offense_and_defense_claims(profile):
    # Best offense in the database is 2013 DEN; 2001 LAR is second. (The
    # first draft of the prose said LAR was first - this test caught it.)
    top_two = profile["offense_z"].nlargest(2).index.tolist()
    assert top_two == [(2013, "DEN"), (2001, "LAR")]
    # "a number only three other teams have ever reached" / "one of only
    # four offenses in fifty-six years to clear 3.0" - exactly four, and
    # 2007 NE is third among them, not the best non-champion (the first
    # draft said it was - this caught it).
    over_3 = profile[profile["offense_z"] >= 3.0]["offense_z"].sort_values(ascending=False)
    assert over_3.index.tolist() == [(2013, "DEN"), (2001, "LAR"), (1994, "SF"), (2007, "NE")]
    champs = profile[profile["won_super_bowl"]]
    # 1994 SF is the highest-rated offense of any champion, and the only
    # >= 3.0 offense that won the title
    assert champs["offense_z"].idxmax() == (1994, "SF")
    assert (champs["offense_z"] >= 3.0).sum() == 1
    # Best defense among champions is 2002 TB; 1985 CHI is second. (The
    # first draft of the prose called the Bears first - this caught it.)
    top_two_def = champs["defense_z"].nlargest(2).index.tolist()
    assert top_two_def == [(2002, "TB"), (1985, "CHI")]


def test_1972_dolphins_schedule_is_third_softest_among_champions(profile):
    champs = profile[profile["won_super_bowl"]]
    assert int(champs["schedule_difficulty"].rank().loc[(1972, "MIA")]) == 3


def test_vikings_claims(profile):
    minn = profile.xs("MIN", level="franchise")
    assert (minn["bayes_rating_z"] >= 1.1).sum() == 10
    sb_years = minn[minn["reached_super_bowl"]].index.tolist()
    assert sb_years == [1973, 1974, 1976]
    assert (minn.loc[sb_years, "rank_in_season"] == 4).all()
    assert not minn.loc[sb_years, "won_super_bowl"].any()


def test_only_three_franchises_have_seven_top_100_seasons(profile):
    counts = profile[profile["alltime_rank"] <= 100].groupby(level="franchise").size()
    assert set(counts[counts >= 7].index) == {"SF", "NE", "DAL"}


def test_1978_is_the_only_super_bowl_with_both_teams_in_the_alltime_top_six(profile):
    sb = profile[profile["reached_super_bowl"]].groupby(level="season")["alltime_rank"].max()
    assert sb[sb <= 6].index.tolist() == [1978]


def test_manning_colts_title_team_was_fifth_best_of_the_run(profile):
    run = profile.loc[[(s, "IND") for s in range(2003, 2011)]]
    order = run["bayes_rating_z"].rank(ascending=False)
    assert order.loc[(2006, "IND")] == 5


def test_1972_dolphins_hold_the_only_maximum_acc(profile):
    assert profile["acc"].idxmax() == (1972, "MIA")
    assert profile.loc[(1972, "MIA"), "acc"] == pytest.approx(30.0)
    assert (profile["acc"] >= 29.999).sum() == 1


def test_eight_champions_rate_below_1_25(profile):
    champs = profile[profile["won_super_bowl"]]
    assert (champs["bayes_rating_z"] < 1.25).sum() == 8
