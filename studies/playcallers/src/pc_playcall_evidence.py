"""Phase 1b Task 1-2: mine play-calling evidence from cached Wikipedia pages.

Two source types:
- team_season_page: the 480 already-cached "{season} {team} season" pages
  (2011-2025), re-read from disk, no new fetches needed.
- biography: a coach's own Wikipedia biography, fetched (network, budget-
  limited) via pc_wiki_fetch.fetch_wikitext, for head coaches first, then
  coordinators with the most seasons, until the request budget runs out.

Both source types are scanned with the same sentence-level pattern match
and written into data/processed/playcall_evidence.csv.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pc_extract_staff import strip_wiki_markup  # noqa: E402
from pc_wiki_fetch import fetch_wikitext, request_count  # noqa: E402

STUDY_DIR = Path(__file__).resolve().parent.parent
PROCESSED = STUDY_DIR / "data" / "processed"
RAW_WIKI = STUDY_DIR / "data" / "raw" / "wikipedia"

# "signal caller" is explicitly excluded (means QB, not play-caller).
PLAYCALL_PATTERNS = [
    r"play[\s-]?calling",
    r"called plays",
    r"call plays",
    r"calling plays",
    r"play[\s-]?caller",
    r"calls the (?:offense|defense|plays|playcalls)",
]
PLAYCALL_RE = re.compile("|".join(PLAYCALL_PATTERNS), re.IGNORECASE)

OFFENSE_WORDS = re.compile(r"\boffen", re.IGNORECASE)
DEFENSE_WORDS = re.compile(r"\bdefen", re.IGNORECASE)

SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")


def sentences_from_wikitext(wikitext: str) -> list[str]:
    """Strip markup from the whole page, then split into rough sentences."""
    plain = strip_wiki_markup(wikitext)
    # Collapse excess whitespace/newlines first so sentence splitting works
    # across what were originally separate wikitext lines.
    plain = re.sub(r"\n+", " ", plain)
    plain = re.sub(r"\s{2,}", " ", plain)
    parts = SENT_SPLIT_RE.split(plain)
    return [p.strip() for p in parts if p.strip()]


def unit_guess(sentence: str) -> str:
    has_off = bool(OFFENSE_WORDS.search(sentence))
    has_def = bool(DEFENSE_WORDS.search(sentence))
    if has_off and not has_def:
        return "offense"
    if has_def and not has_off:
        return "defense"
    return "unknown"


def persons_mentioned(sentence: str, candidate_names: list[str]) -> list[str]:
    found = []
    for name in candidate_names:
        if not name:
            continue
        last = name.split()[-1].rstrip(".")
        # match on last name token (case-sensitive-ish, whole word) to avoid
        # missing "Reid" when sentence says "Andy Reid" or just "Reid".
        if re.search(r"\b" + re.escape(last) + r"\b", sentence):
            found.append(name)
    return found


def extract_hits(sentences: list[str], candidate_names: list[str]) -> list[dict]:
    hits = []
    for sent in sentences:
        if PLAYCALL_RE.search(sent):
            trimmed = sent[:400] if len(sent) > 400 else sent
            hits.append({
                "sentence": trimmed,
                "unit_guess": unit_guess(sent),
                "persons_mentioned": " | ".join(persons_mentioned(sent, candidate_names)),
            })
    return hits


def load_staff_stints() -> list[dict]:
    with open(PROCESSED / "staff_stints.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def team_season_page_path(season: int, wiki_team_name: str) -> Path | None:
    import hashlib
    title = f"{season} {wiki_team_name} season"
    h = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
    safe = "".join(c if c.isalnum() else "_" for c in title)[:80]
    p = RAW_WIKI / f"{safe}_{h}.wikitext"
    return p if p.exists() else None


def mine_team_season_pages(stints: list[dict], team_wiki_rows: list[dict]) -> list[dict]:
    from pc_extract_staff import wiki_name_for_season

    by_key: dict[tuple, list[str]] = {}
    for row in stints:
        key = (int(row["season"]), row["franchise"])
        by_key.setdefault(key, []).append(row["person"])

    evidence = []
    seen_pages = set()
    for (season, franchise), names in sorted(by_key.items()):
        wiki_name = wiki_name_for_season(franchise, season, team_wiki_rows)
        if not wiki_name:
            continue
        path = team_season_page_path(season, wiki_name)
        if path is None or path in seen_pages:
            if path is None:
                continue
        seen_pages.add(path)
        wikitext = path.read_text(encoding="utf-8")
        sentences = sentences_from_wikitext(wikitext)
        hits = extract_hits(sentences, names)
        title = f"{season} {wiki_name} season"
        url = f"https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
        for h in hits:
            evidence.append({
                "season": season,
                "franchise": franchise,
                "page_title": title,
                "url": url,
                "sentence": h["sentence"],
                "persons_mentioned": h["persons_mentioned"],
                "unit_guess": h["unit_guess"],
                "source_type": "team_season_page",
            })
    return evidence


BIO_SUFFIXES = ["", " (American football)", " (American football coach)"]


def resolve_biography_title(name: str) -> tuple[str, str] | None:
    """Try a few title forms; return (wikitext, url) for the first that
    looks like an American-football-coach biography, else None."""
    for suffix in BIO_SUFFIXES:
        title = name + suffix
        result = fetch_wikitext(title)
        if result is None:
            continue
        wikitext, url = result
        # Reject obvious disambiguation pages.
        if re.search(r"\{\{disambiguation", wikitext, re.IGNORECASE) or \
           re.search(r"may refer to:", wikitext, re.IGNORECASE):
            continue
        plain = strip_wiki_markup(wikitext)
        first_para = plain[:1500]
        if re.search(r"football", first_para, re.IGNORECASE) and \
           re.search(r"coach", first_para, re.IGNORECASE):
            return wikitext, url
    return None


def build_bio_priority_list(stints: list[dict], budget: int) -> list[tuple[str, str, list[int]]]:
    """Returns [(name, primary_role, seasons_for_context)], head coaches
    first (all of them), then OC/DC ranked by season count, until budget."""
    hc_names: dict[str, set[int]] = {}
    coord_names: dict[str, set[int]] = {}
    for row in stints:
        season = int(row["season"])
        if row["role"] == "HC":
            hc_names.setdefault(row["person"], set()).add(season)
        elif row["role"] in ("OC", "DC"):
            coord_names.setdefault(row["person"], set()).add(season)

    ordered: list[tuple[str, str, list[int]]] = []
    for name, seasons in sorted(hc_names.items()):
        ordered.append((name, "HC", sorted(seasons)))

    # Coordinators who are NOT also a head coach in our list, ranked by
    # season count (most seasons first) as a tiebreak for budget priority.
    coord_only = [(n, s) for n, s in coord_names.items() if n not in hc_names]
    coord_only.sort(key=lambda t: (-len(t[1]), t[0]))
    for name, seasons in coord_only:
        ordered.append((name, "OC/DC", sorted(seasons)))

    return ordered[:budget] if budget else ordered


def mine_biographies(stints: list[dict], request_budget: int) -> tuple[list[dict], list[str], list[str]]:
    """Returns (evidence_rows, resolved_names, unresolved_names)."""
    priority = build_bio_priority_list(stints, budget=0)  # rank all, cap by budget below
    names_and_seasons = {row["person"]: [] for row in stints}
    person_seasons: dict[str, list[tuple[int, str, str]]] = {}
    for row in stints:
        person_seasons.setdefault(row["person"], []).append(
            (int(row["season"]), row["franchise"], row["role"])
        )

    evidence = []
    resolved = []
    unresolved = []
    requests_used_before = request_count()

    for name, primary_role, seasons in priority:
        if request_count() - requests_used_before >= request_budget:
            break
        result = resolve_biography_title(name)
        if result is None:
            unresolved.append(name)
            continue
        wikitext, url = result
        resolved.append(name)
        sentences = sentences_from_wikitext(wikitext)
        # candidate names for persons_mentioned: just this person (bios are
        # about one person primarily) plus any co-mentioned staff isn't
        # tracked here; keep it simple and precise.
        hits = extract_hits(sentences, [name])
        title_used = url.rsplit("/", 1)[-1].replace("_", " ")
        for h in hits:
            # crude season/team attach: look for a 4-digit year and known
            # franchise-ish capitalized words in the same sentence; leave
            # blank if not found rather than guess.
            year_match = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", h["sentence"])
            season_hint = year_match.group(0) if year_match else ""
            evidence.append({
                "season": season_hint,
                "franchise": "",
                "page_title": title_used,
                "url": url,
                "sentence": h["sentence"] + (f"  [subject: {name}]"),
                "persons_mentioned": name,
                "unit_guess": h["unit_guess"],
                "source_type": "biography",
            })

    return evidence, resolved, unresolved


EVIDENCE_FIELDS = [
    "evidence_id", "season", "franchise", "page_title", "url", "sentence",
    "persons_mentioned", "unit_guess", "source_type",
]


def write_evidence_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EVIDENCE_FIELDS)
        w.writeheader()
        for i, row in enumerate(rows, start=1):
            out = {"evidence_id": i}
            out.update(row)
            w.writerow(out)


def main():
    import argparse
    from pc_extract_staff import load_team_wiki_names_seasonal

    ap = argparse.ArgumentParser()
    ap.add_argument("--bio-budget", type=int, default=440)
    ap.add_argument("--out", default=str(PROCESSED / "playcall_evidence.csv"))
    args = ap.parse_args()

    stints = load_staff_stints()
    team_wiki_rows = load_team_wiki_names_seasonal()

    team_evidence = mine_team_season_pages(stints, team_wiki_rows)
    print(f"team_season_page evidence sentences: {len(team_evidence)}")

    bio_evidence, resolved, unresolved = mine_biographies(stints, args.bio_budget)
    print(f"biography evidence sentences: {len(bio_evidence)}")
    print(f"biographies resolved: {len(resolved)}, unresolved: {len(unresolved)}")
    print(f"requests used this run: {request_count()}")

    all_evidence = team_evidence + bio_evidence
    write_evidence_csv(all_evidence, Path(args.out))

    # Save resolution lists for the report.
    ref_dir = STUDY_DIR / "data" / "reference"
    with open(ref_dir / "playcaller_bio_resolution.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "resolved"])
        for n in resolved:
            w.writerow([n, "yes"])
        for n in unresolved:
            w.writerow([n, "no"])

    print(f"wrote {len(all_evidence)} evidence rows to {args.out}")


if __name__ == "__main__":
    main()
