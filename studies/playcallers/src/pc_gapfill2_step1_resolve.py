"""Phase 1d step 1b: fetch/resolve biographies for names in
gapfill2_fetch_candidates.csv, in tier order, appending newly resolved/
unresolved names to data/reference/playcaller_bio_resolution.csv.

Resumable: skips names already present in playcaller_bio_resolution.csv.
Stops after this invocation uses --max-requests new HTTP requests (default
100), so re-run repeatedly (checking `tasklist | grep -i python` is clear
first, per the fetch rules) until the candidate list is exhausted or the
overall budget is used up.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_wiki_fetch import fetch_wikitext, request_count  # noqa: E402
from pc_extract_staff import strip_wiki_markup  # noqa: E402

STUDY = Path(__file__).resolve().parent.parent
REFERENCE = STUDY / "data" / "reference"

BIO_SUFFIXES = ["", " (American football)", " (American football coach)"]


def resolve_biography_title(name: str):
    for suffix in BIO_SUFFIXES:
        title = name + suffix
        result = fetch_wikitext(title)
        if result is None:
            continue
        wikitext, url = result
        if re.search(r"\{\{disambiguation", wikitext, re.IGNORECASE) or re.search(r"may refer to:", wikitext, re.IGNORECASE):
            continue
        plain = strip_wiki_markup(wikitext)
        first_para = plain[:1500]
        if re.search(r"football", first_para, re.IGNORECASE) and re.search(r"coach", first_para, re.IGNORECASE):
            return wikitext, url
    return None


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-requests", type=int, default=100)
    args = ap.parse_args()

    known = {r["name"] for r in load_csv(REFERENCE / "playcaller_bio_resolution.csv")}
    candidates = load_csv(REFERENCE / "gapfill2_fetch_candidates.csv")
    todo = [r["name"] for r in candidates if r["name"] not in known]

    start = request_count()
    resolved, unresolved = [], []
    processed = 0
    for name in todo:
        if request_count() - start >= args.max_requests:
            break
        result = resolve_biography_title(name)
        processed += 1
        if result is None:
            unresolved.append(name)
        else:
            resolved.append(name)

    with open(REFERENCE / "playcaller_bio_resolution.csv", "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for n in resolved:
            w.writerow([n, "yes"])
        for n in unresolved:
            w.writerow([n, "no"])

    print(f"processed {processed} names this run ({request_count() - start} requests used)")
    print(f"resolved: {len(resolved)}, unresolved: {len(unresolved)}")
    print(f"remaining candidates not yet attempted: {len(todo) - processed}")


if __name__ == "__main__":
    main()
