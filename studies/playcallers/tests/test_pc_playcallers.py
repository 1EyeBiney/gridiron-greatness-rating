"""Tests for Phase 1b: evidence mining and the play-caller draft builder."""
from pathlib import Path

from pc_playcall_evidence import (
    extract_hits,
    resolve_biography_title,
    sentences_from_wikitext,
    unit_guess,
)
from pc_build_playcaller_draft import (
    build_draft,
    build_review_subset,
    MODEL_KNOWLEDGE_OVERRIDES,
)

STUDY_DIR = Path(__file__).resolve().parents[1]
PROCESSED = STUDY_DIR / "data" / "processed"


# --- sentence extraction on inline snippets ------------------------------

def test_sentences_from_wikitext_splits_and_strips_markup():
    wikitext = "'''Andy Reid''' called the offense. [[Steve Spagnuolo]] ran the defense."
    sentences = sentences_from_wikitext(wikitext)
    assert any("Andy Reid called the offense." in s for s in sentences)
    assert any("Steve Spagnuolo ran the defense." in s for s in sentences)
    assert "'''" not in " ".join(sentences)
    assert "[[" not in " ".join(sentences)


def test_extract_hits_finds_playcalling_sentences():
    sentences = [
        "Andy Reid has called plays for the Chiefs offense since 2013.",
        "This sentence is irrelevant filler about attendance figures.",
        "Bob Smith is the team's signal caller at quarterback.",
    ]
    hits = extract_hits(sentences, ["Andy Reid"])
    assert len(hits) == 1
    assert hits[0]["unit_guess"] == "offense"
    assert "Andy Reid" in hits[0]["persons_mentioned"]


def test_extract_hits_excludes_signal_caller():
    sentences = ["Bob Smith is the team's signal caller."]
    hits = extract_hits(sentences, ["Bob Smith"])
    assert hits == []


def test_extract_hits_truncates_long_sentences_to_400_chars():
    long_sentence = "X " * 300 + "called plays for the defense."
    hits = extract_hits([long_sentence], [])
    assert len(hits) == 1
    assert len(hits[0]["sentence"]) <= 400


def test_unit_guess_offense_defense_unknown():
    assert unit_guess("He called the offensive plays.") == "offense"
    assert unit_guess("He called the defensive plays.") == "defense"
    assert unit_guess("He called plays.") == "unknown"
    # both offense and defense mentioned -> unknown (ambiguous)
    assert unit_guess("He called offensive and defensive plays.") == "unknown"


# --- biography-title validation logic (network-free: bad inputs only) ---

def test_resolve_biography_title_returns_none_for_nonexistent_name(monkeypatch):
    import pc_playcall_evidence as mod

    def fake_fetch(title, lang="en"):
        return None

    monkeypatch.setattr(mod, "fetch_wikitext", fake_fetch)
    assert resolve_biography_title("Zzzznotarealcoachname") is None


def test_resolve_biography_title_rejects_disambiguation_and_non_coach_pages(monkeypatch):
    import pc_playcall_evidence as mod

    calls = []

    def fake_fetch(title, lang="en"):
        calls.append(title)
        if title == "John Smith":
            return ("'''John Smith''' may refer to:", "https://en.wikipedia.org/wiki/John_Smith")
        if title == "John Smith (American football)":
            return (
                "'''John Smith''' is a mathematician who studies football statistics academically.",
                "https://en.wikipedia.org/wiki/John_Smith_(American_football)",
            )
        if title == "John Smith (American football coach)":
            return (
                "'''John Smith''' is an American football coach.",
                "https://en.wikipedia.org/wiki/John_Smith_(American_football_coach)",
            )
        return None

    monkeypatch.setattr(mod, "fetch_wikitext", fake_fetch)
    result = resolve_biography_title("John Smith")
    assert result is not None
    _, url = result
    assert url.endswith("(American_football_coach)")


# --- draft builder on small inline frames --------------------------------

def _stint(season, franchise, role, person, order=1, n=1):
    return {
        "season": str(season), "franchise": franchise, "role": role,
        "person": person, "order_in_season": str(order),
        "n_holders_that_season": str(n), "is_co_holder": "False",
        "is_interim": "False", "note": "", "source": "infobox",
        "wiki_url": "https://en.wikipedia.org/wiki/test",
    }


def test_build_draft_default_coordinator_case():
    stints = [
        _stint(2015, "JAX", "HC", "Bruce Arians"),
        _stint(2015, "JAX", "OC", "Harold Goodwin"),
        _stint(2015, "JAX", "DC", "James Bettcher"),
    ]
    rows = build_draft(stints, [])
    off = [r for r in rows if r["season"] == 2015 and r["franchise"] == "JAX" and r["unit"] == "offense"][0]
    assert off["basis"] == "default_coordinator"
    assert off["proposed_playcaller"] == "Harold Goodwin"
    assert off["confidence"] != "high"


def test_build_draft_no_coordinator_case():
    stints = [_stint(2011, "ARI", "HC", "Ken Whisenhunt")]
    rows = build_draft(stints, [])
    off = [r for r in rows if r["unit"] == "offense"][0]
    de = [r for r in rows if r["unit"] == "defense"][0]
    assert off["basis"] == "default_no_coordinator_headcoach"
    assert off["proposed_playcaller"] == "Ken Whisenhunt"
    assert de["basis"] == "default_no_coordinator_headcoach"
    assert off["coordinator"] == ""


def test_build_draft_evidence_override_case():
    stints = [
        _stint(2017, "KC", "HC", "Andy Reid"),
        _stint(2017, "KC", "OC", "Matt Nagy"),
        _stint(2017, "KC", "DC", "Bob Sutton"),
    ]
    evidence = [{
        "evidence_id": "1", "season": "2017", "franchise": "KC",
        "page_title": "2017 Kansas City Chiefs season",
        "url": "https://en.wikipedia.org/wiki/2017_Kansas_City_Chiefs_season",
        "sentence": "Andy Reid gave play calling duties to Matt Nagy.",
        "persons_mentioned": "Matt Nagy", "unit_guess": "offense",
        "source_type": "team_season_page",
    }]
    rows = build_draft(stints, evidence)
    off = [r for r in rows if r["season"] == 2017 and r["franchise"] == "KC" and r["unit"] == "offense"][0]
    assert off["basis"] == "evidence_wikipedia"
    assert off["proposed_playcaller"] == "Matt Nagy"
    assert off["evidence_ids"] == "1"


def test_build_draft_model_knowledge_override_never_high_confidence():
    stints = [
        _stint(2020, "KC", "HC", "Andy Reid"),
        _stint(2020, "KC", "OC", "Eric Bieniemy"),
        _stint(2020, "KC", "DC", "Steve Spagnuolo"),
    ]
    rows = build_draft(stints, [])
    off = [r for r in rows if r["unit"] == "offense"][0]
    assert off["basis"] == "model_knowledge_unverified"
    assert off["confidence"] in ("low", "medium")
    assert off["proposed_playcaller"] == "Andy Reid"
    assert "needs a source" in off["note"].lower() or "needs a source" in off["note"]


def test_no_model_knowledge_override_is_ever_high_confidence():
    # Directly enforce the hard rule across every hand-entered override,
    # independent of any specific test franchise/season.
    for _, _, _, confidence, note in MODEL_KNOWLEDGE_OVERRIDES:
        assert confidence in ("low", "medium")
        assert "needs a source" in note.lower()


def test_build_draft_midseason_change_flagged():
    stints = [
        _stint(2015, "TEN", "HC", "Ken Whisenhunt", order=1, n=2),
        _stint(2015, "TEN", "HC", "Mike Mularkey", order=2, n=2),
        _stint(2015, "TEN", "OC", "Jason Michael"),
        _stint(2015, "TEN", "DC", "Ray Horton"),
    ]
    rows = build_draft(stints, [])
    off = [r for r in rows if r["unit"] == "offense"][0]
    assert off["midseason_change"] is True


def test_review_subset_includes_no_coordinator_and_overrides_only():
    stints = [
        _stint(2015, "JAX", "HC", "Bruce Arians"),
        _stint(2015, "JAX", "OC", "Harold Goodwin"),
        _stint(2015, "JAX", "DC", "James Bettcher"),
        _stint(2011, "ARI", "HC", "Ken Whisenhunt"),
    ]
    rows = build_draft(stints, [])
    review = build_review_subset(rows, [])
    # 2015 JAX is a plain default_coordinator case on both units - excluded.
    assert not any(r["season"] == 2015 for r in review)
    # 2011 ARI has no coordinator on either unit - included.
    assert any(r["season"] == 2011 for r in review)


# --- checks against the real files, if present ---------------------------

def test_real_draft_has_one_row_per_unit_season_if_present():
    path = PROCESSED / "playcaller_draft.csv"
    if not path.exists():
        return
    import csv
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2 * (31 * 3 + 32 * 24)      # 1999-2001 had 31 teams


def test_real_draft_proposed_playcaller_never_missing_unless_both_missing():
    path = PROCESSED / "playcaller_draft.csv"
    if not path.exists():
        return
    import csv
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if not r["proposed_playcaller"]:
            assert not r["head_coach"] and not r["coordinator"]


def test_real_draft_evidence_ids_refer_to_existing_evidence_rows():
    draft_path = PROCESSED / "playcaller_draft.csv"
    evidence_path = PROCESSED / "playcall_evidence.csv"
    if not draft_path.exists() or not evidence_path.exists():
        return
    import csv
    with open(evidence_path, encoding="utf-8") as f:
        evidence_ids = {row["evidence_id"] for row in csv.DictReader(f)}
    with open(draft_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        ids = [e for e in r["evidence_ids"].split(" | ") if e]
        for eid in ids:
            assert eid in evidence_ids


def test_continuity_guess_fills_a_gap_between_two_seasons_of_the_same_coordinator():
    stints = [
        _stint(2003, "IND", "HC", "Head Coach"), _stint(2004, "IND", "HC", "Head Coach"),
        _stint(2005, "IND", "HC", "Head Coach"),
        _stint(2003, "IND", "OC", "Steady Hand"), _stint(2005, "IND", "OC", "Steady Hand"),
        _stint(2003, "IND", "DC", "First Man"), _stint(2005, "IND", "DC", "Second Man"),
    ]
    rows = {(r["season"], r["unit"]): r for r in build_draft(stints, []) if r["franchise"] == "IND"}
    off = rows[(2004, "offense")]
    assert off["proposed_playcaller"] == "Steady Hand" and off["basis"] == "continuity_guess"
    assert off["confidence"] == "low"
    de = rows[(2004, "defense")]                      # different men before and after: no guess
    assert de["basis"] == "default_no_coordinator_headcoach" and de["proposed_playcaller"] == "Head Coach"
