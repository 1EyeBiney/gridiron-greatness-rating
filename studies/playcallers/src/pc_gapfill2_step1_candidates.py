"""Phase 1d (second gap-fill pass) step 1: build the priority-ordered list
of person names whose biography is not yet cached/resolved, and write it
to data/reference/gapfill2_fetch_candidates.csv (name, tier, reason).

Tiers (lower fetched first):
  1 = head coach or coordinator of a franchise that still has an OC/DC gap
      (per staff_gaps.csv minus staff_gapfill.csv), in a season within 3
      years of one of that franchise's gap seasons, OR a name surfaced by
      the discovery scan (mentioned as "offensive/defensive coordinator"
      in the cached team-season-page text of a gap season or its
      neighbours for that franchise).
  2 = everyone else appearing (staff_stints_all or games.csv coach) in a
      season 1999-2012.
  3 = everyone else.

Does not fetch anything itself (no network) - it only reads already-cached
team-season-page wikitext and existing CSVs.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_extract_staff import strip_wiki_markup, load_team_wiki_names_seasonal, wiki_name_for_season  # noqa: E402

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"
REFERENCE = STUDY / "data" / "reference"
RAW_WIKI = STUDY / "data" / "raw" / "wikipedia"
GAMES_CSV = STUDY.parents[1] / "studies" / "home-field-advantage" / "data" / "raw" / "nflverse" / "games.csv"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def already_known_names() -> set[str]:
    rows = load_csv(REFERENCE / "playcaller_bio_resolution.csv")
    return {r["name"] for r in rows}


def team_season_page_path(season: int, wiki_team_name: str) -> Path | None:
    import hashlib
    title = f"{season} {wiki_team_name} season"
    h = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
    safe = "".join(c if c.isalnum() else "_" for c in title)[:80]
    p = RAW_WIKI / f"{safe}_{h}.wikitext"
    return p if p.exists() else None


SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
ROLE_MENTION_RE = re.compile(r"offensive coordinator|defensive coordinator", re.IGNORECASE)
WIKILINK_RE = re.compile(r"\[\[([^\]|]*)(?:\|([^\]]*))?\]\]")


NON_PERSON_LINK_SUBSTRINGS = (
    "coordinator", "National Football League", "category:", "Category:",
    "Journal", "Times", "News", "Press", "season", "Bowl", "Conference",
    "Division", "Stadium", "University", "College",
)


NON_PERSON_EXACT = {
    "AFC West", "AFC East", "AFC North", "AFC South",
    "NFC West", "NFC East", "NFC North", "NFC South",
}


def _looks_like_team_or_junk(name: str, team_names: set[str]) -> bool:
    if name in NON_PERSON_EXACT:
        return True
    bare = name.rstrip("'")
    if bare in team_names or name in team_names:
        return True
    return False


def discovery_candidates_for(franchise: str, season: int, team_wiki_rows) -> set[str]:
    """Scan the cached team-season page text (this season +/- 1) for
    *sentences* mentioning an OC/DC role, and take the single wikilink
    closest (by character distance) to the role phrase within that
    sentence - much tighter than a raw-character window, to avoid pulling
    in unrelated players/executives/sources mentioned nearby."""
    team_names = {r["wiki_team_name"] for r in team_wiki_rows}
    names = set()
    for s in (season - 1, season, season + 1):
        wiki_name = wiki_name_for_season(franchise, s, team_wiki_rows)
        if not wiki_name:
            continue
        path = team_season_page_path(s, wiki_name)
        if path is None:
            continue
        raw = path.read_text(encoding="utf-8")
        # crude sentence split directly on the wikitext (keeps [[links]] intact)
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\[])", raw.replace("\n", " "))
        offset = 0
        for sent in sentences:
            if ROLE_MENTION_RE.search(sent):
                role_m = ROLE_MENTION_RE.search(sent)
                links = list(WIKILINK_RE.finditer(sent))
                best = None
                best_dist = None
                for lm in links:
                    target = lm.group(1).strip()
                    if any(w.lower() in target.lower() for w in NON_PERSON_LINK_SUBSTRINGS):
                        continue
                    display = (lm.group(2) or target).strip()
                    candidate = display.split("(")[0].strip()
                    if not candidate or " " not in candidate or not candidate[0].isupper():
                        continue
                    dist = min(abs(lm.start() - role_m.end()), abs(lm.end() - role_m.start()))
                    if best_dist is None or dist < best_dist:
                        best_dist = dist
                        best = candidate
                if best and not _looks_like_team_or_junk(best, team_names):
                    names.add(best)
    return names


def main():
    known = already_known_names()
    stints = load_csv(PROCESSED / "staff_stints_all.csv")
    gaps = load_csv(PROCESSED / "staff_gaps.csv")
    gapfill = load_csv(PROCESSED / "staff_gapfill.csv")
    filled_keys = {(r["season"], r["franchise"], r["role"]) for r in gapfill}
    remaining_gaps = [g for g in gaps if (g["season"], g["franchise"], g["role"]) not in filled_keys]

    team_wiki_rows = load_team_wiki_names_seasonal()

    # franchise -> set of gap seasons remaining
    gap_seasons_by_franchise: dict[str, set[int]] = {}
    for g in remaining_gaps:
        gap_seasons_by_franchise.setdefault(g["franchise"], set()).add(int(g["season"]))

    # tier1 name -> reason
    tier1 = {}
    for row in stints:
        fr = row["franchise"]
        if fr not in gap_seasons_by_franchise:
            continue
        season = int(row["season"])
        gap_seasons = gap_seasons_by_franchise[fr]
        if any(abs(season - gs) <= 3 for gs in gap_seasons):
            name = row["person"]
            if name and name not in known:
                tier1.setdefault(name, f"staff of gap-franchise {fr}, season {season} (within 3y of a gap)")

    discovery_names = set()
    for fr, seasons in gap_seasons_by_franchise.items():
        for gs in sorted(seasons):
            discovery_names |= discovery_candidates_for(fr, gs, team_wiki_rows)
    tier1a = {}
    for name in discovery_names:
        if name not in known:
            tier1a[name] = "discovery scan: mentioned near an OC/DC role phrase on the gap franchise's team-season page (adjacent seasons included)"
    # tier1 (proximity staff) excludes anything already promoted to tier1a
    tier1 = {n: r for n, r in tier1.items() if n not in tier1a}

    # tier2: everyone else 1999-2012, from staff_stints_all or games.csv coaches
    tier2 = {}
    for row in stints:
        if int(row["season"]) <= 2012:
            name = row["person"]
            if name and name not in known and name not in tier1:
                tier2.setdefault(name, "staff_stints_all, season <=2012")

    if GAMES_CSV.exists():
        with open(GAMES_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                season = int(r["season"])
                if not (1999 <= season <= 2025):
                    continue
                for col in ("home_coach", "away_coach"):
                    name = (r.get(col) or "").strip()
                    if not name or name in known:
                        continue
                    if season <= 2012:
                        if name not in tier1:
                            tier2.setdefault(name, f"games.csv {col}, season <=2012")
                    else:
                        pass  # handled in tier3 pass below

    # tier3: everyone else (games.csv coaches 2013-2025 not already placed, and
    # any staff_stints_all person >2012 not already placed)
    tier3 = {}
    for row in stints:
        name = row["person"]
        if name and name not in known and name not in tier1 and name not in tier2:
            tier3.setdefault(name, "staff_stints_all, season >2012")
    if GAMES_CSV.exists():
        with open(GAMES_CSV, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                season = int(r["season"])
                if not (1999 <= season <= 2025):
                    continue
                for col in ("home_coach", "away_coach"):
                    name = (r.get(col) or "").strip()
                    if not name or name in known or name in tier1 or name in tier2:
                        continue
                    tier3.setdefault(name, f"games.csv {col}, season >2012")

    out_path = REFERENCE / "gapfill2_fetch_candidates.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "tier", "reason"])
        w.writeheader()
        for name, reason in sorted(tier1a.items()):
            w.writerow({"name": name, "tier": "1a", "reason": reason})
        for name, reason in sorted(tier1.items()):
            w.writerow({"name": name, "tier": "1b", "reason": reason})
        for name, reason in sorted(tier2.items()):
            w.writerow({"name": name, "tier": "2", "reason": reason})
        for name, reason in sorted(tier3.items()):
            w.writerow({"name": name, "tier": "3", "reason": reason})

    print(f"wrote {out_path}: tier1a={len(tier1a)} tier1b={len(tier1)} tier2={len(tier2)} tier3={len(tier3)} "
          f"total={len(tier1a)+len(tier1)+len(tier2)+len(tier3)}")


if __name__ == "__main__":
    main()
