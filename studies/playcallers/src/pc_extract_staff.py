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
    path = STUDY / "data" / "reference" / "team_wiki_names.csv"
    mapping = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mapping[row["franchise"]] = row["wiki_team_name"]
    return mapping


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", type=int, default=[2022, 2023, 2024])
    args = ap.parse_args()
    rows = run(args.seasons)
    out_path = STUDY / "data" / "processed" / "staff_phase0.csv"
    write_csv(rows, out_path)
    print(f"wrote {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
