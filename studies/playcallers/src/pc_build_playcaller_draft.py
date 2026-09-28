"""Phase 1b Task 3-4: build the draft play-caller table with evidence.

Reads data/processed/staff_stints.csv (title holders) and
data/processed/playcall_evidence.csv (mined sentences), writes
data/processed/playcaller_draft.csv (one row per season/franchise/unit,
2011-2025, 960 rows) and data/reference/playcaller_overrides_for_review.csv
(the subset a human should look at).

Hard rule (from the task): a model-knowledge override is never confidence
"high", and its note must say what is believed and that it needs a source.
"""
from __future__ import annotations

import csv
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent.parent
PROCESSED = STUDY_DIR / "data" / "processed"
REFERENCE = STUDY_DIR / "data" / "reference"

SEASONS = list(range(1999, 2026))
FRANCHISES = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN",
    "DET", "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "MIA",
    "MIN", "NE", "NO", "NYG", "NYJ", "OAK", "PHI", "PIT", "SEA",
    "SF", "TB", "TEN", "WSH",
]

UNIT_ROLE = {"offense": "OC", "defense": "DC"}


def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- Model-knowledge overrides (reviewer's outside NFL knowledge) -------
# Every entry here is UNVERIFIED against a Wikipedia source: confidence is
# capped at "medium", never "high", and the note says what is believed and
# that it needs a source, per the task's hard rule. franchise/season use
# this study's franchise codes and the 2011-2025 window; seasons outside
# that range, or seasons with a mid-season head-coach change (ambiguous),
# are left out deliberately rather than guessed at.
MODEL_KNOWLEDGE_OVERRIDES = [
    # (franchise, unit, seasons, confidence, note)
    ("KC", "offense", list(range(2013, 2026)), "medium",
     "Believed: Andy Reid calls Kansas City's offensive plays as head "
     "coach for his entire KC tenure (2013-2025), as he did earlier at "
     "Philadelphia. Widely reported in NFL media but not sourced to a "
     "specific Wikipedia citation here - needs a source."),
    ("LAR", "offense", list(range(2017, 2026)), "medium",
     "Believed: Sean McVay calls the Rams' offensive plays as head coach "
     "for his entire tenure (2017-2025). Widely reported; not sourced to "
     "a specific citation here - needs a source."),
    ("SF", "offense", list(range(2017, 2026)), "medium",
     "Believed: Kyle Shanahan calls San Francisco's offensive plays as "
     "head coach for his entire tenure (2017-2025), consistent with his "
     "offensive-coordinator background. Widely reported; needs a source."),
    ("NO", "offense", [2011, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021], "medium",
     "Believed: Sean Payton calls New Orleans' offensive plays in every "
     "season he is head coach on the sideline. 2012 (Bountygate "
     "suspension) is deliberately excluded here since Payton was not "
     "actively coaching that season. Widely reported; needs a source."),
    ("DEN", "offense", [2023, 2024, 2025], "medium",
     "Believed: Sean Payton calls Denver's offensive plays as head coach "
     "(2023-2025), continuing the pattern from his New Orleans tenure. "
     "Widely reported; needs a source."),
    ("MIA", "offense", list(range(2022, 2026)), "medium",
     "Believed: Mike McDaniel calls Miami's offensive plays as head coach "
     "(2022-2025), consistent with his Shanahan-tree offensive background. "
     "Widely reported; needs a source."),
    ("TB", "defense", list(range(2022, 2026)), "medium",
     "Believed: Todd Bowles calls Tampa Bay's defensive plays as head "
     "coach (2022-2025), continuing the role he held as Tampa Bay's own "
     "defensive coordinator/DC-as-HC in 2019-2021. Widely reported; needs "
     "a source."),
    ("CHI", "defense", [2022, 2023, 2024], "low",
     "Believed: Matt Eberflus, a defensive-background head coach, called "
     "or closely directed Chicago's defensive plays in at least part of "
     "his 2022-2024 tenure, but this study is less sure which seasons "
     "exactly (he also had a titled DC in some of these years) - marked "
     "low confidence rather than medium. Needs a source."),
    ("ATL", "defense", [2015, 2016, 2017, 2018, 2019, 2020], "low",
     "Believed: Dan Quinn, a defensive-background head coach, was closely "
     "involved in calling Atlanta's defense for at least part of his "
     "2015-2020 tenure, but this study is not confident which seasons he "
     "held the play-caller role personally versus deferring to a titled "
     "DC - marked low confidence. Needs a source."),
    ("PHI", "offense", [2016, 2017, 2018], "low",
     "Believed: Doug Pederson called Philadelphia's offensive plays for "
     "at least part of his 2016-2018 tenure, with public reporting "
     "suggesting the arrangement changed across those seasons (and that "
     "he later handed the duty off, per general reporting after this "
     "window). This study is not confident about which exact seasons - "
     "marked low confidence. Needs a source."),
    ("MIA", "defense", [2019, 2020, 2021], "medium",
     "Believed: Brian Flores, a defensive-background head coach, was "
     "closely involved in calling Miami's defense in his 2019-2021 "
     "tenure. Widely reported; needs a source."),
]



# Candidates added by the reviewing model (Fable), 2026-09-27. Same status as the rows above:
# unverified, never 'high', for Brian's review.
MODEL_KNOWLEDGE_OVERRIDES += [
    ('CHI', 'offense', [2025], 'medium', "Added in review. Believed: Ben Johnson called Chicago's offensive plays as head coach. Not sourced; needs a source."),
    ('CHI', 'offense', [2018, 2019], 'medium', "Added in review. Believed: Matt Nagy called Chicago's offensive plays as head coach (he handed off for parts of 2020 and 2021, which are left at the default). Not sourced; needs a source."),
    ('SEA', 'defense', [2024, 2025], 'medium', "Added in review. Believed: Mike Macdonald called Seattle's defensive plays as head coach. Not sourced; needs a source."),
    ('DET', 'offense', [2025], 'low', "Added in review. Believed: Dan Campbell called Detroit's offensive plays as head coach for the later part of 2025 after taking over from the coordinator; a mid-season change that needs a date. Not sourced; needs a source."),
    ('GB', 'offense', [2019, 2020, 2021, 2022, 2023, 2024, 2025], 'medium', "Added in review. Believed: Matt LaFleur called Green Bay's offensive plays as head coach. Not sourced; needs a source."),
    ('CIN', 'offense', [2019, 2020, 2021, 2022, 2023, 2024, 2025], 'medium', "Added in review. Believed: Zac Taylor called Cincinnati's offensive plays as head coach. Not sourced; needs a source."),
    ('MIN', 'offense', [2022, 2023, 2024, 2025], 'medium', "Added in review. Believed: Kevin O'Connell called Minnesota's offensive plays as head coach. Not sourced; needs a source."),
    ('MIN', 'defense', [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021], 'medium', "Added in review. Believed: Mike Zimmer called Minnesota's defensive plays as head coach. Not sourced; needs a source."),
    ('CLE', 'offense', [2020, 2021, 2022, 2023], 'medium', "Added in review. Believed: Kevin Stefanski called Cleveland's offensive plays as head coach (2024 and 2025 involved hand-offs and are left to the evidence or default). Not sourced; needs a source."),
    ('IND', 'offense', [2018, 2019, 2020, 2021, 2022], 'medium', "Added in review. Believed: Frank Reich called Indianapolis's offensive plays as head coach until his dismissal during 2022. Not sourced; needs a source."),
    ('IND', 'offense', [2023, 2024, 2025], 'medium', "Added in review. Believed: Shane Steichen called Indianapolis's offensive plays as head coach. Not sourced; needs a source."),
    ('ARI', 'offense', [2013, 2014, 2015, 2016, 2017], 'medium', "Added in review. Believed: Bruce Arians called Arizona's offensive plays as head coach. Not sourced; needs a source."),
    ('ARI', 'offense', [2019, 2020, 2021, 2022], 'medium', "Added in review. Believed: Kliff Kingsbury called Arizona's offensive plays as head coach. Not sourced; needs a source."),
    ('OAK', 'offense', [2018, 2019, 2020, 2021], 'medium', "Added in review. Believed: Jon Gruden called the Raiders's offensive plays as head coach until his resignation during 2021. Not sourced; needs a source."),
    ('OAK', 'offense', [2022, 2023], 'medium', "Added in review. Believed: Josh McDaniels called the Raiders's offensive plays as head coach until his dismissal during 2023. Not sourced; needs a source."),
    ('DAL', 'offense', [2023, 2024], 'medium', "Added in review. Believed: Mike McCarthy called Dallas's offensive plays as head coach. Not sourced; needs a source."),
    ('DAL', 'offense', [2025], 'low', "Added in review. Believed: Brian Schottenheimer called Dallas's offensive plays as head coach. Not sourced; needs a source."),
    ('PHI', 'offense', [2013, 2014, 2015], 'medium', "Added in review. Believed: Chip Kelly called Philadelphia's offensive plays as head coach. Not sourced; needs a source."),
    ('TEN', 'offense', [2024, 2025], 'low', "Added in review. Believed: Brian Callahan called Tennessee's offensive plays as head coach until his dismissal during 2025. Not sourced; needs a source."),
    ('CAR', 'offense', [2024, 2025], 'medium', "Added in review. Believed: Dave Canales called Carolina's offensive plays as head coach. Not sourced; needs a source."),
    ('ATL', 'offense', [2021, 2022, 2023], 'medium', "Added in review. Believed: Arthur Smith called Atlanta's offensive plays as head coach. Not sourced; needs a source."),
    ('JAX', 'offense', [2025], 'low', "Added in review. Believed: Liam Coen called Jacksonville's offensive plays as head coach. Not sourced; needs a source."),
    ('NYJ', 'offense', [2019], 'medium', "Added in review. Believed: Adam Gase called the Jets's offensive plays as head coach. Not sourced; needs a source."),
    ('NYJ', 'defense', [2015, 2016, 2017, 2018], 'medium', "Added in review. Believed: Todd Bowles called the Jets's defensive plays as head coach. Not sourced; needs a source."),
    ('NYG', 'offense', [2024], 'low', "Added in review. Believed: Brian Daboll called the Giants's offensive plays as head coach in 2024 after the coordinator called plays in 2022 and 2023. Not sourced; needs a source."),
    ('BUF', 'defense', [2023], 'medium', "Added in review. Believed: Sean McDermott called Buffalo's defensive plays as head coach in 2023, when the team had no titled coordinator. Not sourced; needs a source."),
    ('LAC', 'defense', [2021, 2022, 2023], 'medium', "Added in review. Believed: Brandon Staley called the Chargers's defensive plays as head coach until his dismissal during 2023. Not sourced; needs a source."),
    ('DEN', 'defense', [2019, 2020, 2021], 'medium', "Added in review. Believed: Vic Fangio called Denver's defensive plays as head coach. Not sourced; needs a source."),
    ('NO', 'defense', [2022, 2023, 2024], 'low', "Added in review. Believed: Dennis Allen called New Orleans's defensive plays as head coach until his dismissal during 2024. Not sourced; needs a source."),
    ('HOU', 'defense', [2023, 2024, 2025], 'low', "Added in review. Believed: DeMeco Ryans called Houston's defensive plays as head coach. Not sourced; needs a source."),
]

# Known case the head-coach override cannot express: New England 2022 had no titled offensive
# coordinator and the plays are believed to have been called by an assistant (Matt Patricia), not
# the head coach. It stays at the no-coordinator default and is flagged in docs/PHASE1B_REVIEW.md.



# Candidates for the older seasons, added by the reviewing model (Fable), 2026-09-28.
# Same status as every row here: unverified belief, never 'high'.
MODEL_KNOWLEDGE_OVERRIDES += [
    ('LAR', 'offense', [2000, 2001, 2002, 2003, 2004, 2005], 'medium', "Added in review for 1999-2010. Believed: Mike Martz called the Rams's offensive plays as head coach. Not sourced; needs a source."),
    ('SEA', 'offense', [1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008], 'medium', "Added in review for 1999-2010. Believed: Mike Holmgren called Seattle's offensive plays as head coach. Not sourced; needs a source."),
    ('DEN', 'offense', [1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008], 'medium', "Added in review for 1999-2010. Believed: Mike Shanahan called Denver's offensive plays as head coach. Not sourced; needs a source."),
    ('OAK', 'offense', [1999, 2000, 2001], 'medium', "Added in review for 1999-2010. Believed: Jon Gruden called Oakland's offensive plays as head coach. Not sourced; needs a source."),
    ('TB', 'offense', [2002, 2003, 2004, 2005, 2006, 2007, 2008], 'medium', "Added in review for 1999-2010. Believed: Jon Gruden called Tampa Bay's offensive plays as head coach. Not sourced; needs a source."),
    ('PHI', 'offense', [1999, 2000, 2001, 2002, 2003, 2004, 2005], 'medium', "Added in review for 1999-2010. Believed: Andy Reid called Philadelphia's offensive plays as head coach through 2005; he is believed to have handed off during 2006, so later seasons stay at the default. Not sourced; needs a source."),
    ('NO', 'offense', [2006, 2007, 2008, 2009, 2010], 'medium', "Added in review for 1999-2010. Believed: Sean Payton called New Orleans's offensive plays as head coach. Not sourced; needs a source."),
    ('LAC', 'offense', [2007, 2008, 2009, 2010, 2011, 2012], 'medium', "Added in review for 1999-2010. Believed: Norv Turner called San Diego's offensive plays as head coach. Not sourced; needs a source."),
    ('GB', 'offense', [2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2016, 2017, 2018], 'medium', "Added in review for 1999-2010. Believed: Mike McCarthy called Green Bay's offensive plays as head coach (2015, when he is believed to have handed off for most of the season, stays at the default). Not sourced; needs a source."),
    ('HOU', 'offense', [2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013], 'medium', "Added in review for 1999-2010. Believed: Gary Kubiak called Houston's offensive plays as head coach. Not sourced; needs a source."),
    ('DEN', 'offense', [2015, 2016], 'medium', "Added in review for 1999-2010. Believed: Gary Kubiak called Denver's offensive plays as head coach. Not sourced; needs a source."),
    ('WSH', 'offense', [2002, 2003], 'medium', "Added in review for 1999-2010. Believed: Steve Spurrier called Washington's offensive plays as head coach. Not sourced; needs a source."),
    ('DAL', 'offense', [2011, 2012], 'medium', "Added in review for 1999-2010. Believed: Jason Garrett called Dallas's offensive plays as head coach. Not sourced; needs a source."),
    ('CHI', 'offense', [2013, 2014], 'medium', "Added in review for 1999-2010. Believed: Marc Trestman called Chicago's offensive plays as head coach. Not sourced; needs a source."),
    ('BUF', 'offense', [2010, 2011, 2012], 'medium', "Added in review for 1999-2010. Believed: Chan Gailey called Buffalo's offensive plays as head coach. Not sourced; needs a source."),
    ('OAK', 'offense', [2011], 'low', "Added in review for 1999-2010. Believed: Hue Jackson called Oakland's offensive plays as head coach. Not sourced; needs a source."),
    ('TEN', 'offense', [2014, 2015], 'low', "Added in review for 1999-2010. Believed: Ken Whisenhunt called Tennessee's offensive plays as head coach. Not sourced; needs a source."),
    ('BAL', 'offense', [2007], 'low', "Added in review for 1999-2010. Believed: Brian Billick called Baltimore's offensive plays as head coach in 2007 after taking over during 2006. Not sourced; needs a source."),
    ('NYJ', 'defense', [2009, 2010, 2011, 2012, 2013, 2014], 'medium', "Added in review for 1999-2010. Believed: Rex Ryan called the Jets's defensive plays as head coach. Not sourced; needs a source."),
    ('BUF', 'defense', [2015, 2016], 'low', "Added in review for 1999-2010. Believed: Rex Ryan called Buffalo's defensive plays as head coach. Not sourced; needs a source."),
    ('DAL', 'defense', [2007, 2008, 2009, 2010], 'medium', "Added in review for 1999-2010. Believed: Wade Phillips called Dallas's defensive plays as head coach. Not sourced; needs a source."),
]

def build_model_knowledge_index():
    idx = {}
    for franchise, unit, seasons, confidence, note in MODEL_KNOWLEDGE_OVERRIDES:
        for season in seasons:
            idx[(season, franchise, unit)] = (confidence, note)
    return idx


def index_stints(stints: list[dict]) -> dict:
    """(season, franchise, role) -> list of stint rows, in order_in_season order."""
    idx: dict[tuple, list[dict]] = {}
    for row in stints:
        key = (int(row["season"]), row["franchise"], row["role"])
        idx.setdefault(key, []).append(row)
    for key in idx:
        idx[key].sort(key=lambda r: int(r["order_in_season"]))
    return idx


def index_evidence(evidence: list[dict]) -> dict:
    """(season, franchise) -> list of (evidence_id, row) for team_season_page
    evidence with a usable season+franchise (biography rows often lack one
    or the other and are not indexed here)."""
    idx: dict[tuple, list[tuple]] = {}
    for row in evidence:
        if row["source_type"] != "team_season_page":
            continue
        if not row["season"] or not row["franchise"]:
            continue
        key = (int(row["season"]), row["franchise"])
        idx.setdefault(key, []).append((row["evidence_id"], row))
    return idx


def names_str(rows: list[dict]) -> str:
    return " | ".join(r["person"] for r in rows)


CONTINUITY_WINDOW = 3


def continuity_guess(stint_idx: dict, season: int, franchise: str, role: str) -> str | None:
    """When a team-season lists nobody in a role, guess the man who held it
    both before and after. If the nearest earlier season (within
    CONTINUITY_WINDOW years) and the nearest later one each list a single
    holder and it is the same person, he is the guess. A guess, not a
    finding: the basis is `continuity_guess` and the confidence is low."""
    def nearest(step: int) -> str | None:
        for k in range(1, CONTINUITY_WINDOW + 1):
            rows = stint_idx.get((season + step * k, franchise, role), [])
            if rows:
                return rows[0]["person"] if len(rows) == 1 else None
        return None
    before, after = nearest(-1), nearest(+1)
    return before if before and before == after else None


def build_draft(stints: list[dict], evidence: list[dict]) -> list[dict]:
    stint_idx = index_stints(stints)
    evidence_idx = index_evidence(evidence)
    model_idx = build_model_knowledge_index()

    out = []
    for season in SEASONS:
        for franchise in FRANCHISES:
            hc_rows = stint_idx.get((season, franchise, "HC"), [])
            if not hc_rows:
                continue  # franchise code not in play that season (relocations)
            head_coach = names_str(hc_rows)
            hc_midseason = len(hc_rows) > 1

            for unit in ("offense", "defense"):
                role = UNIT_ROLE[unit]
                coord_rows = stint_idx.get((season, franchise, role), [])
                coordinator = names_str(coord_rows)
                coord_midseason = len(coord_rows) > 1

                if coord_rows:
                    default_playcaller = coordinator
                    basis = "default_coordinator"
                    confidence = "medium"
                    note = (f"Default assumption: the titled {role} calls "
                            f"{unit} plays. Not evidence-verified.")
                else:
                    guess = continuity_guess(stint_idx, season, franchise, role)
                    if guess:
                        default_playcaller = guess
                        basis = "continuity_guess"
                        confidence = "low"
                        note = (f"No titled {role} found for this team-season; {guess} held the "
                                f"title for this team both before and after, so he is assumed to "
                                f"have held it here too. A guess; needs a source.")
                    else:
                        default_playcaller = head_coach
                        basis = "default_no_coordinator_headcoach"
                        confidence = "low"
                        note = (f"No titled {role} found for this team-season; "
                                f"defaulting to the head coach as {unit} "
                                f"play-caller. Not evidence-verified, and not used in "
                                f"the ratings unless an override names him.")

                proposed_playcaller = default_playcaller
                evidence_ids: list[str] = []
                midseason_change = hc_midseason or coord_midseason

                # 1) Wikipedia evidence (team-season page mining), if any
                # hits for this season/franchise/unit exist.
                hits = [
                    (eid, r) for eid, r in evidence_idx.get((season, franchise), [])
                    if r["unit_guess"] == unit
                ]
                if hits:
                    # Prefer a hit whose persons_mentioned overlaps the
                    # current default holder(s) or head coach - otherwise
                    # take the first hit's mentioned person(s) as the
                    # proposed override.
                    eid, r = hits[0]
                    mentioned = [n.strip() for n in r["persons_mentioned"].split("|") if n.strip()]
                    if mentioned:
                        proposed_playcaller = " | ".join(mentioned)
                        basis = "evidence_wikipedia"
                        confidence = "high" if len(mentioned) == 1 else "medium"
                        note = (f"Wikipedia team-season page states: "
                                f"\"{r['sentence']}\" (evidence id {eid}).")
                        evidence_ids.append(str(eid))
                    for extra_eid, extra_r in hits[1:]:
                        evidence_ids.append(str(extra_eid))

                # 2) Model-knowledge override, only if no Wikipedia evidence
                # already resolved this row, and only when it doesn't
                # coincide with a mid-season coaching change (too ambiguous
                # to assert a season-long play-caller).
                elif (season, franchise, unit) in model_idx and not midseason_change:
                    mk_confidence, mk_note = model_idx[(season, franchise, unit)]
                    hc_names = [r["person"] for r in hc_rows]
                    # Only apply if the believed play-caller is in fact this
                    # season's (sole) head coach, matching how each entry
                    # above was written.
                    proposed_playcaller = hc_names[0]
                    basis = "model_knowledge_unverified"
                    confidence = mk_confidence
                    note = mk_note

                out.append({
                    "season": season,
                    "franchise": franchise,
                    "unit": unit,
                    "head_coach": head_coach,
                    "coordinator": coordinator,
                    "default_playcaller": default_playcaller,
                    "proposed_playcaller": proposed_playcaller,
                    "basis": basis,
                    "confidence": confidence,
                    "evidence_ids": " | ".join(evidence_ids),
                    "midseason_change": midseason_change,
                    "note": note,
                })
    return out


DRAFT_FIELDS = [
    "season", "franchise", "unit", "head_coach", "coordinator",
    "default_playcaller", "proposed_playcaller", "basis", "confidence",
    "evidence_ids", "midseason_change", "note",
]


def write_draft_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DRAFT_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


REVIEW_FIELDS = DRAFT_FIELDS + ["reviewer_decision", "reviewer_note"]


def build_review_subset(draft_rows: list[dict], evidence: list[dict]) -> list[dict]:
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    review = []
    for row in draft_rows:
        differs = row["proposed_playcaller"] != row["coordinator"] if row["coordinator"] else row["proposed_playcaller"] != row["default_playcaller"]
        no_coordinator = not row["coordinator"]
        if not (differs or row["midseason_change"] or no_coordinator):
            continue
        r = dict(row)
        # Inline evidence sentence/url for the first evidence id, if any.
        eids = [e for e in row["evidence_ids"].split(" | ") if e]
        if eids:
            ev = evidence_by_id.get(eids[0])
            if ev:
                r["evidence_sentence"] = ev["sentence"]
                r["evidence_url"] = ev["url"]
            else:
                r["evidence_sentence"] = ""
                r["evidence_url"] = ""
        else:
            r["evidence_sentence"] = ""
            r["evidence_url"] = ""
        r["reviewer_decision"] = ""
        r["reviewer_note"] = ""
        review.append(r)
    review.sort(key=lambda r: (r["franchise"], r["season"], r["unit"]))
    return review


def write_review_csv(rows: list[dict], path: Path) -> None:
    fields = DRAFT_FIELDS + ["evidence_sentence", "evidence_url", "reviewer_decision", "reviewer_note"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def main():
    stints = load_csv(PROCESSED / "staff_stints_all.csv")
    evidence_path = PROCESSED / "playcall_evidence.csv"
    evidence = load_csv(evidence_path) if evidence_path.exists() else []

    draft = build_draft(stints, evidence)
    write_draft_csv(draft, PROCESSED / "playcaller_draft.csv")
    print(f"playcaller_draft.csv: {len(draft)} rows")

    review = build_review_subset(draft, evidence)
    write_review_csv(review, REFERENCE / "playcaller_overrides_for_review.csv")
    print(f"playcaller_overrides_for_review.csv: {len(review)} rows")

    from collections import Counter
    print("basis counts:", Counter(r["basis"] for r in draft))
    print("confidence counts:", Counter(r["confidence"] for r in draft))


if __name__ == "__main__":
    main()
