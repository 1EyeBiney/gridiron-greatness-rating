"""Tests for the Phase 1c gap-fill scripts. No network. Run:
    python -m pytest tests/test_pc_gapfill.py -q
from the study folder.
"""
import csv
from pathlib import Path

import pc_gapfill_step2_bios as bios
import pc_gapfill_step6_combine as combine

STUDY = Path(__file__).resolve().parents[1]
PROCESSED = STUDY / "data" / "processed"


# ------------------------------------------------------- navbox / years


def test_extract_years_range():
    assert bios.extract_years("1999–2012") == (1999, 2012)


def test_extract_years_single():
    assert bios.extract_years("2005") == (2005, 2005)


def test_extract_years_present():
    assert bios.extract_years("2013–present") == (2013, 2025)


def test_extract_years_endash_and_hyphen():
    assert bios.extract_years("2000-2004") == (2000, 2004)
    assert bios.extract_years("2000–2004") == (2000, 2004)


# ------------------------------------------------------- title normalization


def test_normalize_titles_head_coach():
    assert bios.normalize_titles("Head coach") == [("HC", False, False)]


def test_normalize_titles_offensive_coordinator():
    assert bios.normalize_titles("Offensive coordinator") == [("OC", False, False)]


def test_normalize_titles_interim():
    result = bios.normalize_titles("Interim defensive coordinator")
    assert result == [("DC", True, False)]


def test_normalize_titles_compound_excludes_bare_assistant_head_coach():
    # a plain "assistant head coach" (no coordinator) is an assistant, not HC
    assert bios.normalize_titles("Assistant head coach") == []


def test_normalize_titles_compound_interim_hc_and_oc():
    result = bios.normalize_titles("Interim head coach & offensive coordinator")
    roles = {r for r, _, _ in result}
    assert roles == {"HC", "OC"}
    assert all(interim for _, interim, _ in result)


def test_normalize_titles_assistant_head_coach_slash_oc():
    result = bios.normalize_titles("Assistant head coach/offensive coordinator")
    assert ("OC", False, False) in result
    assert not any(r == "HC" for r, _, _ in result)


# ------------------------------------------------------- pastcoaching parsing


def test_parse_pastcoaching_simple_line():
    block = "\n* [[Philadelphia Eagles]] ({{nfly|1999}}–{{nfly|2012}})<br />Head coach\n"
    rows = bios.parse_pastcoaching(block)
    assert len(rows) == 1
    r = rows[0]
    assert r["team"] == "Philadelphia Eagles"
    assert (r["first_season"], r["last_season"]) == (1999, 2012)
    assert r["role"] == "HC"


def test_parse_pastcoaching_subbullets_inherit_team():
    block = (
        "\n* {{ubl|[[Green Bay Packers]] ({{nfly|1992|1998}})}}\n"
        "** {{ubl|Assistant offensive line & tight ends coach ({{nfly|1992|1996}})}}\n"
        "** {{ubl|Quarterbacks coach & assistant head coach ({{nfly|1997|1998}})}}\n"
    )
    rows = bios.parse_pastcoaching(block)
    # neither sub-title is HC/OC/DC, so no rows should be produced (not
    # "quarterbacks coach", and "assistant head coach" alone is excluded)
    assert rows == []


def test_parse_pastcoaching_subbullet_produces_role():
    block = (
        "\n* {{ubl|[[Kansas City Chiefs]] ({{nfly|2013|2020}})}}\n"
        "** {{ubl|Offensive coordinator ({{nfly|2013|2017}})}}\n"
    )
    rows = bios.parse_pastcoaching(block)
    assert len(rows) == 1
    assert rows[0]["team"] == "Kansas City Chiefs"
    assert (rows[0]["first_season"], rows[0]["last_season"]) == (2013, 2017)
    assert rows[0]["role"] == "OC"


def test_parse_pastcoaching_single_year_graduate_assistant_excluded():
    block = "\n* [[BYU Cougars football|BYU]] (1982)<br />Graduate assistant\n"
    rows = bios.parse_pastcoaching(block)
    assert rows == []  # not HC/OC/DC


# ------------------------------------------------------- team -> franchise mapping


def test_team_to_franchise_relocated_teams():
    mapping = bios.load_team_name_to_franchise()
    assert mapping["San Diego Chargers"] == "LAC"
    assert mapping["Los Angeles Chargers"] == "LAC"
    assert mapping["St. Louis Rams"] == "LAR"
    assert mapping["Los Angeles Rams"] == "LAR"
    assert mapping["Oakland Raiders"] == "OAK"
    assert mapping["Las Vegas Raiders"] == "OAK"
    assert mapping["Washington Redskins"] == "WSH"
    assert mapping["Washington Commanders"] == "WSH"
    assert mapping["Houston Oilers"] == "TEN"
    assert mapping["Tennessee Oilers"] == "TEN"
    assert mapping["Houston Texans"] == "HOU"


def test_team_to_franchise_non_nfl_team_absent():
    mapping = bios.load_team_name_to_franchise()
    assert "Arizona State" not in mapping
    assert "Long Beach Poly HS (CA)" not in mapping


# ------------------------------------------------------- name cleaning reuse


def test_normalize_key_reused_from_build_derived():
    assert combine.normalize_key("Pete Carmichael Jr.") == combine.normalize_key("Pete Carmichael Jr")


# ------------------------------------------------------- real-file checks (skip if not generated)


def _load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_staff_stints_all_no_duplicate_rows():
    path = PROCESSED / "staff_stints_all.csv"
    if not path.exists():
        return
    rows = _load(path)
    keys = [(r["season"], r["franchise"], r["role"], r["person"]) for r in rows]
    assert len(keys) == len(set(keys)), "staff_stints_all.csv has duplicate (season, franchise, role, person) rows"


def test_every_gapfill_row_corresponds_to_a_real_gap():
    gapfill_path = PROCESSED / "staff_gapfill.csv"
    gaps_path = PROCESSED / "staff_gaps.csv"
    if not (gapfill_path.exists() and gaps_path.exists()):
        return
    gaps = {(r["season"], r["franchise"], r["role"]) for r in _load(gaps_path)}
    gapfill = _load(gapfill_path)
    for r in gapfill:
        assert (r["season"], r["franchise"], r["role"]) in gaps


def test_coverage_improves_over_1999_2010_pages_only():
    old_path = PROCESSED / "staff_stints_pages_1999_2010.csv"
    all_path = PROCESSED / "staff_stints_all.csv"
    if not (old_path.exists() and all_path.exists()):
        return
    old_rows = _load(old_path)
    all_rows = _load(all_path)

    def coverage(rows):
        have = set()
        for r in rows:
            season = int(r["season"])
            if 1999 <= season <= 2010 and r["role"] in ("OC", "DC"):
                have.add((season, r["franchise"], r["role"]))
        return have

    old_cov = coverage(old_rows)
    new_cov = coverage(all_rows)
    assert len(new_cov) >= len(old_cov)
    # should be a real improvement given known gaps existed
    assert len(new_cov) > len(old_cov)
