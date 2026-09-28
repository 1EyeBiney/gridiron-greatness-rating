"""Phase 1c step 1: build data/processed/staff_gaps.csv.

Every (season, franchise, role) 1999-2025 with role in {OC, DC} that has no
named holder in staff_stints.csv + staff_stints_pages_1999_2010.csv.
"""
from __future__ import annotations

import csv
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"
REFERENCE = STUDY / "data" / "reference"


def load_team_wiki_names():
    with open(REFERENCE / "team_wiki_names.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def franchise_seasons(rows):
    """franchise -> set of valid seasons 1999-2025 (union across name eras)."""
    out = {}
    for r in rows:
        fr = r["franchise"]
        lo, hi = int(r["valid_from_season"]), int(r["valid_to_season"])
        out.setdefault(fr, set()).update(range(lo, hi + 1))
    return out


def load_stints():
    rows = []
    for fn in ("staff_stints.csv", "staff_stints_pages_1999_2010.csv"):
        with open(PROCESSED / fn, newline="", encoding="utf-8") as f:
            rows.extend(list(csv.DictReader(f)))
    return rows


def main():
    wiki_rows = load_team_wiki_names()
    fseasons = franchise_seasons(wiki_rows)
    stints = load_stints()

    have = set()
    for r in stints:
        have.add((int(r["season"]), r["franchise"], r["role"]))

    gaps = []
    for fr, seasons in sorted(fseasons.items()):
        for season in sorted(seasons):
            for role in ("OC", "DC"):
                if (season, fr, role) not in have:
                    gaps.append({"season": season, "franchise": fr, "role": role})

    gaps.sort(key=lambda r: (r["season"], r["franchise"], r["role"]))
    out_path = PROCESSED / "staff_gaps.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["season", "franchise", "role"])
        w.writeheader()
        for r in gaps:
            w.writerow(r)

    print(f"wrote {out_path}: {len(gaps)} gaps")
    by_range = {"1999-2010": 0, "2011-2025": 0}
    for r in gaps:
        by_range["1999-2010" if r["season"] <= 2010 else "2011-2025"] += 1
    print(by_range)


if __name__ == "__main__":
    main()
