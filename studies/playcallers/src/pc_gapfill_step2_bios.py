"""Phase 1c step 2/3: parse cached biography pastcoaching fields into
data/processed/bio_coaching_history.csv, and write an empty (schema-only)
data/processed/navbox_coordinators.csv with a note explaining why.

Source B1 (coordinator navigation templates) was tested and does not exist
on Wikipedia: "Template:<Team> offensive/defensive coordinator navbox" and
several plausible variants all 404, and an API search of the Template
namespace for those phrases turns up only unrelated templates (current
team-staff snapshot templates with no year ranges, and current-season
league-wide "NFL offensive/defensive coordinators" navboxes with no
history). So navbox_coordinators.csv is written empty and all gap-filling
in step 4 comes from Source B2 (biographies) only.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_wiki_fetch import fetch_wikitext  # noqa: E402

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"
REFERENCE = STUDY / "data" / "reference"

BIO_SUFFIXES = ["", " (American football)", " (American football coach)"]

PASTCOACHING_FIELDS = [
    "pastcoaching", "past_coaching", "coaching_teams", "coach_teams",
]

def normalize_titles(raw: str) -> list[tuple[str, bool, bool]]:
    """Returns a list of (role, is_interim, is_co) for every HC/OC/DC role
    mentioned in a (possibly compound, e.g. "Interim head coach & offensive
    coordinator" or "Assistant head coach/offensive coordinator") title
    string. A bare "(assistant) head coach" with no coordinator qualifier
    that is NOT the primary head-coach title (e.g. "assistant head coach"
    alone, meaning an assistant, not the HC) is excluded - only "head
    coach"/"interim head coach"/"co-head coach" count as HC."""
    t = raw.lower()
    is_interim = "interim" in t
    out = []
    if re.search(r"offensive coordinator", t):
        out.append(("OC", is_interim, "co-offensive coordinator" in t or bool(re.search(r"\bco-?offensive coordinator\b", t))))
    if re.search(r"defensive coordinator", t):
        out.append(("DC", is_interim, bool(re.search(r"\bco-?defensive coordinator\b", t))))
    if re.search(r"(?:^|[^a-z])head coach\b", t) and "assistant head coach" not in t:
        out.append(("HC", is_interim, "co-head coach" in t))
    elif re.search(r"assistant head coach\s*/\s*(?:offensive|defensive) coordinator", t):
        pass  # already captured via the OC/DC branch above
    return out


def extract_years(paren_text: str) -> tuple[int, int] | None:
    tokens = re.findall(r"\d{4}|present", paren_text)
    if not tokens:
        return None
    first = int(tokens[0])
    if len(tokens) == 1:
        return first, first
    last = 2025 if tokens[1] == "present" else int(tokens[1])
    return first, last


def strip_markup_keep_years(s: str) -> str:
    # keep template params but drop the {{...|}} wrapper so digits/"present" remain
    s = re.sub(r"\{\{ubl\|(.*?)\}\}", r"\1", s, flags=re.IGNORECASE)
    s = re.sub(r"\{\{(?:nfly|NFL ?Year)\|([^{}]*)\}\}", lambda m: m.group(1).replace("|", "-"), s, flags=re.IGNORECASE)
    s = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''?", "", s)
    return s


def find_field_block(wikitext: str, field: str) -> str | None:
    pat = re.compile(r"\|\s*" + re.escape(field) + r"\s*=(.*?)(?=\n\s*\|\s*[a-zA-Z_]+\s*=|\n\}\}|\Z)", re.DOTALL)
    m = pat.search(wikitext)
    return m.group(1) if m else None


def parse_pastcoaching(block: str) -> list[dict]:
    """Parse bullet lines. Handles:
    * [[Team]] (years)<br />Title            -> one entry
    * {{ubl|[[Team]] (years)}}               -> team/year context only
    ** {{ubl|Title (subyears)}}              -> entry using context team,
                                                 own years if given else context years
    """
    rows = []
    current_team = None
    current_years = None
    for raw_line in block.split("\n"):
        line = raw_line.strip()
        if not line or not line.startswith("*"):
            continue
        depth = len(line) - len(line.lstrip("*"))
        content = line.lstrip("*").strip()
        clean = strip_markup_keep_years(content)
        # split off <br> separated team/title
        parts = re.split(r"<br\s*/?>", clean, maxsplit=1)
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""

        # team name = text before "(" in left
        team_m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", left)
        if depth == 1:
            if team_m:
                team = team_m.group(1).strip()
                years = extract_years(team_m.group(2))
                if right:
                    # complete entry on one line
                    if years:
                        for role, interim, co in normalize_titles(right):
                            rows.append({
                                "team": team, "first_season": years[0], "last_season": years[1],
                                "title_raw": right, "role": role, "is_interim": interim, "is_co": co,
                            })
                    current_team, current_years = None, None
                else:
                    # team/year context only, no title on this line (sub-bullets follow)
                    current_team, current_years = team, years
            else:
                # left has no paren at all; maybe title only line with no team (rare) - skip
                current_team, current_years = None, None
        else:
            # sub-bullet: content is "Title (years)" or just "Title"
            sub_m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", left)
            if sub_m:
                title_text = sub_m.group(1).strip()
                years = extract_years(sub_m.group(2))
            else:
                title_text = left
                years = None
            if years is None:
                years = current_years
            if current_team and years:
                for role, interim, co in normalize_titles(title_text):
                    rows.append({
                        "team": current_team, "first_season": years[0], "last_season": years[1],
                        "title_raw": title_text, "role": role, "is_interim": interim, "is_co": co,
                    })
    return rows


# Extra historical/alternate spellings not in team_wiki_names.csv (which
# already covers the in-range relocations: SD/LA Chargers, StL/LA Rams,
# Oakland/LV Raiders, Washington Redskins/Football Team/Commanders).
EXTRA_TEAM_ALIASES = {
    "Houston Oilers": "TEN",
    "Tennessee Oilers": "TEN",
    "San Diego Chargers": "LAC",
    "Los Angeles Chargers": "LAC",
    "St. Louis Rams": "LAR",
    "Los Angeles Rams": "LAR",
    "Oakland Raiders": "OAK",
    "Las Vegas Raiders": "OAK",
    "Washington Redskins": "WSH",
    "Washington Football Team": "WSH",
    "Washington Commanders": "WSH",
}


def load_team_name_to_franchise() -> dict[str, str]:
    mapping = dict(EXTRA_TEAM_ALIASES)
    with open(REFERENCE / "team_wiki_names.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mapping[r["wiki_team_name"]] = r["franchise"]
    return mapping


def load_resolved_names() -> list[str]:
    with open(REFERENCE / "playcaller_bio_resolution.csv", encoding="utf-8") as f:
        return [r["name"] for r in csv.DictReader(f) if r["resolved"] == "yes"]


def resolve_cached(name: str):
    for suffix in BIO_SUFFIXES:
        title = name + suffix
        result = fetch_wikitext(title)  # cache hit, no network
        if result is None:
            continue
        wikitext, url = result
        if re.search(r"\{\{disambiguation", wikitext, re.IGNORECASE) or re.search(r"may refer to:", wikitext, re.IGNORECASE):
            continue
        return wikitext, url, title
    return None


def main():
    names = load_resolved_names()
    team_to_fr = load_team_name_to_franchise()
    out_rows = []
    parsed_count = 0
    skipped_non_nfl = 0
    for name in names:
        r = resolve_cached(name)
        if r is None:
            continue
        wikitext, url, title = r
        block = None
        for field in PASTCOACHING_FIELDS:
            block = find_field_block(wikitext, field)
            if block:
                break
        if not block:
            continue
        entries = parse_pastcoaching(block)
        if entries:
            parsed_count += 1
        for e in entries:
            fr = team_to_fr.get(e["team"])
            if fr is None:
                skipped_non_nfl += 1
                continue
            if e["last_season"] < 1999 or e["first_season"] > 2025:
                continue
            first_season = max(e["first_season"], 1999)
            last_season = min(e["last_season"], 2025)
            out_rows.append({
                "person": name,
                "franchise": fr,
                "team_wiki_name": e["team"],
                "first_season": first_season,
                "last_season": last_season,
                "role": e["role"],
                "title_raw": e["title_raw"],
                "is_interim": e["is_interim"],
                "is_co": e["is_co"],
                "source_url": url,
            })

    fields = ["person", "franchise", "team_wiki_name", "first_season", "last_season", "role",
              "title_raw", "is_interim", "is_co", "source_url"]
    out_path = PROCESSED / "bio_coaching_history.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"wrote {out_path}: {len(out_rows)} rows from {parsed_count}/{len(names)} biographies with a parsed field "
          f"({skipped_non_nfl} entries skipped: not an NFL franchise or outside 1999-2025)")

    # Empty navbox_coordinators.csv, schema only (Source B1 does not exist; see docstring/report).
    navbox_path = PROCESSED / "navbox_coordinators.csv"
    with open(navbox_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "franchise", "role", "person", "first_season", "last_season",
            "template_title", "source_url",
        ])
        w.writeheader()
    print(f"wrote {navbox_path}: 0 rows (Source B1 templates do not exist on Wikipedia - tested, see report)")


if __name__ == "__main__":
    main()
