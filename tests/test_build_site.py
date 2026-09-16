import numpy as np
import pandas as pd
import pytest

from build_site import _fmt, _record, _season_result_text, build_super_bowls_table


def test_fmt_handles_nan_and_rounds():
    assert _fmt(np.nan) == "-"
    assert _fmt(1.2345, 2) == "1.23"


def test_record_includes_ties_only_when_present():
    assert _record({"wins": 10, "losses": 5, "ties": 1}) == "10-5-1"
    assert _record({"wins": 10, "losses": 6, "ties": 0}) == "10-6"


@pytest.mark.parametrize(
    "row,expected",
    [
        ({"won_super_bowl": True, "reached_super_bowl": True, "division_title": True}, "Won the Super Bowl"),
        ({"won_super_bowl": False, "reached_super_bowl": True, "division_title": True}, "Lost the Super Bowl"),
        ({"won_super_bowl": False, "reached_super_bowl": False, "division_title": True}, "Division champion"),
        ({"won_super_bowl": False, "reached_super_bowl": False, "division_title": False}, ""),
    ],
)
def test_season_result_text_priority_order(row, expected):
    assert _season_result_text(row) == expected


def test_build_super_bowls_table_computes_correct_z_gap():
    sb = pd.DataFrame(
        [{"season": 2000, "winner": "A", "loser": "B", "winner_score": 20, "loser_score": 10}]
    )
    profile = pd.DataFrame(
        [
            {"season": 2000, "franchise": "A", "bayes_rating_z": 1.5},
            {"season": 2000, "franchise": "B", "bayes_rating_z": 0.5},
        ]
    )
    table = build_super_bowls_table(sb, profile)
    row = table.iloc[0]
    assert row["z_gap"] == pytest.approx(1.0)
    assert row["winner_score"] == 20
