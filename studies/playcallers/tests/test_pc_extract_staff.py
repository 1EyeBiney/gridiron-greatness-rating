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
