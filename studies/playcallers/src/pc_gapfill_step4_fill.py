"""Phase 1c step 4: fill data/processed/staff_gaps.csv using
navbox_coordinators.csv (empty - see step2 script/report) and
bio_coaching_history.csv. Writes data/processed/staff_gapfill.csv.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    gaps = load_csv(PROCESSED / "staff_gaps.csv")
    navbox = load_csv(PROCESSED / "navbox_coordinators.csv")
    bios = load_csv(PROCESSED / "bio_coaching_history.csv")

    # index bios by (franchise, role) -> list of (person, first, last, url, interim, co)
    bio_idx = defaultdict(list)
    for r in bios:
        bio_idx[(r["franchise"], r["role"])].append(r)
    nav_idx = defaultdict(list)
    for r in navbox:
        nav_idx[(r["franchise"], r["role"])].append(r)

    out_rows = []
    n_filled = 0
    n_unfilled = 0
    for g in gaps:
        season = int(g["season"])
        fr, role = g["franchise"], g["role"]

        nav_people = {}
        for r in nav_idx.get((fr, role), []):
            if int(r["first_season"]) <= season <= int(r["last_season"]):
                nav_people.setdefault(r["person"], []).append(r["source_url"])

        bio_people = {}
        for r in bio_idx.get((fr, role), []):
            if int(r["first_season"]) <= season <= int(r["last_season"]):
                note_bits = []
                if r["is_interim"] == "True":
                    note_bits.append("interim")
                if r["is_co"] == "True":
                    note_bits.append("co-role")
                bio_people.setdefault(r["person"], {"urls": [], "notes": set()})
                bio_people[r["person"]]["urls"].append(r["source_url"])
                bio_people[r["person"]]["notes"].update(note_bits)

        all_people = set(nav_people) | set(bio_people)
        if not all_people:
            n_unfilled += 1
            continue

        n_filled += 1
        for person in sorted(all_people):
            in_nav = person in nav_people
            in_bio = person in bio_people
            if in_nav and in_bio:
                source = "both"
            elif in_nav:
                source = "navbox"
            else:
                source = "biography"

            if len(all_people) == 1:
                agreement = "both_agree" if (in_nav and in_bio) else (
                    "navbox_only" if in_nav else "biography_only")
            else:
                agreement = "sources_disagree"

            urls = []
            if in_nav:
                urls.extend(nav_people[person])
            if in_bio:
                urls.extend(bio_people[person]["urls"])
            note = ""
            if in_bio:
                note = ", ".join(sorted(bio_people[person]["notes"]))
            if len(all_people) > 1:
                note = (note + "; " if note else "") + f"disagreement: {len(all_people)} candidates for this season"

            out_rows.append({
                "season": season, "franchise": fr, "role": role, "person": person,
                "source": source, "source_url": " | ".join(sorted(set(urls))),
                "agreement": agreement, "note": note,
            })

    fields = ["season", "franchise", "role", "person", "source", "source_url", "agreement", "note"]
    out_path = PROCESSED / "staff_gapfill.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(out_rows, key=lambda r: (r["season"], r["franchise"], r["role"])):
            w.writerow(r)

    print(f"wrote {out_path}: {len(out_rows)} rows")
    print(f"gaps filled (>=1 candidate): {n_filled} / {len(gaps)}; still unfilled: {n_unfilled}")


if __name__ == "__main__":
    main()
