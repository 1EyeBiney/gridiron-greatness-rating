"""Phase 0: extract head coach / OC / DC per team-season from Wikipedia
season-page wikitext (infobox + Staff section), and cross-check the head
coach against the nflverse schedule file.

Run from the study folder:
    python src/pc_extract_staff.py --seasons 2022 2023 2024

Writes data/processed/staff_phase0.csv and
data/processed/staff_phase0_headcoach_check.csv.

Every value in these CSVs is copied from a fetched Wikipedia page. No name
is filled in from outside knowledge.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
SRC = STUDY / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
MAIN = STUDY.parents[1]

from pc_wiki_fetch import fetch_wikitext  # noqa: E402

INFOBOX_RE = re.compile(
    r"\{\{\s*Infobox[ _](?:NFL[ _](?:team[ _])?season|gridiron football team season)",
    re.IGNORECASE,
)
STAFF_HEADING_RE = re.compile(r"={2,4}\s*Staff\b[^=\n]*={2,4}", re.IGNORECASE)
STAFF_TEMPLATE_RE = re.compile(r"\{\{\s*NFL (?:final|current) staff", re.IGNORECASE)

# infobox field name -> role
INFOBOX_FIELDS = {
    "coach": "head_coach",
    "head_coach": "head_coach",
    "off_coach": "offensive_coordinator",
    "offensive_coordinator": "offensive_coordinator",
    "oc": "offensive_coordinator",
    "def_coach": "defensive_coordinator",
    "defensive_coordinator": "defensive_coordinator",
    "dc": "defensive_coordinator",
}

# staff-section bullet label (lowercased, text before a "/") -> role
STAFF_LABELS = {
    "head coach": "head_coach",
    "interim head coach": "head_coach",
    "co-head coach": "head_coach",
    "offensive coordinator": "offensive_coordinator",
    "interim offensive coordinator": "offensive_coordinator",
    "co-offensive coordinator": "offensive_coordinator",
    "passing game coordinator/offensive coordinator": "offensive_coordinator",
    "defensive coordinator": "defensive_coordinator",
    "interim defensive coordinator": "defensive_coordinator",
    "co-defensive coordinator": "defensive_coordinator",
}

ROLES = ("head_coach", "offensive_coordinator", "defensive_coordinator")


# --------------------------------------------------------------- cleaning


def strip_wiki_markup(text: str) -> str:
    """Strip refs, comments, wikilinks, bold/italic markup, html tags,
    footnote brackets, and the mojibake dash/'e9' artifacts that show up
    when this environment reads UTF-8 en/em dashes as latin-1. Returns
    plain text with wikilink display text kept."""
    if text is None:
        return ""
    s = text
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)
    s = re.sub(r"<ref[^>]*/>", "", s, flags=re.DOTALL)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.DOTALL)
    s = re.sub(r"<br\s*/?>", " | ", s, flags=re.IGNORECASE)
    # [[A|B]] -> B ; [[A]] -> A
    s = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''?", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[\d+\]", "", s)
    s = s.replace("�", "-")  # mojibake replacement char from bad decode
    s = expand_ubl(s)
    # Drop any other remaining templates outright (e.g. {{winpct|3|5|1|
    # record=y}} inside a "(fired ...; {{winpct|...}} record)" parenthetical
    # note) - their pipes would otherwise be mistaken for name separators.
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = s.strip()
    return s


UBL_RE = re.compile(r"\{\{\s*(?:ubl|unbulleted list|plainlist)\s*\|(.*?)\}\}", re.IGNORECASE | re.DOTALL)


def expand_ubl(s: str) -> str:
    """{{ubl|A|B}} (an unbulleted-list template used inline as a field
    value, e.g. def_coach = {{ubl|[[Jack Del Rio]] (fired)|Ron Rivera
    (interim)}}) -> 'A | B', so the normal '|' split downstream picks up
    each item as its own name segment."""
    def repl(m):
        return m.group(1).replace("|", " | ")
    return UBL_RE.sub(repl, s)


AND_SPLIT_RE = re.compile(
    r"^([A-Z][\w.\'\-]*(?: [A-Z][\w.\'\-]*)+)\s+and\s+([A-Z][\w.\'\-]*(?: [A-Z][\w.\'\-]*)+)$"
)


def split_name_segments_detailed(raw: str) -> list[dict]:
    """Like split_name_segments, but keeps annotations instead of dropping
    them, and splits "X and Y" prose (co-coordinators written as a sentence
    rather than a <br>/pipe-separated list) into two co-holder entries.

    Returns a list of {"name": str, "note": str, "co_holder": bool}. `note`
    is the raw annotation text found for that segment (parentheticals,
    text after a semicolon), joined with " | " if there is more than one.
    `co_holder` is True when two names came from splitting a single "X and
    Y" segment (they held the role at the same time, not one after another).
    """
    cleaned = strip_wiki_markup(raw)
    segments = [seg.strip() for seg in cleaned.split("|") if seg.strip()]
    out: list[dict] = []
    for seg in segments:
        # pull off parenthetical(s) and any trailing "; ..." as notes, but
        # keep them instead of discarding
        notes = []
        for pm in re.finditer(r"\(([^()]*)\)", seg):
            notes.append(pm.group(1).strip())
        name_part = re.sub(r"\(.*?\)", "", seg).strip()
        if ";" in name_part:
            head, _, tail = name_part.partition(";")
            tail = tail.strip()
            if tail:
                notes.append(tail)
            name_part = head.strip()
        name_part = name_part.rstrip(",").strip()
        if not name_part:
            continue
        if name_part[0].islower():
            # an annotation-only segment (leftover italic text), not a name;
            # fold it into the previous entry's note instead of dropping it
            if out:
                out[-1]["note"] = " | ".join([n for n in [out[-1]["note"], name_part] if n])
            continue
        m = AND_SPLIT_RE.match(name_part)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            note = " | ".join(notes)
            out.append({"name": a, "note": note, "co_holder": True})
            out.append({"name": b, "note": note, "co_holder": True})
        else:
            out.append({"name": name_part, "note": " | ".join(notes), "co_holder": False})
    return out


def split_name_segments(raw: str) -> list[str]:
    """Split a raw infobox/staff field on '<br>' (already turned into ' | '
    by strip_wiki_markup) and on literal ' | ' if present in source. Each
    segment may carry a parenthetical note ('(fired November 27...)') which
    is dropped from the name but the whole raw text is kept separately as
    raw_note by the caller."""
    cleaned = strip_wiki_markup(raw)
    segments = [seg.strip() for seg in cleaned.split("|") if seg.strip()]
    names = []
    for seg in segments:
        # drop trailing parenthetical annotation(s)
        name = re.sub(r"\(.*?\)", "", seg).strip()
        name = re.sub(r";.*$", "", name).strip()
        name = name.rstrip(",")
        # drop stray italic annotations left over from a "<br>''resigned on
        # September 20''"-style note once <br> has been split into its own
        # segment: these start with a lowercase word, unlike a real name.
        if name and name[0].islower():
            continue
        if name:
            names.append(name)
    return names


# --------------------------------------------------------------- infobox


def extract_infobox_block(wikitext: str) -> str | None:
    m = INFOBOX_RE.search(wikitext)
    if not m:
        return None
    start = m.start()
    # walk forward counting brace depth from the "{{" at start
    depth = 0
    i = start
    n = len(wikitext)
    while i < n - 1:
        two = wikitext[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
            continue
        if two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return wikitext[start:i]
            continue
        i += 1
    return wikitext[start:]


def parse_infobox_fields(block: str) -> dict[str, str]:
    """Return {role: raw_field_text} for head_coach/offensive_coordinator/
    defensive_coordinator, taken from top-level '| field = value' lines
    (not lines belonging to a nested template like {{Collapsible list}})."""
    if not block:
        return {}
    # Drop the opening "{{Infobox ..." line (its own braces aren't nesting
    # relative to the template's own fields) and stop once the closing
    # brace of the whole infobox is reached (depth would go negative).
    lines = block.split("\n")[1:]
    out: dict[str, str] = {}
    depth = 0
    current_field = None
    current_lines: list[str] = []

    def flush():
        if current_field and current_field.strip().lower() in INFOBOX_FIELDS:
            role = INFOBOX_FIELDS[current_field.strip().lower()]
            value = "\n".join(current_lines).strip()
            if value:
                out.setdefault(role, value)

    for line in lines:
        stripped = line.strip()
        open_braces = stripped.count("{{")
        close_braces = stripped.count("}}")
        if depth + open_braces - close_braces < 0:
            break
        if depth == 0 and stripped.startswith("|") and "=" in stripped:
            flush()
            field, _, value = stripped[1:].partition("=")
            current_field = field.strip()
            current_lines = [value]
        else:
            if depth > 0 or not stripped.startswith("|"):
                current_lines.append(stripped)
        depth += open_braces - close_braces
        if depth < 0:
            depth = 0
    flush()
    return out


# ------------------------------------------------------------ staff section


def extract_staff_block(wikitext: str) -> str | None:
    m = STAFF_HEADING_RE.search(wikitext)
    if not m:
        return None
    rest = wikitext[m.end():]
    tm = STAFF_TEMPLATE_RE.search(rest)
    if not tm:
        return None
    start = tm.start()
    depth = 0
    i = start
    n = len(rest)
    while i < n - 1:
        two = rest[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
            continue
        if two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return rest[start:i]
            continue
        i += 1
    return rest[start:]


def parse_staff_fields(block: str) -> dict[str, list[str]]:
    """Return {role: [raw_bullet_text, ...]} in document order, scanning
    bullet lines '*Label <dash> Name' inside the staff template."""
    if not block:
        return {}
    out: dict[str, list[str]] = {}
    for line in block.split("\n"):
        line = line.strip()
        if not line.startswith("*"):
            continue
        body = line[1:].strip()
        m = re.match(r"^(.*?)\s*[–—�-]\s*(.+)$", body)
        if not m:
            continue
        label_raw, name_raw = m.group(1), m.group(2)
        role = None
        for part in label_raw.split("/"):
            role = STAFF_LABELS.get(part.strip().lower())
            if role is not None:
                break
        if role is None:
            continue
        out.setdefault(role, []).append(name_raw.strip())
    return out


# --------------------------------------------------------------- assembly


def build_team_wiki_names() -> dict[str, str]:
    """Back-compat: single-era mapping, using each franchise's row whose
    valid range covers the highest season present (i.e. its current name),
    for callers that only need one name (there are none left after Phase
    1a, kept only in case older tooling imports this)."""
    rows = load_team_wiki_names_seasonal()
    mapping: dict[str, str] = {}
    for r in rows:
        mapping[r["franchise"]] = r["wiki_team_name"]  # last row wins == latest era
    return mapping


def load_team_wiki_names_seasonal() -> list[dict]:
    path = STUDY / "data" / "reference" / "team_wiki_names.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def wiki_name_for_season(franchise: str, season: int, rows: list[dict]) -> str | None:
    for r in rows:
        if r["franchise"] != franchise:
            continue
        lo, hi = int(r["valid_from_season"]), int(r["valid_to_season"])
        if lo <= season <= hi:
            return r["wiki_team_name"]
    return None


def merge_union(infobox_segs: list[dict], staff_segs: list[dict]) -> list[dict]:
    """Union of infobox and staff-section segments for one role, in page
    order: infobox entries first (in their order), then any staff-section
    entry whose last name isn't already present. Each output entry gets a
    `source` of "infobox", "staff_section", or "both" (name appears, by
    last name, in both lists - notes from both sides are combined)."""

    _suffix_re = re.compile(r"^(Jr\.?|Sr\.?|II|III|IV)$", re.IGNORECASE)

    def lastname(n):
        parts = [p.rstrip(",") for p in n.split()]
        while parts and _suffix_re.match(parts[-1]):
            parts.pop()
        return parts[-1].lower() if parts else n.lower()

    out = []
    seen = {}
    for seg in infobox_segs:
        key = lastname(seg["name"])
        entry = dict(seg, source="infobox")
        out.append(entry)
        seen[key] = entry
    for seg in staff_segs:
        key = lastname(seg["name"])
        if key in seen:
            existing = seen[key]
            existing["source"] = "both"
            if seg["note"] and seg["note"] not in (existing["note"] or ""):
                existing["note"] = " | ".join([n for n in [existing["note"], seg["note"]] if n])
        else:
            entry = dict(seg, source="staff_section")
            out.append(entry)
            seen[key] = entry
    return out


def extract_team_season_v2(season: int, franchise: str, wiki_team_name: str) -> tuple[dict, dict]:
    """Union-based extraction for the 2011-2025 stints table. Returns
    (row_for_staff_by_season_csv, role_segments) where role_segments is
    {role: [merged segment dicts]} for the stints builder."""
    title = f"{season} {wiki_team_name} season"
    fetched = fetch_wikitext(title)
    row = {
        "season": season, "franchise": franchise, "wiki_title": title,
        "wiki_url": "", "head_coach": "", "offensive_coordinator": "",
        "defensive_coordinator": "", "n_hc": 0, "n_oc": 0, "n_dc": 0,
        "source_field": "none", "raw_note": "",
    }
    role_segments: dict[str, list[dict]] = {r: [] for r in ROLES}
    if fetched is None:
        row["raw_note"] = "PAGE NOT FOUND (404)"
        return row, role_segments
    wikitext, url = fetched
    row["wiki_url"] = url

    infobox_block = extract_infobox_block(wikitext)
    infobox_fields = parse_infobox_fields(infobox_block) if infobox_block else {}
    staff_block = extract_staff_block(wikitext)
    staff_fields = parse_staff_fields(staff_block) if staff_block else {}

    raw_notes = []
    sources_used = set()
    for role in ROLES:
        infobox_raw = infobox_fields.get(role)
        infobox_segs = split_name_segments_detailed(infobox_raw) if infobox_raw else []
        staff_raw_list = staff_fields.get(role, [])
        staff_segs = []
        for raw in staff_raw_list:
            staff_segs.extend(split_name_segments_detailed(raw))

        merged = merge_union(infobox_segs, staff_segs)
        role_segments[role] = merged
        for seg in merged:
            sources_used.add(seg["source"])

        col = {"head_coach": "head_coach", "offensive_coordinator": "offensive_coordinator",
               "defensive_coordinator": "defensive_coordinator"}[role]
        row[col] = " | ".join(seg["name"] for seg in merged)
        row[f"n_{'hc' if role == 'head_coach' else ('oc' if role == 'offensive_coordinator' else 'dc')}"] = len(merged)
        if infobox_raw:
            raw_notes.append(f"{role} infobox raw: {infobox_raw.strip()[:200]}")
        if staff_raw_list:
            raw_notes.append(f"{role} staff raw: {' ; '.join(staff_raw_list)[:200]}")

    if sources_used == {"infobox"}:
        row["source_field"] = "infobox"
    elif sources_used == {"staff_section"}:
        row["source_field"] = "staff_section"
    elif sources_used:
        row["source_field"] = "both" if len(sources_used) > 1 else next(iter(sources_used))
    else:
        row["source_field"] = "none"
    row["raw_note"] = " || ".join(raw_notes)
    return row, role_segments


def run_v2(seasons: list[int]) -> tuple[list[dict], list[dict]]:
    """Returns (staff_by_season_rows, stint_rows) for the given seasons,
    across all franchises, using the season-aware team-name table."""
    name_rows = load_team_wiki_names_seasonal()
    franchises = sorted({r["franchise"] for r in name_rows})
    staff_rows = []
    stint_rows = []
    for season in seasons:
        for franchise in franchises:
            wiki_name = wiki_name_for_season(franchise, season, name_rows)
            if wiki_name is None:
                staff_rows.append({
                    "season": season, "franchise": franchise, "wiki_title": "",
                    "wiki_url": "", "head_coach": "", "offensive_coordinator": "",
                    "defensive_coordinator": "", "n_hc": 0, "n_oc": 0, "n_dc": 0,
                    "source_field": "none", "raw_note": "NO WIKI NAME MAPPED FOR THIS SEASON",
                })
                continue
            row, role_segments = extract_team_season_v2(season, franchise, wiki_name)
            staff_rows.append(row)
            for role, segs in role_segments.items():
                n = len(segs)
                for i, seg in enumerate(segs):
                    stint_rows.append({
                        "season": season, "franchise": franchise, "role": ROLE_ABBR[role],
                        "person": seg["name"], "order_in_season": i + 1,
                        "n_holders_that_season": n,
                        "is_co_holder": seg["co_holder"],
                        "is_interim": _is_interim(seg["note"]),
                        "note": seg["note"], "source": seg["source"],
                        "wiki_url": row["wiki_url"],
                    })
    return staff_rows, stint_rows


ROLE_ABBR = {"head_coach": "HC", "offensive_coordinator": "OC", "defensive_coordinator": "DC"}


def _is_interim(note: str) -> bool:
    return bool(note) and "interim" in note.lower()


def extract_team_season(season: int, franchise: str, wiki_team_name: str) -> dict:
    title = f"{season} {wiki_team_name} season"
    fetched = fetch_wikitext(title)
    row = {
        "season": season, "franchise": franchise, "wiki_title": title,
        "wiki_url": "", "head_coach": "", "offensive_coordinator": "",
        "defensive_coordinator": "", "n_hc": 0, "n_oc": 0, "n_dc": 0,
        "source_field": "none", "raw_note": "",
    }
    if fetched is None:
        row["raw_note"] = "PAGE NOT FOUND (404)"
        return row
    wikitext, url = fetched
    row["wiki_url"] = url

    infobox_block = extract_infobox_block(wikitext)
    infobox_fields = parse_infobox_fields(infobox_block) if infobox_block else {}
    staff_block = extract_staff_block(wikitext)
    staff_fields = parse_staff_fields(staff_block) if staff_block else {}

    raw_notes = []
    field_sources = set()
    for role in ROLES:
        infobox_raw = infobox_fields.get(role)
        infobox_names = split_name_segments(infobox_raw) if infobox_raw else []
        staff_raw_list = staff_fields.get(role, [])
        staff_names = []
        for raw in staff_raw_list:
            staff_names.extend(split_name_segments(raw))

        has_infobox = bool(infobox_names)
        has_staff = bool(staff_names)
        if has_infobox and has_staff:
            field_sources.add("both")
            names = infobox_names
            # cross-check: note if the sets disagree (compare last names)
            def lastname(n):
                return n.split()[-1].lower() if n.split() else n.lower()
            if {lastname(n) for n in infobox_names} != {lastname(n) for n in staff_names}:
                raw_notes.append(
                    f"{role}: infobox={infobox_names!r} staff_section={staff_names!r} DISAGREE"
                )
        elif has_infobox:
            field_sources.add("infobox")
            names = infobox_names
        elif has_staff:
            field_sources.add("staff_section")
            names = staff_names
        else:
            names = []

        col = {"head_coach": "head_coach", "offensive_coordinator": "offensive_coordinator",
               "defensive_coordinator": "defensive_coordinator"}[role]
        row[col] = " | ".join(names)
        row[f"n_{'hc' if role == 'head_coach' else ('oc' if role == 'offensive_coordinator' else 'dc')}"] = len(names)
        if infobox_raw:
            raw_notes.append(f"{role} infobox raw: {infobox_raw.strip()[:200]}")
        if staff_raw_list:
            raw_notes.append(f"{role} staff raw: {' ; '.join(staff_raw_list)[:200]}")

    if field_sources == {"infobox"}:
        row["source_field"] = "infobox"
    elif field_sources == {"staff_section"}:
        row["source_field"] = "staff_section"
    elif field_sources:
        row["source_field"] = "both" if "both" in field_sources or len(field_sources) > 1 else next(iter(field_sources))
    else:
        row["source_field"] = "none"
    row["raw_note"] = " || ".join(raw_notes)
    return row


def run(seasons: list[int]) -> list[dict]:
    mapping = build_team_wiki_names()
    rows = []
    for season in seasons:
        for franchise, wiki_name in sorted(mapping.items()):
            rows.append(extract_team_season(season, franchise, wiki_name))
    return rows


OUT_COLUMNS = [
    "season", "franchise", "wiki_title", "wiki_url", "head_coach",
    "offensive_coordinator", "defensive_coordinator", "n_hc", "n_oc", "n_dc",
    "source_field", "raw_note",
]


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in OUT_COLUMNS})


STINT_COLUMNS = [
    "season", "franchise", "role", "person", "order_in_season",
    "n_holders_that_season", "is_co_holder", "is_interim", "note",
    "source", "wiki_url",
]


def write_stints_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=STINT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in STINT_COLUMNS})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", type=int, default=[2022, 2023, 2024])
    ap.add_argument("--mode", choices=["phase0", "full"], default="phase0")
    args = ap.parse_args()
    if args.mode == "phase0":
        rows = run(args.seasons)
        out_path = STUDY / "data" / "processed" / "staff_phase0.csv"
        write_csv(rows, out_path)
        print(f"wrote {out_path} ({len(rows)} rows)")
    else:
        staff_rows, stint_rows = run_v2(args.seasons)
        staff_path = STUDY / "data" / "processed" / "staff_by_season.csv"
        stints_path = STUDY / "data" / "processed" / "staff_stints.csv"
        write_csv(staff_rows, staff_path)
        write_stints_csv(stint_rows, stints_path)
        print(f"wrote {staff_path} ({len(staff_rows)} rows)")
        print(f"wrote {stints_path} ({len(stint_rows)} rows)")


if __name__ == "__main__":
    main()
