"""Source A for 1999-2010: run the team-season page extractor on the older
seasons and write separate files, leaving the 2011-2025 tables untouched.

Usage (from the study folder), in batches so each run finishes quickly:
    python src/pc_extract_older.py --seasons 1999 2000 2001 2002
    python src/pc_extract_older.py --write        # after all batches are cached

Pages are cached by pc_wiki_fetch, so --write makes no new requests once
every batch has run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pc_extract_staff as ex

STUDY = Path(__file__).resolve().parents[1]
OLDER = list(range(1999, 2011))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", type=int, default=[])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    seasons = OLDER if args.write else args.seasons
    staff_rows, stint_rows = ex.run_v2(seasons)
    staff_rows = [r for r in staff_rows if r["wiki_title"]]          # drop franchises that did not exist yet
    named = sum(1 for r in staff_rows if r["offensive_coordinator"])
    print(f"seasons {seasons[0]}-{seasons[-1]}: {len(staff_rows)} team-seasons, {named} with a named OC, "
          f"{sum(1 for r in staff_rows if r['defensive_coordinator'])} with a named DC")
    if args.write:
        ex.write_csv(staff_rows, STUDY / "data" / "processed" / "staff_by_season_1999_2010.csv")
        ex.write_stints_csv(stint_rows, STUDY / "data" / "processed" / "staff_stints_pages_1999_2010.csv")
        print("written")


if __name__ == "__main__":
    main()
