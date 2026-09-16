import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from build_site import _fmt, _record, _season_result_text, build_super_bowls_table, render_all

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
