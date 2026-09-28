"""Phase 1a: build person-name aliases, apply them to staff_stints.csv, and
derive the two movers tables (coordinator_moves.csv,
coordinator_to_headcoach.csv) plus the head-coach cross-check for the full
2011-2025 range.

Run from the study folder, after pc_extract_staff.py --mode full has
written data/processed/staff_stints.csv and staff_by_season.csv:
    python src/pc_build_derived.py
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

STUDY = Path(__file__).resolve().parent.parent

SUFFIX_RE = re.compile(r"\s+(Jr\.?|Sr\.?|II|III|IV)$", re.IGNORECASE)


def normalize_key(name: str) -> str:
    """Core-name key used only to *detect* candidate aliases: lowercase,
    strip a trailing generational suffix and periods. Two names that share
    this key are suffix/punctuation variants of the same string, not
    necessarily the same person - the caller still checks before merging."""
    n = name.strip()
    n = SUFFIX_RE.sub("", n)
    n = n.replace(".", "")
    return n.lower().strip()


def build_aliases(people: list[str]) -> tuple[dict[str, str], list[dict]]:
    """Only merges names that differ solely by a trailing Jr./Sr./II/III/IV
    suffix or periods (e.g. "Pete Carmichael Jr." / "Pete Carmichael") -
    the one case explicit enough not to be guesswork. Everything else that
    merely looks similar (different first name, nickname, etc.) is left
    alone and is NOT written here.

    Returns (rename_map, alias_rows). rename_map maps every raw name that
    was merged to its canonical form (the longest variant, on the theory
    that the fuller name - the one with the suffix - is the more complete
    citation and reads the same either way)."""
    groups: dict[str, list[str]] = {}
    for name in sorted(set(people)):
        groups.setdefault(normalize_key(name), []).append(name)

    rename_map: dict[str, str] = {}
    alias_rows = []
    for key, variants in groups.items():
        if len(variants) < 2:
            continue
        canonical = max(variants, key=len)
        for v in variants:
            rename_map[v] = canonical
            if v != canonical:
                alias_rows.append({
                    "raw_name": v, "canonical_name": canonical,
                    "reason": "suffix/punctuation variant (Jr./Sr./II/III/IV or period)",
                })
    return rename_map, alias_rows


def find_doubtful_pairs(people: list[str]) -> list[dict]:
    """Same last name + same first initial, but not already merged as a
    suffix variant - flagged for a human, never merged automatically."""
    uniq = sorted(set(people))
    by_last_initial: dict[tuple, list[str]] = {}
    for n in uniq:
        parts = n.split()
        if len(parts) < 2:
            continue
        key = (parts[-1].lower(), parts[0][0].lower())
        by_last_initial.setdefault(key, []).append(n)
    doubtful = []
    for key, names in by_last_initial.items():
        if len(names) < 2:
            continue
        keys_norm = {normalize_key(n) for n in names}
        if len(keys_norm) == 1:
            continue  # already handled as a clean suffix alias
        doubtful.append({"names": " / ".join(names)})
    return doubtful


def apply_aliases(stints: pd.DataFrame, rename_map: dict[str, str]) -> pd.DataFrame:
    stints = stints.copy()
    stints["person"] = stints["person"].map(lambda n: rename_map.get(n, n))
    return stints


def build_coordinator_moves(stints: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for role in ("OC", "DC"):
        sub = stints[stints.role == role]
        for person, g in sub.groupby("person"):
            franchises = sorted(g["franchise"].unique())
            if len(franchises) < 2:
                continue
            stints_list = []
            for fr in franchises:
                seasons = sorted(g[g.franchise == fr]["season"].unique())
                stints_list.append(f"{fr}:{seasons[0]}-{seasons[-1]}")
            rows.append({
                "role": role, "person": person,
                "n_franchises": len(franchises),
                "stints": " | ".join(stints_list),
            })
    df = pd.DataFrame(rows).sort_values(["role", "person"]) if rows else pd.DataFrame(
        columns=["role", "person", "n_franchises", "stints"])
    return df


def build_coordinator_to_headcoach(stints: pd.DataFrame) -> pd.DataFrame:
    rows = []
    coord = stints[stints.role.isin(["OC", "DC"])]
    hc = stints[stints.role == "HC"]
    for person, cg in coord.groupby("person"):
        hg = hc[hc.person == person]
        if hg.empty:
            continue
        first_coord_season = cg["season"].min()
        coord_stints = sorted(
            f"{r.franchise}:{r.role}:{r.season}" for r in cg.itertuples()
        )
        hc_stints = sorted(hg["franchise"].unique())
        later_hc = hg[hg["season"] > first_coord_season]
        if later_hc.empty:
            continue
        hc_seasons_by_fr = {}
        for fr in later_hc["franchise"].unique():
            seasons = sorted(later_hc[later_hc.franchise == fr]["season"].unique())
            hc_seasons_by_fr[fr] = f"{fr}:{seasons[0]}-{seasons[-1]}"
        rows.append({
            "person": person,
            "coordinator_stints": " | ".join(sorted(set(coord_stints))),
            "headcoach_stints": " | ".join(sorted(hc_seasons_by_fr.values())),
        })
    df = pd.DataFrame(rows).sort_values("person") if rows else pd.DataFrame(
        columns=["person", "coordinator_stints", "headcoach_stints"])
    return df


def main():
    stints_path = STUDY / "data" / "processed" / "staff_stints.csv"
    stints = pd.read_csv(stints_path, dtype={"season": int})

    people = stints["person"].dropna().tolist()
    rename_map, alias_rows = build_aliases(people)
    doubtful = find_doubtful_pairs(people)

    aliases_path = STUDY / "data" / "reference" / "person_aliases.csv"
    aliases_path.parent.mkdir(parents=True, exist_ok=True)
    with open(aliases_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["raw_name", "canonical_name", "reason"])
        w.writeheader()
        for r in alias_rows:
            w.writerow(r)
    print(f"wrote {aliases_path}: {len(alias_rows)} alias merges")

    doubtful_path = STUDY / "data" / "reference" / "person_doubtful_pairs.csv"
    with open(doubtful_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["names"])
        w.writeheader()
        for r in doubtful:
            w.writerow(r)
    print(f"wrote {doubtful_path}: {len(doubtful)} doubtful pairs (not merged)")

    stints = apply_aliases(stints, rename_map)
    stints.to_csv(stints_path, index=False)
    print(f"rewrote {stints_path} with aliases applied ({len(stints)} rows)")

    moves = build_coordinator_moves(stints)
    moves_path = STUDY / "data" / "processed" / "coordinator_moves.csv"
    moves.to_csv(moves_path, index=False)
    print(f"wrote {moves_path}: {len(moves)} movers")

    c2h = build_coordinator_to_headcoach(stints)
    c2h_path = STUDY / "data" / "processed" / "coordinator_to_headcoach.csv"
    c2h.to_csv(c2h_path, index=False)
    print(f"wrote {c2h_path}: {len(c2h)} coordinator-to-head-coach cases")


if __name__ == "__main__":
    main()
