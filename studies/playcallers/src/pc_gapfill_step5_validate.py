"""Phase 1c step 5: validate navbox/biography sources against team-season
pages for seasons where the team-season page DOES name a holder. Reports
agreement rate per source and writes data/processed/staff_source_disagreements.csv.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"

SUFFIX_RE = re.compile(r"\s+(Jr\.?|Sr\.?|II|III|IV)$", re.IGNORECASE)


def last_name_key(name: str) -> str:
    n = SUFFIX_RE.sub("", name.strip())
    n = n.replace(".", "")
    parts = n.split()
    return parts[-1].lower() if parts else ""


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    stints = load_csv(PROCESSED / "staff_stints.csv") + load_csv(PROCESSED / "staff_stints_pages_1999_2010.csv")
    navbox = load_csv(PROCESSED / "navbox_coordinators.csv")
    bios = load_csv(PROCESSED / "bio_coaching_history.csv")

    # truth: (season, franchise, role) -> set of last-name keys named on the team-season page
    truth = defaultdict(set)
    truth_person = defaultdict(list)
    for r in stints:
        if r["role"] not in ("OC", "DC"):
            continue
        key = (int(r["season"]), r["franchise"], r["role"])
        truth[key].add(last_name_key(r["person"]))
        truth_person[key].append(r["person"])

    nav_idx = defaultdict(set)
    for r in navbox:
        for season in range(int(r["first_season"]), int(r["last_season"]) + 1):
            nav_idx[(season, r["franchise"], r["role"])].add(last_name_key(r["person"]))

    bio_idx = defaultdict(set)
    bio_names = defaultdict(list)
    for r in bios:
        for season in range(int(r["first_season"]), int(r["last_season"]) + 1):
            key = (season, r["franchise"], r["role"])
            bio_idx[key].add(last_name_key(r["person"]))
            bio_names[key].append(r["person"])

    disagreements = []
    counts = {"navbox": [0, 0], "biography": [0, 0]}  # [agree, total_with_candidate]

    for key, truth_names in truth.items():
        season, fr, role = key
        if key in nav_idx:
            counts["navbox"][1] += 1
            if truth_names & nav_idx[key]:
                counts["navbox"][0] += 1
            else:
                disagreements.append({
                    "season": season, "franchise": fr, "role": role, "source": "navbox",
                    "team_season_page_person": " | ".join(truth_person[key]),
                    "source_person": " | ".join(sorted(set(n for n in nav_idx[key]))),
                })
        if key in bio_idx:
            counts["biography"][1] += 1
            if truth_names & bio_idx[key]:
                counts["biography"][0] += 1
            else:
                disagreements.append({
                    "season": season, "franchise": fr, "role": role, "source": "biography",
                    "team_season_page_person": " | ".join(truth_person[key]),
                    "source_person": " | ".join(sorted(set(bio_names[key]))),
                })

    out_path = PROCESSED / "staff_source_disagreements.csv"
    fields = ["season", "franchise", "role", "source", "team_season_page_person", "source_person"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(disagreements, key=lambda r: (r["season"], r["franchise"], r["role"], r["source"])):
            w.writerow(r)

    print(f"wrote {out_path}: {len(disagreements)} disagreements")
    for src, (agree, total) in counts.items():
        rate = f"{agree}/{total} = {agree/total:.1%}" if total else "n/a (no overlap)"
        print(f"{src}: agreement rate {rate}")


if __name__ == "__main__":
    main()
