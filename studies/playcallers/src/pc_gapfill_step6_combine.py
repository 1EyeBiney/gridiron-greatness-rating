"""Phase 1c step 6: build data/processed/staff_stints_all.csv (1999-2025)
= staff_stints.csv + staff_stints_pages_1999_2010.csv + staff_gapfill.csv
rows, with source_detail and disagreement columns. Applies the same name
cleaning as pc_build_derived.py and extends person_aliases.csv /
person_doubtful_pairs.csv for any new certain/doubtful merges surfaced by
the gap-fill rows (existing entries are left untouched).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_build_derived import build_aliases, find_doubtful_pairs, normalize_key  # noqa: E402

STUDY = Path(__file__).resolve().parent.parent
PROCESSED = STUDY / "data" / "processed"
REFERENCE = STUDY / "data" / "reference"

FIELDS = ["season", "franchise", "role", "person", "order_in_season",
          "n_holders_that_season", "is_co_holder", "is_interim", "note",
          "source", "wiki_url", "source_detail", "disagreement"]


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    base_rows = []
    for r in load_csv(PROCESSED / "staff_stints.csv"):
        r["source_detail"] = "team_season_page"
        r["disagreement"] = "False"
        base_rows.append(r)
    for r in load_csv(PROCESSED / "staff_stints_pages_1999_2010.csv"):
        r["source_detail"] = "team_season_page"
        r["disagreement"] = "False"
        base_rows.append(r)

    gapfill = load_csv(PROCESSED / "staff_gapfill.csv")
    have_keys = {(r["season"], r["franchise"], r["role"]) for r in base_rows}
    n_holders_by_key = {}
    for r in gapfill:
        n_holders_by_key.setdefault((r["season"], r["franchise"], r["role"]), 0)
        n_holders_by_key[(r["season"], r["franchise"], r["role"])] += 1

    src_map = {"navbox": "navbox", "biography": "biography", "both": "navbox+biography"}
    for r in gapfill:
        key = (r["season"], r["franchise"], r["role"])
        base_rows.append({
            "season": r["season"], "franchise": r["franchise"], "role": r["role"],
            "person": r["person"], "order_in_season": "1",
            "n_holders_that_season": str(n_holders_by_key[key]),
            "is_co_holder": "False", "is_interim": "interim" in r["note"],
            "note": f"gap-fill ({r['agreement']}): {r['note']}".strip(": "),
            "source": r["source"], "wiki_url": r["source_url"],
            "source_detail": src_map.get(r["source"], r["source"]),
            "disagreement": str(r["agreement"] == "sources_disagree"),
        })

    # name cleaning identical to pc_build_derived._clean
    import re
    def _clean(name):
        if not isinstance(name, str):
            return name
        name = re.sub(r"[^A-Za-z.\)']+$", "", name)
        return re.sub(r",\s*(Jr|Sr)\.", r" \g<1>.", name).strip()

    for r in base_rows:
        r["person"] = _clean(r["person"])

    people = [r["person"] for r in base_rows if r["person"]]
    rename_map, alias_rows = build_aliases(people)
    doubtful = find_doubtful_pairs(people)

    # extend person_aliases.csv / person_doubtful_pairs.csv with anything new
    existing_aliases = load_csv(REFERENCE / "person_aliases.csv")
    existing_raw = {r["raw_name"] for r in existing_aliases}
    new_aliases = [r for r in alias_rows if r["raw_name"] not in existing_raw]
    if new_aliases:
        with open(REFERENCE / "person_aliases.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["raw_name", "canonical_name", "reason"])
            for r in new_aliases:
                w.writerow(r)
    print(f"person_aliases.csv: {len(new_aliases)} new merges added ({len(alias_rows)} total certain merges seen)")

    existing_doubtful = load_csv(REFERENCE / "person_doubtful_pairs.csv")
    existing_names_set = {r["names"] for r in existing_doubtful}
    new_doubtful = [r for r in doubtful if r["names"] not in existing_names_set]
    if new_doubtful:
        with open(REFERENCE / "person_doubtful_pairs.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["names"])
            for r in new_doubtful:
                w.writerow(r)
    print(f"person_doubtful_pairs.csv: {len(new_doubtful)} new doubtful pairs added")

    for r in base_rows:
        r["person"] = rename_map.get(r["person"], r["person"])

    # dedupe exact duplicate (season, franchise, role, person) rows, keeping
    # the team_season_page version if both a page and a gap-fill row exist
    # for the same triple (can happen if a gap-fill person also appears
    # as a co-holder already on the page).
    dedup = {}
    order = []
    for r in base_rows:
        key = (r["season"], r["franchise"], r["role"], r["person"])
        if key not in dedup:
            dedup[key] = r
            order.append(key)
        else:
            prev = dedup[key]
            if prev["source_detail"] != "team_season_page" and r["source_detail"] == "team_season_page":
                dedup[key] = r
    final_rows = [dedup[k] for k in order]

    out_path = PROCESSED / "staff_stints_all.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(final_rows, key=lambda r: (int(r["season"]), r["franchise"], r["role"], r["order_in_season"])):
            w.writerow({k: r.get(k, "") for k in FIELDS})

    print(f"wrote {out_path}: {len(final_rows)} rows (from {len(base_rows)} before dedup)")


if __name__ == "__main__":
    main()
