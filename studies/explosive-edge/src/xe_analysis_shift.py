"""
Explosive Edge, Phase 2 analyses A-C ("the shift"): association, exchange
rate, mechanism. See docs/PLAN.md sections 0, 3, 4.

Everything here works from ONE ROW PER GAME (regular season only,
1999-2025), picked as the home team's row out of team_game.csv (team_game
has one row per team-game; dropping the away row avoids double-counting a
game in any regression). Differentials (`*_diff` columns) are already
team-minus-opponent in team_game.csv, so the home row's `explosive_*_diff`
is home-minus-away for that game.

Standardization is per-season z-scores of the differential columns,
computed on the same one-row-per-game regular-season sample the model is
fit on (ties dropped for the logit tables, since "win" isn't defined for a
tie; kept for computing the z-score would shift the scale for a handful of
seasons that have ties, so ties are dropped BEFORE standardizing too, to
keep the standardization consistent with the fit sample).

Model fitting is hand-rolled (numpy only, no statsmodels/sklearn):
  - `fit_logit_irls`: IRLS/Newton-Raphson logistic regression with a small
    L2 ridge (default 1e-6) on all coefficients except the intercept, for
    numerical stability in well-separated or small-n seasons. Standard
    errors come from the inverse of the (ridge-penalized) Hessian at
    convergence.
  - `fit_ols`: closed-form OLS with the usual (X'X)^-1 sigma^2 covariance.

Eras: 1999-2007, 2008-2016, 2017-2025 (three nine-season blocks spanning
1999-2025).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "processed"

ERAS = [("1999-2007", 1999, 2007), ("2008-2016", 2008, 2016), ("2017-2025", 2017, 2025)]
FIRST_SEASON = 1999
LAST_SEASON = 2025

EXPLOSIVE_DEFS = ["explosive_20_10", "explosive_25_15", "explosive_20_20", "explosive_epa2"]


# ------------------------------------------------------------------ data


def load_team_game(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or OUT / "team_game.csv")


def load_league_season(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or OUT / "league_season.csv")


def game_rows(team_game: pd.DataFrame, first: int = FIRST_SEASON, last: int = LAST_SEASON) -> pd.DataFrame:
    """One row per regular-season game, 1999-2025: the home team's
    team_game row (is_home == True). Differentials are already home-minus-
    away in that row. Ties (win == 0.5) are kept here; callers that need a
    binary winner drop them."""
    d = team_game[(team_game["game_type"] == "REG") & team_game["season"].between(first, last)]
    d = d[d["is_home"]].copy()
    assert d["game_id"].is_unique, "expected one row per game after is_home filter"
    return d.reset_index(drop=True)


def era_of(season: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=season.index, dtype=object)
    for label, lo, hi in ERAS:
        out = out.where(~season.between(lo, hi), label)
    return out


def zscore_within_season(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Add z_<col> columns: (x - season mean) / season sd, grouped by
    `season`. A season with zero variance (constant column) gets z = 0."""
    out = df.copy()
    for c in cols:
        grp = out.groupby("season")[c]
        mean = grp.transform("mean")
        sd = grp.transform("std", ddof=0)
        z = (out[c] - mean) / sd.replace(0.0, np.nan)
        out[f"z_{c}"] = z.fillna(0.0)
    return out


# -------------------------------------------------------------- fitters


def fit_logit_irls(X: np.ndarray, y: np.ndarray, ridge: float = 1e-6,
                    max_iter: int = 100, tol: float = 1e-10) -> dict:
    """Logistic regression by Newton-Raphson / IRLS. X must already include
    an intercept column (all-ones, conventionally column 0). A tiny L2
    ridge is applied to every coefficient EXCEPT the intercept, for
    stability on well-separated or small seasons. Returns beta, se (from
    the inverse penalized Hessian), the covariance matrix, and fit
    diagnostics (converged, n_iter, log_loss, accuracy on the training
    data)."""
    n, k = X.shape
    beta = np.zeros(k)
    R = ridge * np.eye(k)
    R[0, 0] = 0.0  # do not penalize the intercept
    converged = False
    n_iter = 0
    for it in range(1, max_iter + 1):
        eta = X @ beta
        p = 1.0 / (1.0 + np.exp(-eta))
        p = np.clip(p, 1e-12, 1 - 1e-12)
        W = p * (1 - p)
        grad = X.T @ (y - p) - R @ beta
        H = -(X.T * W) @ X - R  # negative definite (approx)
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        beta_new = beta - step
        n_iter = it
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            converged = True
            break
        beta = beta_new
    eta = X @ beta
    p = np.clip(1.0 / (1.0 + np.exp(-eta)), 1e-12, 1 - 1e-12)
    W = p * (1 - p)
    H = -(X.T * W) @ X - R
    cov = np.linalg.inv(-H)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    log_loss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    accuracy = float(np.mean((p >= 0.5).astype(float) == y))
    return {
        "beta": beta, "se": se, "cov": cov, "converged": converged, "n_iter": n_iter,
        "log_loss": log_loss, "accuracy": accuracy, "n": n,
    }


def fit_ols(X: np.ndarray, y: np.ndarray) -> dict:
    """Closed-form OLS with (X'X)^-1 sigma^2 covariance. X includes an
    intercept column."""
    n, k = X.shape
    XtX = X.T @ X
    XtX_inv = np.linalg.inv(XtX)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    dof = max(n - k, 1)
    sigma2 = float(resid @ resid / dof)
    cov = sigma2 * XtX_inv
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    ss_res = float(resid @ resid)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return {"beta": beta, "se": se, "cov": cov, "n": n, "sigma": np.sqrt(sigma2), "r2": r2}


def ols_slope(x: np.ndarray, y: np.ndarray) -> dict:
    """Simple OLS y ~ x (one predictor) with SE of the slope, via fit_ols."""
    X = np.column_stack([np.ones(len(x)), x])
    f = fit_ols(X, y)
    return {"intercept": f["beta"][0], "slope": f["beta"][1],
            "slope_se": f["se"][1], "n": f["n"], "r2": f["r2"]}


# ------------------------------------------------------------ analysis A


def _prep_binary(df: pd.DataFrame, epd_col: str, tod_col: str) -> pd.DataFrame:
    """Drop ties, then add per-season z-scores of the two differential
    columns on the decided-game sample."""
    d = df[df["win"].isin([0.0, 1.0])].copy()
    d = zscore_within_season(d, [epd_col, tod_col])
    return d


def _fit_three_models(d: pd.DataFrame, epd_col: str, tod_col: str) -> dict:
    """Fit EPD-only, TOD-only, and both (standardized) logits on one
    sample `d` (already z-scored). Returns a flat dict of results."""
    y = d["win"].to_numpy(float)
    z_epd = d[f"z_{epd_col}"].to_numpy(float)
    z_tod = d[f"z_{tod_col}"].to_numpy(float)
    raw_epd = d[epd_col].to_numpy(float)
    raw_tod = d[tod_col].to_numpy(float)
    sd_epd = raw_epd.std(ddof=0) or np.nan
    sd_tod = raw_tod.std(ddof=0) or np.nan

    n = len(d)
    ones = np.ones(n)

    res = {"n_games": n}

    X_epd = np.column_stack([ones, z_epd])
    f_epd = fit_logit_irls(X_epd, y)
    res["epd_only_b0"], res["epd_only_b_epd"] = f_epd["beta"]
    res["epd_only_se_b_epd"] = f_epd["se"][1]
    res["epd_only_b_epd_raw"] = f_epd["beta"][1] / sd_epd
    res["epd_only_se_b_epd_raw"] = f_epd["se"][1] / sd_epd
    res["epd_only_log_loss"] = f_epd["log_loss"]
    res["epd_only_accuracy"] = f_epd["accuracy"]
    res["epd_only_converged"] = f_epd["converged"]

    X_tod = np.column_stack([ones, z_tod])
    f_tod = fit_logit_irls(X_tod, y)
    res["tod_only_b0"], res["tod_only_b_tod"] = f_tod["beta"]
    res["tod_only_se_b_tod"] = f_tod["se"][1]
    res["tod_only_b_tod_raw"] = f_tod["beta"][1] / sd_tod
    res["tod_only_se_b_tod_raw"] = f_tod["se"][1] / sd_tod
    res["tod_only_log_loss"] = f_tod["log_loss"]
    res["tod_only_accuracy"] = f_tod["accuracy"]
    res["tod_only_converged"] = f_tod["converged"]

    X_both = np.column_stack([ones, z_epd, z_tod])
    f_both = fit_logit_irls(X_both, y)
    res["both_b0"], res["both_b_epd"], res["both_b_tod"] = f_both["beta"]
    res["both_se_b_epd"], res["both_se_b_tod"] = f_both["se"][1], f_both["se"][2]
    res["both_b_epd_raw"] = f_both["beta"][1] / sd_epd
    res["both_se_b_epd_raw"] = f_both["se"][1] / sd_epd
    res["both_b_tod_raw"] = f_both["beta"][2] / sd_tod
    res["both_se_b_tod_raw"] = f_both["se"][2] / sd_tod
    res["both_log_loss"] = f_both["log_loss"]
    res["both_accuracy"] = f_both["accuracy"]
    res["both_converged"] = f_both["converged"]

    return res


def shift_logit_by_season(df: pd.DataFrame, epd_col: str = "explosive_20_10_diff",
                           tod_col: str = "turnovers_diff") -> pd.DataFrame:
    """Per season 1999-2025: EPD-only, TOD-only, both logistic models of
    win ~ (standardized) differentials. See module docstring."""
    d = _prep_binary(df, epd_col, tod_col)
    rows = []
    for season, ds in d.groupby("season"):
        r = _fit_three_models(ds, epd_col, tod_col)
        r["season"] = int(season)
        rows.append(r)
    cols_first = ["season", "n_games"]
    out = pd.DataFrame(rows)
    out = out[cols_first + [c for c in out.columns if c not in cols_first]]
    return out.sort_values("season").reset_index(drop=True)


def shift_logit_by_era(df: pd.DataFrame, epd_col: str = "explosive_20_10_diff",
                        tod_col: str = "turnovers_diff") -> pd.DataFrame:
    """Same three models, pooled within each era rather than per season."""
    d = df.copy()
    d["era"] = era_of(d["season"])
    d = _prep_binary(d, epd_col, tod_col)
    rows = []
    for label, _, _ in ERAS:
        ds = d[d["era"] == label]
        if len(ds) == 0:
            continue
        r = _fit_three_models(ds, epd_col, tod_col)
        r["era"] = label
        rows.append(r)
    cols_first = ["era", "n_games"]
    out = pd.DataFrame(rows)
    out = out[cols_first + [c for c in out.columns if c not in cols_first]]
    return out


def shift_trend(by_season: pd.DataFrame) -> pd.DataFrame:
    """OLS slope of the standardized EPD coefficient (from the 'both'
    model) against season, and likewise for TOD. One row per coefficient."""
    rows = []
    for name, col in [("epd_std_coef", "both_b_epd"), ("tod_std_coef", "both_b_tod")]:
        fit = ols_slope(by_season["season"].to_numpy(float), by_season[col].to_numpy(float))
        rows.append({"coefficient": name, "slope_per_season": fit["slope"],
                     "slope_se": fit["slope_se"], "intercept": fit["intercept"],
                     "r2": fit["r2"], "n_seasons": fit["n"]})
    return pd.DataFrame(rows)


def shift_logit_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """Analysis A repeated for the sensitivity explosive definitions
    (25/15, 20/20, EPA>=2) and for the non-garbage-time (_ng) variant of
    every definition (including the primary 20/10). One row per
    season x definition. turnovers_diff (not the _ng or scrimmage variant)
    is used as TOD throughout, matching the primary spec's TOD."""
    defs = []
    for base in EXPLOSIVE_DEFS:
        defs.append(base)
        defs.append(f"{base}_ng")
    frames = []
    for name in defs:
        epd_col = f"{name}_diff"
        by_season = shift_logit_by_season(df, epd_col=epd_col, tod_col="turnovers_diff")
        by_season.insert(1, "definition", name)
        frames.append(by_season)
    return pd.concat(frames, ignore_index=True)


# ------------------------------------------------------------ analysis B


def _fit_exchange(d: pd.DataFrame, epd_col: str, tod_col: str) -> dict:
    n = len(d)
    ones = np.ones(n)
    margin = d["margin"].to_numpy(float)
    epd = d[epd_col].to_numpy(float)
    tod = d[tod_col].to_numpy(float)

    f_epd = fit_ols(np.column_stack([ones, epd]), margin)
    f_tod = fit_ols(np.column_stack([ones, tod]), margin)
    f_both = fit_ols(np.column_stack([ones, epd, tod]), margin)

    points_per_explosive = f_both["beta"][1]
    points_per_turnover = f_both["beta"][2]
    var_e = f_both["cov"][1, 1]
    var_t = f_both["cov"][2, 2]
    cov_et = f_both["cov"][1, 2]
    ratio = points_per_turnover / points_per_explosive if points_per_explosive else np.nan
    # delta method SE of ratio r = b_t / b_e
    if points_per_explosive:
        d_dbe = -points_per_turnover / points_per_explosive ** 2
        d_dbt = 1.0 / points_per_explosive
        var_ratio = d_dbe ** 2 * var_e + d_dbt ** 2 * var_t + 2 * d_dbe * d_dbt * cov_et
        ratio_se = float(np.sqrt(max(var_ratio, 0.0)))
    else:
        ratio_se = np.nan

    return {
        "n_games": n,
        "points_per_explosive": points_per_explosive,
        "points_per_explosive_se": f_both["se"][1],
        "points_per_turnover": points_per_turnover,
        "points_per_turnover_se": f_both["se"][2],
        "exchange_ratio_turnover_to_explosive": ratio,
        "exchange_ratio_se": ratio_se,
        "r2_epd_only": f_epd["r2"],
        "r2_tod_only": f_tod["r2"],
        "r2_both": f_both["r2"],
        "points_per_explosive_alone": f_epd["beta"][1],
        "points_per_explosive_alone_se": f_epd["se"][1],
        "points_per_turnover_alone": f_tod["beta"][1],
        "points_per_turnover_alone_se": f_tod["se"][1],
    }


def exchange_rate_by_season(df: pd.DataFrame, epd_col: str = "explosive_20_10_diff",
                             tod_col: str = "turnovers_diff") -> pd.DataFrame:
    """Per season 1999-2025: OLS margin ~ EPD + TOD (raw units, ties kept
    -- margin is well-defined for a tie, unlike a binary win)."""
    rows = []
    for season, ds in df.groupby("season"):
        r = _fit_exchange(ds, epd_col, tod_col)
        r["season"] = int(season)
        rows.append(r)
    out = pd.DataFrame(rows)
    cols_first = ["season", "n_games"]
    return out[cols_first + [c for c in out.columns if c not in cols_first]].sort_values("season").reset_index(drop=True)


def exchange_rate_by_era(df: pd.DataFrame, epd_col: str = "explosive_20_10_diff",
                          tod_col: str = "turnovers_diff") -> pd.DataFrame:
    d = df.copy()
    d["era"] = era_of(d["season"])
    rows = []
    for label, _, _ in ERAS:
        ds = d[d["era"] == label]
        r = _fit_exchange(ds, epd_col, tod_col)
        r["era"] = label
        rows.append(r)
    out = pd.DataFrame(rows)
    cols_first = ["era", "n_games"]
    return out[cols_first + [c for c in out.columns if c not in cols_first]]


# ------------------------------------------------------------ analysis C


def mechanism_by_season(league_season: pd.DataFrame, team_game: pd.DataFrame,
                         first: int = FIRST_SEASON, last: int = LAST_SEASON) -> pd.DataFrame:
    """Per season 1999-2025: explosive rate per play and per drive, plays
    per drive, seconds per drive, pass rate, def-play rate per snap,
    turnovers per game, yards per play. Most columns already exist in
    league_season.csv (built from REG team_game rows); yards per play is
    computed here from team_game.csv."""
    ls = league_season[league_season["season"].between(first, last)].copy()
    tg = team_game[(team_game["game_type"] == "REG") & team_game["season"].between(first, last)]
    yards_per_play = tg.groupby("season").apply(
        lambda g: g["yards"].sum() / g["plays"].sum() if g["plays"].sum() else np.nan,
        include_groups=False,
    ).rename("yards_per_play")
    out = ls.merge(yards_per_play, on="season", how="left")
    keep = ["season", "explosive_rate_per_play", "explosive_rate_per_play_ng",
            "explosive_rate_per_drive", "plays_per_drive", "seconds_per_drive",
            "pass_rate", "def_play_rate_per_snap", "turnovers_per_game", "yards_per_play"]
    return out[keep].sort_values("season").reset_index(drop=True)


def _fisher_r_se(n: int) -> float:
    return float(1.0 / np.sqrt(n - 3)) if n > 3 else np.nan


def mechanism_strategy_by_era(team_game: pd.DataFrame, first: int = FIRST_SEASON,
                               last: int = LAST_SEASON) -> pd.DataFrame:
    """Within each era, the correlation across team-seasons between a
    team's explosive rate per play and its plays per drive: does more
    explosiveness go with shorter drives? SE via Fisher z transform of the
    Pearson correlation (1/sqrt(n-3) on the z scale, mapped back to a
    symmetric CI on r would need un-transforming; here we report the
    Fisher-z SE directly alongside r and n, which is the standard way to
    report precision for a correlation)."""
    tg = team_game[(team_game["game_type"] == "REG") & team_game["season"].between(first, last)].copy()
    tg["era"] = era_of(tg["season"])
    g = tg.groupby(["era", "season", "team"]).agg(
        plays=("plays", "sum"), explosive=("explosive_20_10", "sum"),
        drives=("drives", "sum"), drive_plays_total=("drive_plays_total", "sum"),
    ).reset_index()
    g = g[(g["plays"] > 0) & (g["drives"] > 0)]
    g["explosive_rate_per_play"] = g["explosive"] / g["plays"]
    g["plays_per_drive"] = g["drive_plays_total"] / g["drives"]

    rows = []
    for label, _, _ in ERAS:
        ge = g[g["era"] == label]
        n = len(ge)
        if n > 2:
            r = float(np.corrcoef(ge["explosive_rate_per_play"], ge["plays_per_drive"])[0, 1])
        else:
            r = np.nan
        z = np.arctanh(np.clip(r, -0.999999, 0.999999)) if n > 3 and not np.isnan(r) else np.nan
        z_se = _fisher_r_se(n)
        rows.append({
            "era": label, "n_team_seasons": n, "correlation": r,
            "fisher_z": z, "fisher_z_se": z_se,
        })
    return pd.DataFrame(rows)


# -------------------------------------------------------------- pipeline


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    tg = load_team_game()
    ls = load_league_season()
    games = game_rows(tg)

    tables = {}
    tables["shift_logit_by_season"] = shift_logit_by_season(games)
    tables["shift_logit_by_era"] = shift_logit_by_era(games)
    tables["shift_trend"] = shift_trend(tables["shift_logit_by_season"])
    tables["shift_logit_sensitivity"] = shift_logit_sensitivity(games)
    tables["exchange_rate_by_season"] = exchange_rate_by_season(games)
    tables["exchange_rate_by_era"] = exchange_rate_by_era(games)
    tables["mechanism_by_season"] = mechanism_by_season(ls, tg)
    tables["mechanism_strategy_by_era"] = mechanism_strategy_by_era(tg)

    for name, table in tables.items():
        table.to_csv(OUT / f"{name}.csv", index=False)
    return tables


if __name__ == "__main__":
    run()
