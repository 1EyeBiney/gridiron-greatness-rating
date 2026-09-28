"""
The Playcallers, Phase 3: play-caller ratings.

Joins unit_season_ratings (Phase 2) to playcaller_draft (Phase 1) and
produces person-level and career-level ratings, a QB-adjusted offense
model, and a four-way mover comparison.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
XE = STUDY.parents[0] / "explosive-edge"
HFA = STUDY.parents[0] / "home-field-advantage"
OUT = STUDY / "data" / "processed"

sys.path.insert(0, str(XE / "src"))
import xe_metrics  # noqa: E402

FIRST_SEASON = 2011
LAST_SEASON = 2025


# --------------------------------------------------------------- loading


def load_inputs():
    unit = pd.read_csv(OUT / "unit_season_ratings.csv")
    draft = pd.read_csv(OUT / "playcaller_draft.csv")
    stints = pd.read_csv(OUT / "staff_stints.csv")
    return unit, draft, stints


def load_primary_qb() -> pd.DataFrame:
    """Per (season, franchise): the QB with the most starts that season,
    using home_qb/away_qb from games.csv, mapped through to_franchise."""
    games = pd.read_csv(HFA / "data" / "raw" / "nflverse" / "games.csv", low_memory=False)
    games = games[(games["season"] >= FIRST_SEASON) & (games["season"] <= LAST_SEASON)]
    games = games[games["game_type"] == "REG"] if "game_type" in games.columns else games

    cw = xe_metrics.load_crosswalk()
    home = games[["game_id", "season", "home_team", "home_qb_id", "home_qb_name"]].rename(
        columns={"home_team": "team", "home_qb_id": "qb_id", "home_qb_name": "qb_name"})
    away = games[["game_id", "season", "away_team", "away_qb_id", "away_qb_name"]].rename(
        columns={"away_team": "team", "away_qb_id": "qb_id", "away_qb_name": "qb_name"})
    starts = pd.concat([home, away], ignore_index=True)
    starts["franchise"] = xe_metrics.to_franchise(starts["team"], starts["season"], cw)
    starts = starts.dropna(subset=["qb_id"])

    counts = starts.groupby(["season", "franchise", "qb_id", "qb_name"]).size().rename("starts").reset_index()
    counts = counts.sort_values("starts", ascending=False)
    primary = counts.drop_duplicates(subset=["season", "franchise"], keep="first")
    return primary[["season", "franchise", "qb_id", "qb_name"]].rename(
        columns={"qb_id": "primary_qb_id", "qb_name": "primary_qb_name"})


# --------------------------------------------------------------- exclusion + join


def apply_exclusions(draft: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = draft.copy()
    d["_multi"] = d["proposed_playcaller"].astype(str).str.contains(r" \| ", regex=True)
    d["_missing"] = d["proposed_playcaller"].isna() | (d["proposed_playcaller"].astype(str).str.strip() == "")
    d["_midseason"] = d["midseason_change"].astype(bool)

    excl_mask = d["_midseason"] | d["_multi"] | d["_missing"]
    excluded = d[excl_mask].copy()
    reasons = []
    for _, row in excluded.iterrows():
        rs = []
        if row["_midseason"]:
            rs.append("midseason_change")
        if row["_multi"]:
            rs.append("multiple_playcallers")
        if row["_missing"]:
            rs.append("no_proposed_playcaller")
        reasons.append(";".join(rs))
    excluded["reason"] = reasons
    excluded = excluded.drop(columns=["_multi", "_missing", "_midseason"])

    kept = d[~excl_mask].drop(columns=["_multi", "_missing", "_midseason"]).copy()
    return kept, excluded


def role_lookup(stints: pd.DataFrame) -> pd.DataFrame:
    """(season, franchise, unit) -> role_that_season for the coordinator
    named in staff_stints (HC or coordinator role code -> 'HC'/'coordinator')."""
    role_col_map = {"offense": "OC", "defense": "DC"}
    rows = []
    for unit, code in role_col_map.items():
        sub = stints[stints["role"].isin([code, "HC"])][["season", "franchise", "role", "person"]].copy()
        sub["unit"] = unit
        rows.append(sub)
    long = pd.concat(rows, ignore_index=True)
    # A person can hold both HC and OC/DC in the same season (e.g. a head
    # coach who is also the titled coordinator) -> one row per
    # (season, franchise, unit, person), preferring the coordinator title.
    long = long.sort_values("role", ascending=False)  # 'OC'/'DC' before 'HC' alphabetically is false; use explicit key
    long["_pref"] = (long["role"] != "HC").astype(int)
    long = long.sort_values("_pref", ascending=False).drop_duplicates(
        subset=["season", "franchise", "unit", "person"], keep="first").drop(columns="_pref")
    return long


def attach_role(kept: pd.DataFrame, stints: pd.DataFrame) -> pd.DataFrame:
    long = role_lookup(stints)
    out = kept.copy()
    out["role_that_season"] = None
    merged = out.merge(
        long, left_on=["season", "franchise", "unit", "proposed_playcaller"],
        right_on=["season", "franchise", "unit", "person"], how="left")
    merged["role_that_season"] = np.where(
        merged["role"] == "HC", "HC", np.where(merged["role"].notna(), "coordinator", None))
    merged = merged.drop(columns=["role", "person"])
    return merged


def build_playcaller_seasons(unit: pd.DataFrame, kept: pd.DataFrame, stints: pd.DataFrame, primary_qb: pd.DataFrame) -> pd.DataFrame:
    piv = unit.pivot_table(index=["season", "franchise", "unit"], columns="metric", values="z").reset_index()
    piv = piv.rename(columns={"epa_per_play": "z_epa", "explosive_rate": "z_explosive", "yards_per_play": "z_ypp"})

    df = kept.merge(piv, on=["season", "franchise", "unit"], how="left")
    df = attach_role(df, stints)
    df = df.merge(primary_qb, on=["season", "franchise"], how="left")
    # QB columns only meaningful for offense
    df.loc[df["unit"] != "offense", ["primary_qb_id", "primary_qb_name"]] = None

    df = df.rename(columns={"proposed_playcaller": "person"})
    cols = ["season", "franchise", "unit", "person", "role_that_season", "z_epa", "z_explosive", "z_ypp",
            "basis", "confidence", "primary_qb_id", "primary_qb_name"]
    return df[cols].sort_values(["unit", "season", "franchise"]).reset_index(drop=True)


# --------------------------------------------------------------- shrinkage


def anova_variance_components(df: pd.DataFrame, value_col: str, group_col: str) -> tuple[float, float]:
    """Method-of-moments (ANOVA) estimator for a one-way random-effects
    model with unbalanced groups. Returns (sigma2, tau2), tau2 floored."""
    groups = df.groupby(group_col)[value_col]
    n_i = groups.size()
    N = n_i.sum()
    k = len(n_i)
    grand_mean = df[value_col].mean()

    ss_within = groups.apply(lambda s: ((s - s.mean()) ** 2).sum()).sum()
    df_within = N - k
    sigma2 = ss_within / df_within if df_within > 0 else df[value_col].var(ddof=1)

    group_means = groups.mean()
    ss_between = (n_i * (group_means - grand_mean) ** 2).sum()
    df_between = k - 1
    ms_between = ss_between / df_between if df_between > 0 else 0.0

    n0 = (N - (n_i ** 2).sum() / N) / (k - 1) if k > 1 else N
    tau2 = (ms_between - sigma2) / n0 if n0 > 0 else 0.0
    tau2 = max(tau2, 1e-4)
    sigma2 = max(sigma2, 1e-4)
    return sigma2, tau2


def shrink_ratings(df: pd.DataFrame, value_col: str, person_col: str, sigma2: float, tau2: float) -> pd.DataFrame:
    g = df.groupby(person_col)[value_col].agg(["mean", "count"]).rename(columns={"mean": "raw_mean", "count": "n"})
    g["rating"] = g["raw_mean"] * g["n"] / (g["n"] + sigma2 / tau2)
    g["rating_se"] = np.sqrt(1.0 / (g["n"] / sigma2 + 1.0 / tau2))
    return g.reset_index()


def build_careers(seasons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    variance_rows = []
    career_frames = []
    for unit in ("offense", "defense"):
        u = seasons[seasons["unit"] == unit].dropna(subset=["z_epa", "person"]).copy()
        sigma2, tau2 = anova_variance_components(u, "z_epa", "person")
        half_weight_n = sigma2 / tau2  # n at which shrink factor n/(n+sigma2/tau2) = 0.5
        variance_rows.append({"unit": unit, "sigma2": sigma2, "tau2": tau2, "seasons_for_half_weight": half_weight_n})

        shrunk = shrink_ratings(u, "z_epa", "person", sigma2, tau2)

        agg = u.groupby("person").agg(
            seasons=("season", "count"),
            first_season=("season", "min"),
            last_season=("season", "max"),
            mean_z_epa=("z_epa", "mean"),
            mean_z_explosive=("z_explosive", "mean"),
            mean_z_ypp=("z_ypp", "mean"),
        ).reset_index()

        franch = u.sort_values("season").groupby("person")["franchise"].apply(lambda s: list(dict.fromkeys(s))).rename("franchises").reset_index()
        agg = agg.merge(franch, on="person")
        agg["n_franchises"] = agg["franchises"].apply(len)
        agg["franchises"] = agg["franchises"].apply(lambda lst: ",".join(lst))

        best = u.loc[u.groupby("person")["z_epa"].idxmax()][["person", "season", "franchise", "z_epa"]]
        best = best.rename(columns={"season": "bs_season", "franchise": "bs_franchise", "z_epa": "bs_z"})
        best["best_season"] = best.apply(lambda r: f"{int(r.bs_season)} {r.bs_franchise} z={r.bs_z:.2f}", axis=1)
        worst = u.loc[u.groupby("person")["z_epa"].idxmin()][["person", "season", "franchise", "z_epa"]]
        worst = worst.rename(columns={"season": "ws_season", "franchise": "ws_franchise", "z_epa": "ws_z"})
        worst["worst_season"] = worst.apply(lambda r: f"{int(r.ws_season)} {r.ws_franchise} z={r.ws_z:.2f}", axis=1)

        unverified = u["basis"].isin(["model_knowledge_unverified", "default_no_coordinator_headcoach"])
        share_unv = unverified.groupby(u["person"]).mean().rename("share_unverified").reset_index()

        agg = agg.merge(best[["person", "best_season"]], on="person").merge(worst[["person", "worst_season"]], on="person")
        agg = agg.merge(share_unv, on="person")
        agg = agg.merge(shrunk[["person", "rating", "rating_se"]], on="person")

        agg["rank_in_unit"] = np.nan
        eligible = agg["seasons"] >= 3
        agg.loc[eligible, "rank_in_unit"] = agg.loc[eligible, "rating"].rank(ascending=False, method="min")
        agg["unit"] = unit
        career_frames.append(agg)

    careers = pd.concat(career_frames, ignore_index=True)
    cols = ["person", "unit", "seasons", "first_season", "last_season", "franchises", "n_franchises",
            "mean_z_epa", "best_season", "worst_season", "share_unverified", "rating", "rating_se",
            "rank_in_unit", "mean_z_explosive", "mean_z_ypp"]
    careers = careers[cols].sort_values(["unit", "rating"], ascending=[True, False]).reset_index(drop=True)
    variance = pd.DataFrame(variance_rows)
    return careers, variance


# --------------------------------------------------------------- QB-adjusted model


def ridge_crossed_fit(y, caller_idx, qb_idx, n_callers, n_qbs, lam_caller, lam_qb):
    """Fit y = caller_effect[caller_idx] + qb_effect[qb_idx] via ridge,
    with a sum-to-zero-ish identification from the ridge penalty itself
    (no explicit intercept; penalizing both blocks keeps it identified)."""
    n = len(y)
    X = np.zeros((n, n_callers + n_qbs))
    X[np.arange(n), caller_idx] = 1.0
    X[np.arange(n), n_callers + qb_idx] = 1.0
    penalty = np.concatenate([np.full(n_callers, lam_caller), np.full(n_qbs, lam_qb)])
    XtX = X.T @ X + np.diag(penalty)
    Xty = X.T @ y
    b = np.linalg.solve(XtX, Xty)
    return b[:n_callers], b[n_callers:]


def cv_select_lambdas(data: pd.DataFrame, grid=(0.5, 1, 2, 5, 10, 20)) -> tuple[float, float, pd.DataFrame]:
    seasons = sorted(data["season"].unique())
    callers = sorted(data["person"].unique())
    qbs = sorted(data["primary_qb_id"].dropna().unique())
    c_idx = {c: i for i, c in enumerate(callers)}
    q_idx = {q: i for i, q in enumerate(qbs)}

    results = []
    for lam_c in grid:
        for lam_q in grid:
            errs = []
            for held in seasons:
                train = data[data["season"] != held]
                test = data[data["season"] == held]
                if test.empty or train.empty:
                    continue
                tr_c = train["person"].map(c_idx).to_numpy()
                tr_q = train["primary_qb_id"].map(q_idx).to_numpy()
                caller_eff, qb_eff = ridge_crossed_fit(
                    train["z_epa"].to_numpy(), tr_c, tr_q, len(callers), len(qbs), lam_c, lam_q)
                te_c = test["person"].map(c_idx)
                te_q = test["primary_qb_id"].map(q_idx)
                valid = te_c.notna() & te_q.notna()
                if not valid.any():
                    continue
                pred = caller_eff[te_c[valid].astype(int)] + qb_eff[te_q[valid].astype(int)]
                actual = test.loc[valid, "z_epa"].to_numpy()
                errs.append(np.mean((pred - actual) ** 2))
            if errs:
                results.append({"lam_caller": lam_c, "lam_qb": lam_q, "cv_mse": np.mean(errs)})
    cv_df = pd.DataFrame(results)
    best = cv_df.loc[cv_df["cv_mse"].idxmin()]
    return best["lam_caller"], best["lam_qb"], cv_df


def build_qb_adjusted(seasons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    off = seasons[(seasons["unit"] == "offense")].dropna(subset=["z_epa", "person", "primary_qb_id"]).copy()

    lam_caller, lam_qb, cv_df = cv_select_lambdas(off)

    callers = sorted(off["person"].unique())
    qbs = sorted(off["primary_qb_id"].unique())
    c_idx = {c: i for i, c in enumerate(callers)}
    q_idx = {q: i for i, q in enumerate(qbs)}
    caller_eff, qb_eff = ridge_crossed_fit(
        off["z_epa"].to_numpy(), off["person"].map(c_idx).to_numpy(), off["primary_qb_id"].map(q_idx).to_numpy(),
        len(callers), len(qbs), lam_caller, lam_qb)

    # caller-only and QB-only CV errors for comparison, at their own best single-block lambda from the same grid
    def cv_single(block_col, grid=(0.5, 1, 2, 5, 10, 20)):
        seasons_list = sorted(off["season"].unique())
        best_mse, best_lam = np.inf, grid[0]
        for lam in grid:
            errs = []
            groups = sorted(off[block_col].unique())
            gidx = {g: i for i, g in enumerate(groups)}
            for held in seasons_list:
                train = off[off["season"] != held]
                test = off[off["season"] == held]
                tr_idx = train[block_col].map(gidx).to_numpy()
                X = np.zeros((len(train), len(groups)))
                X[np.arange(len(train)), tr_idx] = 1.0
                XtX = X.T @ X + np.diag(np.full(len(groups), lam))
                b = np.linalg.solve(XtX, X.T @ train["z_epa"].to_numpy())
                te_idx = test[block_col].map(gidx)
                valid = te_idx.notna()
                if not valid.any():
                    continue
                pred = b[te_idx[valid].astype(int)]
                errs.append(np.mean((pred - test.loc[valid, "z_epa"].to_numpy()) ** 2))
            mse = np.mean(errs) if errs else np.inf
            if mse < best_mse:
                best_mse, best_lam = mse, lam
        return best_mse, best_lam

    caller_only_mse, caller_only_lam = cv_single("person")
    qb_only_mse, qb_only_lam = cv_single("primary_qb_id")

    cv_summary = pd.DataFrame([
        {"model": "crossed_caller_qb", "lam_caller": lam_caller, "lam_qb": lam_qb, "cv_mse": cv_df["cv_mse"].min()},
        {"model": "caller_only", "lam_caller": caller_only_lam, "lam_qb": None, "cv_mse": caller_only_mse},
        {"model": "qb_only", "lam_caller": None, "lam_qb": qb_only_lam, "cv_mse": qb_only_mse},
    ])

    # separability: caller is non-separable if every one of his seasons has
    # a QB who never played for any OTHER caller in the dataset
    qb_to_callers = off.groupby("primary_qb_id")["person"].apply(set)
    caller_rows = []
    for c in callers:
        sub = off[off["person"] == c]
        distinct_qbs = sub["primary_qb_id"].unique()
        separable = False
        for q in distinct_qbs:
            other_callers = qb_to_callers[q] - {c}
            if other_callers:
                separable = True
                break
        caller_rows.append({
            "person": c, "rating_qb_adjusted": caller_eff[c_idx[c]],
            "n_seasons": len(sub), "n_distinct_qbs": len(distinct_qbs), "separable": separable,
        })
    caller_out = pd.DataFrame(caller_rows).sort_values("rating_qb_adjusted", ascending=False).reset_index(drop=True)

    qb_out = pd.DataFrame({"primary_qb_id": qbs, "qb_effect": qb_eff})
    qb_name_map = off.drop_duplicates("primary_qb_id").set_index("primary_qb_id")["primary_qb_name"] if "primary_qb_name" in off.columns else None
    if qb_name_map is not None:
        qb_out["primary_qb_name"] = qb_out["primary_qb_id"].map(qb_name_map)
    qb_out = qb_out.sort_values("qb_effect", ascending=False).reset_index(drop=True)

    return caller_out, qb_out, cv_summary


# --------------------------------------------------------------- moves


def build_moves(seasons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for unit in ("offense", "defense"):
        u = seasons[(seasons["unit"] == unit)].dropna(subset=["person"]).copy()
        u = u.sort_values(["person", "season"])
        for person, grp in u.groupby("person"):
            grp = grp.sort_values("season")
            franchises_in_order = grp["franchise"].tolist()
            seasons_list = grp["season"].tolist()
            for i in range(len(grp) - 1):
                fr_a, s = franchises_in_order[i], seasons_list[i]
                fr_b, t = franchises_in_order[i + 1], seasons_list[i + 1]
                if fr_a == fr_b:
                    continue
                # old_team_with: A's unit z in season s (his last season there)
                old_with_row = u[(u["franchise"] == fr_a) & (u["season"] == s)]
                # old_team_after: A's unit z in season s+1, whoever called plays -> use unit table directly
                old_after = seasons[(seasons["unit"] == unit) & (seasons["franchise"] == fr_a) & (seasons["season"] == s + 1)]
                new_before = seasons[(seasons["unit"] == unit) & (seasons["franchise"] == fr_b) & (seasons["season"] == t - 1)]
                new_with_row = grp[(grp["franchise"] == fr_b) & (grp["season"] == t)]
                if old_with_row.empty or new_with_row.empty:
                    continue
                old_with = old_with_row["z_epa"].iloc[0]
                new_with = new_with_row["z_epa"].iloc[0]
                old_after_z = old_after["z_epa"].iloc[0] if not old_after.empty else np.nan
                new_before_z = new_before["z_epa"].iloc[0] if not new_before.empty else np.nan
                rows.append({
                    "person": person, "unit": unit,
                    "old_franchise": fr_a, "old_season": s, "new_franchise": fr_b, "new_season": t,
                    "old_team_with": old_with, "old_team_after": old_after_z,
                    "new_team_before": new_before_z, "new_team_with": new_with,
                    "departure_change": old_after_z - old_with if pd.notna(old_after_z) else np.nan,
                    "arrival_change": new_with - new_before_z if pd.notna(new_before_z) else np.nan,
                })
    moves = pd.DataFrame(rows)
    return moves


def _tercile_labels(z: pd.Series) -> pd.Series:
    return pd.qcut(z, 3, labels=["low", "mid", "high"], duplicates="drop")


def build_moves_summary(moves: pd.DataFrame, seasons: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # all-unit-seasons baseline (year over year change for the SAME franchise-unit, regardless of person)
    base_all = {}
    base_tercile = {}
    for unit in ("offense", "defense"):
        u = seasons[seasons["unit"] == unit].dropna(subset=["z_epa"]).copy()
        piv = u.pivot_table(index="franchise", columns="season", values="z_epa")
        changes = []
        starts = []
        for fr in piv.index:
            s = piv.loc[fr].dropna()
            yrs = sorted(s.index)
            for i in range(len(yrs) - 1):
                if yrs[i + 1] == yrs[i] + 1:
                    changes.append(s[yrs[i + 1]] - s[yrs[i]])
                    starts.append(s[yrs[i]])
        changes = pd.Series(changes)
        starts = pd.Series(starts)
        base_all[unit] = (changes.mean(), changes.std(ddof=1) / np.sqrt(len(changes)), len(changes))
        terc = _tercile_labels(starts)
        base_tercile[unit] = {}
        for lab in terc.cat.categories:
            sub = changes[terc == lab]
            if len(sub):
                base_tercile[unit][lab] = (sub.mean(), sub.std(ddof=1) / np.sqrt(len(sub)) if len(sub) > 1 else np.nan, len(sub))

    for unit in ("offense", "defense"):
        m = moves[moves["unit"] == unit]
        for col, label in (("arrival_change", "arrival_change"), ("departure_change", "departure_change")):
            s = m[col].dropna()
            n = len(s)
            mean = s.mean() if n else np.nan
            se = s.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
            rows.append({"unit": unit, "quantity": label, "n": n, "mean": mean, "se": se})
        mean_b, se_b, n_b = base_all[unit]
        rows.append({"unit": unit, "quantity": "baseline_all_unit_seasons_change", "n": n_b, "mean": mean_b, "se": se_b})
        for lab, (mean_t, se_t, n_t) in base_tercile[unit].items():
            rows.append({"unit": unit, "quantity": f"baseline_tercile_{lab}", "n": n_t, "mean": mean_t, "se": se_t})
    return pd.DataFrame(rows)


# --------------------------------------------------------------- run


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    unit, draft, stints = load_inputs()
    primary_qb = load_primary_qb()

    kept, excluded = apply_exclusions(draft)
    excluded.to_csv(OUT / "playcaller_excluded_unit_seasons.csv", index=False)

    seasons = build_playcaller_seasons(unit, kept, stints, primary_qb)
    seasons.to_csv(OUT / "playcaller_seasons.csv", index=False)

    careers, variance = build_careers(seasons)
    careers.to_csv(OUT / "playcaller_careers.csv", index=False)
    variance.to_csv(OUT / "playcaller_variance_components.csv", index=False)

    caller_qb, qb_eff, cv_summary = build_qb_adjusted(seasons)
    caller_qb.to_csv(OUT / "playcaller_qb_adjusted.csv", index=False)
    qb_eff.to_csv(OUT / "qb_effects_from_caller_model.csv", index=False)
    cv_summary.to_csv(OUT / "playcaller_qb_model_cv.csv", index=False)

    moves = build_moves(seasons)
    moves.to_csv(OUT / "playcaller_moves.csv", index=False)
    moves_summary = build_moves_summary(moves, seasons)
    moves_summary.to_csv(OUT / "playcaller_moves_summary.csv", index=False)

    print("excluded rows:", len(excluded))
    print("playcaller_seasons rows:", len(seasons))
    print(variance)
    print(cv_summary)
    print(moves_summary)
    return {
        "seasons": seasons, "careers": careers, "variance": variance,
        "caller_qb": caller_qb, "qb_eff": qb_eff, "cv_summary": cv_summary,
        "moves": moves, "moves_summary": moves_summary, "excluded": excluded,
    }


if __name__ == "__main__":
    run()
