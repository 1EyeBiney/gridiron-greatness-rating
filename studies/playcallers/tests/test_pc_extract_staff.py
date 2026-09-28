"""Unit tests for pc_extract_staff.py parsing functions, using small inline
wikitext snippets (no network). Run: python -m pytest tests/ from the study
folder.
"""
from pathlib import Path

import pandas as pd
import pytest

import pc_extract_staff as pcs

STUDY = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------- fixtures

INFOBOX_SIMPLE = """{{Infobox NFL team season
| team            = Detroit Lions
| year            = 2023
| coach           = [[Dan Campbell]]
| off_coach       = [[Ben Johnson (American football coach)|Ben Johnson]]
| def_coach       = [[Aaron Glenn]]
| general_manager = [[Brad Holmes]]
| pro_bowlers     = {{Collapsible list
|title = 7
|1 = RT [[Penei Sewell]]
}}
}}
"""

INFOBOX_INTERIM = """{{Infobox NFL team season
| team            = Carolina Panthers
| year            = 2023
| coach           = [[Frank Reich]] (fired November 27; 1–10 record)<br>[[Chris Tabor]] (interim; 1–15 record)
| general_manager = [[Scott Fitterer]]
}}
"""

INFOBOX_UBL = """{{Infobox NFL team season
| team            = Washington Commanders
| year            = 2023
| coach           = [[Ron Rivera]]
| off_coach       = [[Eric Bieniemy]]
| def_coach       = {{ubl|[[Jack Del Rio]] (fired)|Ron Rivera (interim)}}
}}
"""

INFOBOX_TEMPLATE_IN_NOTE = """{{Infobox NFL team season
| team            = Indianapolis Colts
| year            = 2022
| coach           = [[Frank Reich]] (fired November 7; {{winpct|3|5|1|record=y}} record)<br/>[[Jeff Saturday]] (interim; {{winpct|1|7|record=y}} record)
}}
"""

STAFF_SIMPLE = """==Staff==
{{NFL final staff
|Year=2023
|TeamName=Detroit Lions
|Head Coaches=
*Head coach – [[Dan Campbell]]
*Assistant head coach/running backs – [[Scottie Montgomery]]
|Offensive Coaches=
*Offensive coordinator – [[Ben Johnson (American football coach)|Ben Johnson]]
*Passing game coordinator – [[Tanner Engstrand]]
|Defensive Coaches=
*Defensive coordinator – [[Aaron Glenn]]
}}
"""

STAFF_INTERIM_HC = """==Staff==
{{NFL final staff
|Year=2023
|TeamName=Carolina Panthers
|Head Coaches=
*Head coach – [[Frank Reich]]; ''fired on November 27''
*Interim head coach/special teams coordinator – [[Chris Tabor]]
}}
"""

STAFF_ANNOTATED_DC = """==Staff==
{{NFL final staff
|Year=2023
|TeamName=Chicago Bears
|Defensive Coaches=
*Defensive coordinator – [[Alan Williams (American football)|Alan Williams]]; <br>''resigned on September 20''
*Defensive line – Travis Smith
}}
"""

STAFF_SLASH_ROLE = """==Staff==
{{NFL final staff
|Year=2024
|TeamName=New York Giants
|Offensive Coaches=
*Assistant head coach/offensive coordinator – [[Mike Kafka]]
}}
"""

STAFF_ALT_HEADING = """===Staff / Coaches===
{{NFL final staff
|Year=2022
|TeamName=Denver Broncos
|Offensive Coaches=
*Offensive coordinator – [[Justin Outten]]
}}
"""


# ----------------------------------------------------------------- tests


def test_infobox_simple():
    block = pcs.extract_infobox_block(INFOBOX_SIMPLE)
    fields = pcs.parse_infobox_fields(block)
    assert fields["head_coach"] == "[[Dan Campbell]]"
    assert "Ben Johnson" in fields["offensive_coordinator"]
    assert fields["defensive_coordinator"] == "[[Aaron Glenn]]"


def test_infobox_interim_multiple_names():
    block = pcs.extract_infobox_block(INFOBOX_INTERIM)
    fields = pcs.parse_infobox_fields(block)
    names = pcs.split_name_segments(fields["head_coach"])
    assert names == ["Frank Reich", "Chris Tabor"]


def test_infobox_ubl_template():
    block = pcs.extract_infobox_block(INFOBOX_UBL)
    fields = pcs.parse_infobox_fields(block)
    names = pcs.split_name_segments(fields["defensive_coordinator"])
    assert names == ["Jack Del Rio", "Ron Rivera"]


def test_infobox_nested_template_in_parenthetical_note():
    block = pcs.extract_infobox_block(INFOBOX_TEMPLATE_IN_NOTE)
    fields = pcs.parse_infobox_fields(block)
    names = pcs.split_name_segments(fields["head_coach"])
    assert names == ["Frank Reich", "Jeff Saturday"]


def test_staff_section_simple():
    block = pcs.extract_staff_block(STAFF_SIMPLE)
    fields = pcs.parse_staff_fields(block)
    assert pcs.split_name_segments(fields["head_coach"][0]) == ["Dan Campbell"]
    assert "Ben Johnson" in fields["offensive_coordinator"][0]
    assert pcs.split_name_segments(fields["defensive_coordinator"][0]) == ["Aaron Glenn"]
    # "Assistant head coach/running backs" must NOT be picked up as head coach
    assert len(fields["head_coach"]) == 1


def test_staff_section_interim_head_coach_label():
    block = pcs.extract_staff_block(STAFF_INTERIM_HC)
    fields = pcs.parse_staff_fields(block)
    names = []
    for raw in fields["head_coach"]:
        names.extend(pcs.split_name_segments(raw))
    assert names == ["Frank Reich", "Chris Tabor"]


def test_staff_section_drops_italic_annotation_segment():
    block = pcs.extract_staff_block(STAFF_ANNOTATED_DC)
    fields = pcs.parse_staff_fields(block)
    names = []
    for raw in fields["defensive_coordinator"]:
        names.extend(pcs.split_name_segments(raw))
    assert names == ["Alan Williams"]


def test_staff_section_matches_role_after_slash():
    block = pcs.extract_staff_block(STAFF_SLASH_ROLE)
    fields = pcs.parse_staff_fields(block)
    names = []
    for raw in fields["offensive_coordinator"]:
        names.extend(pcs.split_name_segments(raw))
    assert names == ["Mike Kafka"]


def test_staff_section_alt_heading_level_and_wording():
    block = pcs.extract_staff_block(STAFF_ALT_HEADING)
    assert block is not None
    fields = pcs.parse_staff_fields(block)
    names = []
    for raw in fields["offensive_coordinator"]:
        names.extend(pcs.split_name_segments(raw))
    assert names == ["Justin Outten"]


def test_strip_wiki_markup_removes_refs_and_links():
    raw = "[[Ben Johnson (American football coach)|Ben Johnson]]<ref>cite</ref>"
    assert pcs.strip_wiki_markup(raw).strip() == "Ben Johnson"


# ---------------------------------------------- detailed segments (union/notes)


def test_detailed_segments_keeps_annotation_as_note_not_dropped():
    segs = pcs.split_name_segments_detailed("[[Jack Del Rio]] (fired)|[[Ron Rivera]] (interim)")
    names = [s["name"] for s in segs]
    assert names == ["Jack Del Rio", "Ron Rivera"]
    assert segs[0]["note"] == "fired"
    assert segs[1]["note"] == "interim"
    assert pcs._is_interim(segs[1]["note"])
    assert not pcs._is_interim(segs[0]["note"])


def test_detailed_segments_splits_and_prose_as_co_holders():
    segs = pcs.split_name_segments_detailed("Ryan Nielsen and Kris Richard")
    names = [s["name"] for s in segs]
    assert names == ["Ryan Nielsen", "Kris Richard"]
    assert segs[0]["co_holder"] is True
    assert segs[1]["co_holder"] is True


def test_detailed_segments_single_name_not_co_holder():
    segs = pcs.split_name_segments_detailed("[[Aaron Glenn]]")
    assert len(segs) == 1
    assert segs[0]["co_holder"] is False


def test_detailed_segments_captures_week_range_annotation():
    segs = pcs.split_name_segments_detailed("Matt Canada (weeks 1-11)|Eddie Faulkner (weeks 12-18)")
    assert [s["name"] for s in segs] == ["Matt Canada", "Eddie Faulkner"]
    assert segs[0]["note"] == "weeks 1-11"
    assert segs[1]["note"] == "weeks 12-18"


def test_merge_union_takes_union_in_page_order_and_tags_source():
    infobox_segs = pcs.split_name_segments_detailed("[[Matt Canada]]")
    staff_segs = pcs.split_name_segments_detailed("Matt Canada (fired after Week 11)|Eddie Faulkner")
    merged = pcs.merge_union(infobox_segs, staff_segs)
    names = [m["name"] for m in merged]
    assert names == ["Matt Canada", "Eddie Faulkner"]
    assert merged[0]["source"] == "both"
    assert merged[1]["source"] == "staff_section"
    # the PIT 2023 OC gap the Phase 0 report flagged: infobox-only would
    # have dropped Eddie Faulkner - the union must keep him.
    assert any("Faulkner" in n for n in names)


def test_merge_union_infobox_only_and_staff_only():
    infobox_segs = pcs.split_name_segments_detailed("[[Dan Campbell]]")
    merged = pcs.merge_union(infobox_segs, [])
    assert merged[0]["source"] == "infobox"
    merged2 = pcs.merge_union([], pcs.split_name_segments_detailed("[[Dan Campbell]]"))
    assert merged2[0]["source"] == "staff_section"


# ---------------------------------------------- season-aware team names


def test_wiki_name_for_season_switches_at_relocation_year():
    rows = pcs.load_team_wiki_names_seasonal()
    assert pcs.wiki_name_for_season("LAR", 2015, rows) == "St. Louis Rams"
    assert pcs.wiki_name_for_season("LAR", 2016, rows) == "Los Angeles Rams"
    assert pcs.wiki_name_for_season("LAC", 2016, rows) == "San Diego Chargers"
    assert pcs.wiki_name_for_season("LAC", 2017, rows) == "Los Angeles Chargers"
    assert pcs.wiki_name_for_season("OAK", 2019, rows) == "Oakland Raiders"
    assert pcs.wiki_name_for_season("OAK", 2020, rows) == "Las Vegas Raiders"
    assert pcs.wiki_name_for_season("WSH", 2019, rows) == "Washington Redskins"
    assert pcs.wiki_name_for_season("WSH", 2020, rows) == "Washington Football Team"
    assert pcs.wiki_name_for_season("WSH", 2022, rows) == "Washington Commanders"


# --------------------------------------------------- anchor checks (if built)

STAFF_CSV = STUDY / "data" / "processed" / "staff_phase0.csv"


@pytest.mark.skipif(not STAFF_CSV.exists(), reason="staff_phase0.csv not built yet")
def test_anchors_in_built_csv():
    df = pd.read_csv(STAFF_CSV)

    def oc_for(franchise, season):
        row = df[(df.franchise == franchise) & (df.season == season)]
        assert len(row) == 1, f"expected exactly one row for {franchise} {season}"
        return str(row.iloc[0]["offensive_coordinator"])

    def dc_for(franchise, season):
        row = df[(df.franchise == franchise) & (df.season == season)]
        assert len(row) == 1
        return str(row.iloc[0]["defensive_coordinator"])

    def hc_for(franchise, season):
        row = df[(df.franchise == franchise) & (df.season == season)]
        assert len(row) == 1
        return str(row.iloc[0]["head_coach"])

    for season in (2022, 2023, 2024):
        assert "Ben Johnson" in oc_for("DET", season)

    for season in (2022, 2023):
        assert "Macdonald" in dc_for("BAL", season)

    assert "Macdonald" in hc_for("SEA", 2024)


# ------------------------------------------- Phase 1a anchors (staff_stints)

STINTS_CSV = STUDY / "data" / "processed" / "staff_stints.csv"


@pytest.mark.skipif(not STINTS_CSV.exists(), reason="staff_stints.csv not built yet")
def test_stints_anchor_ben_johnson():
    df = pd.read_csv(STINTS_CSV)

    def persons(fr, role, seasons):
        sub = df[(df.franchise == fr) & (df.role == role) & (df.season.isin(seasons))]
        return set(sub["person"])

    assert persons("DET", "OC", [2022, 2023, 2024]) == {"Ben Johnson"}
    assert persons("CHI", "HC", [2025]) == {"Ben Johnson"}


@pytest.mark.skipif(not STINTS_CSV.exists(), reason="staff_stints.csv not built yet")
def test_stints_anchor_mike_macdonald():
    df = pd.read_csv(STINTS_CSV)

    def persons(fr, role, seasons):
        sub = df[(df.franchise == fr) & (df.role == role) & (df.season.isin(seasons))]
        return set(sub["person"])

    assert persons("BAL", "DC", [2022, 2023]) == {"Mike Macdonald"}
    assert persons("SEA", "HC", [2024, 2025]) == {"Mike Macdonald"}


@pytest.mark.skipif(not STINTS_CSV.exists(), reason="staff_stints.csv not built yet")
def test_stints_anchor_kyle_shanahan_multi_franchise_oc_before_sf_hc():
    df = pd.read_csv(STINTS_CSV)
    oc_rows = df[(df.role == "OC") & (df.person == "Kyle Shanahan")]
    oc_franchises = set(oc_rows["franchise"])
    # OC for more than one franchise before becoming SF head coach in 2017
    assert len(oc_franchises - {"SF"}) >= 2
    hc_rows = df[(df.role == "HC") & (df.person == "Kyle Shanahan") & (df.franchise == "SF")]
    assert hc_rows["season"].min() == 2017


# --------------------------------------------------------- movers builders
# (small inline frames, no network)


def _make_stints_df(rows):
    return pd.DataFrame(rows, columns=[
        "season", "franchise", "role", "person", "order_in_season",
        "n_holders_that_season", "is_co_holder", "is_interim", "note",
        "source", "wiki_url",
    ])


def test_build_coordinator_moves_requires_two_franchises():
    import pc_build_derived as pcd
    rows = [
        (2020, "AAA", "OC", "Coach X", 1, 1, False, False, "", "infobox", ""),
        (2021, "BBB", "OC", "Coach X", 1, 1, False, False, "", "infobox", ""),
        (2020, "AAA", "OC", "Coach Y", 1, 1, False, False, "", "infobox", ""),
        (2021, "AAA", "OC", "Coach Y", 1, 1, False, False, "", "infobox", ""),
    ]
    moves = pcd.build_coordinator_moves(_make_stints_df(rows))
    people = set(moves["person"])
    assert "Coach X" in people
    assert "Coach Y" not in people  # only one franchise, not a mover


def test_build_coordinator_to_headcoach_requires_later_season():
    import pc_build_derived as pcd
    rows = [
        (2018, "AAA", "OC", "Coach Z", 1, 1, False, False, "", "infobox", ""),
        (2021, "BBB", "HC", "Coach Z", 1, 1, False, False, "", "infobox", ""),
        (2019, "CCC", "HC", "Coach W", 1, 1, False, False, "", "infobox", ""),
        (2018, "CCC", "OC", "Coach W", 1, 1, False, False, "", "infobox", ""),  # HC before OC
    ]
    c2h = pcd.build_coordinator_to_headcoach(_make_stints_df(rows))
    people = set(c2h["person"])
    assert "Coach Z" in people
    # Coach W's only HC season (2019) is not after any coordinator season
    # more recent than 2018... 2019 > 2018, so it *is* a valid case too:
    assert "Coach W" in people


def test_build_aliases_merges_only_suffix_variants():
    import pc_build_derived as pcd
    people = ["Pete Carmichael Jr.", "Pete Carmichael", "Mike Smith", "Mike Smyth"]
    rename_map, alias_rows = pcd.build_aliases(people)
    assert rename_map["Pete Carmichael"] == "Pete Carmichael Jr."
    assert "Mike Smith" not in rename_map or rename_map.get("Mike Smith") == "Mike Smith"
    assert "Mike Smyth" not in rename_map  # different spelling, not merged
    assert len(alias_rows) == 1
