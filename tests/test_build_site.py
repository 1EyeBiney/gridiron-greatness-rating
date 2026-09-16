import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from build_site import _fmt, _full_stat_row, _playoffs_text, _record, _vs_elite_text, build_super_bowls_table, render_all

HREF_RE = re.compile(r'href="([^"]+)"')


def test_fmt_handles_nan_and_rounds():
    assert _fmt(np.nan) == "-"
    assert _fmt(1.2345, 2) == "1.23"


def test_record_includes_ties_only_when_present():
    assert _record({"wins": 10, "losses": 5, "ties": 1}) == "10-5-1"
    assert _record({"wins": 10, "losses": 6, "ties": 0}) == "10-6"


@pytest.mark.parametrize(
    "row,expected",
    [
        ({"playoff_games": np.nan, "playoff_wins": 0}, "Did not qualify"),
        ({"playoff_games": 3, "playoff_wins": 3, "won_super_bowl": True, "reached_super_bowl": True}, "3-0 (won SB)"),
        ({"playoff_games": 3, "playoff_wins": 2, "won_super_bowl": False, "reached_super_bowl": True}, "2-1 (lost SB)"),
        ({"playoff_games": 1, "playoff_wins": 0, "won_super_bowl": False, "reached_super_bowl": False}, "0-1"),
    ],
)
def test_playoffs_text(row, expected):
    assert _playoffs_text(row) == expected


def test_vs_elite_text_handles_no_elite_opponents_and_formats_percentage():
    assert _vs_elite_text({"elite_opponents_played": np.nan}) == "-"
    assert _vs_elite_text({"elite_opponents_played": 3, "record_vs_elite_win_pct": 2 / 3}) == "66.7% (3)"


def test_full_stat_row_has_every_declared_column():
    from build_site import FULL_STAT_COLUMNS

    row = pd.Series(
        {
            "conference": "AFC",
            "division": "East",
            "wins": 10,
            "losses": 6,
            "ties": 0,
            "bayes_rating_z": 1.23,
            "bayes_rating_se": 2.5,
            "acc": 15.5,
            "offense_z": 0.5,
            "defense_z": -0.3,
            "dominance_z": 0.1,
            "schedule_difficulty": 0.05,
            "elite_opponents_played": 2,
            "record_vs_elite_win_pct": 0.5,
            "playoff_games": 2,
            "playoff_wins": 1,
            "won_super_bowl": False,
            "reached_super_bowl": True,
        }
    )
    result = _full_stat_row(row)
    for key, _, _ in FULL_STAT_COLUMNS:
        assert key in result, f"missing {key}"


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


def test_every_internal_link_in_the_built_site_resolves_to_a_real_file(tmp_path):
    """Full-site integration test: catches exactly the kind of bug that
    shipped in the first live deploy, where queries/index.html linked to
    'greatest_champions.html' (underscores) but the page generator wrote
    'greatest-champions.html' (hyphens) - a 404 a unit test on either
    piece alone wouldn't catch, since each side was individually correct
    with respect to its own inputs."""
    out_dir = tmp_path / "site"
    render_all(out_dir=out_dir)

    html_files = list(out_dir.rglob("*.html"))
    assert len(html_files) > 100  # sanity check the build actually ran

    broken = []
    for html_file in html_files:
        text = html_file.read_text(encoding="utf-8")
        for href in HREF_RE.findall(text):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (html_file.parent / href).resolve()
            if not target.exists():
                broken.append(f"{html_file.relative_to(out_dir)} -> {href}")

    assert not broken, f"{len(broken)} broken internal link(s):\n" + "\n".join(broken[:20])
