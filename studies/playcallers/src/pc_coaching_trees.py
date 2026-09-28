"""
The Playcallers, Phase 4: coaching trees, from staff_stints.csv only.

An edge is (mentor, protege, franchise, first_season, last_season,
protege_role) where the protege was OC or DC for a franchise-season in
which the mentor was head coach. If a season has multiple head coaches
(is_co_holder / a mid-season change producing more than one HC row), an
edge is created for each mentor and flagged.

Note: this only sees coordinators and head coaches, not position coaches,
and only 2011-2025 (the range of staff_stints.csv).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
OUT = STUDY / "data" / "processed"


def build_edges(stints: pd.DataFrame) -> pd.DataFrame:
    hcs = stints[stints["role"] == "HC"][["season", "franchise", "person"]].rename(columns={"person": "mentor"})
    coords = stints[stints["role"].isin(["OC", "DC"])][["season", "franchise", "person", "role"]].rename(
        columns={"person": "protege", "role": "protege_role"})

    edges = coords.merge(hcs, on=["season", "franchise"], how="inner")
    edges = edges[edges["mentor"] != edges["protege"]]

    multi_hc = hcs.groupby(["season", "franchise"]).size()
    multi_hc_keys = set(multi_hc[multi_hc > 1].index)
    edges["multiple_hc_flag"] = edges.apply(lambda r: (r["season"], r["franchise"]) in multi_hc_keys, axis=1)

    grouped = edges.groupby(["mentor", "protege", "franchise", "protege_role"]).agg(
        first_season=("season", "min"),
        last_season=("season", "max"),
        multiple_hc_flag=("multiple_hc_flag", "any"),
    ).reset_index()
    return grouped[["mentor", "protege", "franchise", "first_season", "last_season", "protege_role", "multiple_hc_flag"]]


def build_summary(edges: pd.DataFrame, stints: pd.DataFrame) -> pd.DataFrame:
    """Per mentor: the coordinators who served under him, and which of them
    became head coaches AFTERWARDS. A protege counts as "became head coach"
    only if he has a head-coaching season later than his first season under
    this mentor. A man who had already been a head coach before joining the
    mentor's staff (Wade Phillips under Sean McVay, say) is counted
    separately as `n_already_head_coach`; he is not a branch of this tree.
    Head-coaching seasons before 2011 are outside the data, so "already" is
    an undercount."""
    hc = stints[stints["role"] == "HC"]
    hc_seasons = hc.groupby("person")["season"].apply(lambda x: sorted(set(x))).to_dict()
    hc_rows = hc.sort_values("season")

    rows = []
    for mentor, grp in edges.groupby("mentor"):
        proteges = [p for p in grp["protege"].unique() if p != mentor]
        became_detail, already = [], []
        for prot in proteges:
            first_under = int(grp.loc[grp["protege"] == prot, "first_season"].min())
            seasons = hc_seasons.get(prot, [])
            later = [x for x in seasons if x > first_under]
            earlier = [x for x in seasons if x <= first_under]
            if earlier:
                already.append(prot)
            elif later:
                first = min(later)
                teams = list(dict.fromkeys(hc_rows.loc[(hc_rows["person"] == prot) & (hc_rows["season"] >= first),
                                                       "franchise"]))
                became_detail.append(f"{prot} ({','.join(teams)}, first HC season {first})")
        coord = stints[stints["role"].isin(["OC", "DC"]) & stints["person"].isin(proteges)]
        elsewhere = 0
        for prot in proteges:
            mentor_fr = set(grp.loc[grp["protege"] == prot, "franchise"])
            if set(coord.loc[coord["person"] == prot, "franchise"]) - mentor_fr:
                elsewhere += 1
        rows.append({
            "mentor": mentor,
            "n_distinct_coordinators": len(proteges),
            "n_became_head_coach": len(became_detail),
            "became_head_coach_detail": "; ".join(became_detail),
            "n_already_head_coach": len(already),
            "already_head_coach_detail": "; ".join(already),
            "n_coordinator_elsewhere": elsewhere,
        })
    return (pd.DataFrame(rows).sort_values(["n_became_head_coach", "n_distinct_coordinators"], ascending=False)
            .reset_index(drop=True))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    stints = pd.read_csv(OUT / "staff_stints.csv")
    edges = build_edges(stints)
    edges.to_csv(OUT / "coaching_tree_edges.csv", index=False)
    summary = build_summary(edges, stints)
    summary.to_csv(OUT / "coaching_tree_summary.csv", index=False)
    print(edges.shape, summary.shape)
    print(summary.head(10).to_string())
    return edges, summary


if __name__ == "__main__":
    run()
