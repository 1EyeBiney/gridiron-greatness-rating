"""
The Playcallers, Phase 2: opponent-adjusted unit ratings.

For each season (2011-2025, regular season only) and each metric, fit a
weighted least-squares model on team-games:

    y = mu + OFF[offense team] - DEF[defense team] + h * is_home

weighted by plays, with a small ridge penalty on OFF/DEF so the model is
identified (sum-to-zero is implied approximately by the ridge, not imposed
exactly). OFF is the offense's schedule-adjusted rating; DEF is the
defense's rating, where a HIGHER DEF value means a defense that holds
opponents further BELOW average (i.e. good defense = high DEF).

Metrics: epa_per_play (primary), explosive_rate, yards_per_play.
Output: data/processed/unit_season_ratings.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
XE = STUDY.parents[0] / "explosive-edge"
OUT = STUDY / "data" / "processed"

FIRST_SEASON = 1999
LAST_SEASON = 2025
RIDGE = 1.0  # ridge penalty on OFF/DEF coefficients (identification + shrinkage)

METRICS = {
    "epa_per_play": ("epa_total", "plays"),
    "explosive_rate": ("explosive_20_10", "plays"),
    "yards_per_play": ("yards", "plays"),
}


def load_team_game() -> pd.DataFrame:
    tg = pd.read_csv(XE / "data" / "processed" / "team_game.csv")
    tg = tg[(tg["game_type"] == "REG") & (tg["season"] >= FIRST_SEASON) & (tg["season"] <= LAST_SEASON)].copy()
    return tg


def _design_matrix(games: pd.DataFrame, teams: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Build the X matrix for one season: columns [mu, OFF_1..OFF_T, DEF_1..DEF_T, home].
    Each row is one team-game (offense = franchise, defense = opp_franchise)."""
    n = len(games)
    t = len(teams)
    idx = {team: i for i, team in enumerate(teams)}
    X = np.zeros((n, 1 + t + t + 1))
    X[:, 0] = 1.0  # mu
    off_idx = games["franchise"].map(idx).to_numpy()
    def_idx = games["opp_franchise"].map(idx).to_numpy()
    rows = np.arange(n)
    X[rows, 1 + off_idx] = 1.0
    X[rows, 1 + t + def_idx] = -1.0
    X[:, -1] = games["is_home"].astype(float).to_numpy()
    return X, np.array(teams)


def fit_season_metric(games: pd.DataFrame, num_col: str, den_col: str) -> pd.DataFrame:
    teams = sorted(games["franchise"].unique())
    y = (games[num_col] / games[den_col]).to_numpy()
    w = games[den_col].to_numpy().astype(float)
    X, teams_arr = _design_matrix(games, teams)
    t = len(teams)

    # Weighted ridge regression: minimize sum(w*(y - X@b)^2) + ridge * ||b_offdef||^2
    W = np.diag(w)
    XtWX = X.T @ W @ X
    XtWy = X.T @ (w * y)
    penalty = np.zeros(X.shape[1])
    penalty[1:1 + 2 * t] = RIDGE  # penalize OFF and DEF coefficients, not mu or home
    XtWX_reg = XtWX + np.diag(penalty)
    b = np.linalg.solve(XtWX_reg, XtWy)

    off = b[1:1 + t]
    defn = b[1 + t:1 + 2 * t]
    return pd.DataFrame({"franchise": teams_arr, "off_raw_coef": off, "def_raw_coef": defn})


def raw_means(games: pd.DataFrame, num_col: str, den_col: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """raw_value: unadjusted per-play mean. For offense: team's own num/den
    summed over its games. For defense: what OPPONENTS did against it,
    i.e. summed num/den of the games where this team was on defense."""
    off = games.groupby("franchise").apply(
        lambda g: g[num_col].sum() / g[den_col].sum(), include_groups=False
    ).rename("raw_value").reset_index().rename(columns={"franchise": "franchise"})
    off_games = games.groupby("franchise").size().rename("games").reset_index()
    off = off.merge(off_games, on="franchise")

    defn = games.groupby("opp_franchise").apply(
        lambda g: g[num_col].sum() / g[den_col].sum(), include_groups=False
    ).rename("raw_value").reset_index().rename(columns={"opp_franchise": "franchise"})
    def_games = games.groupby("opp_franchise").size().rename("games").reset_index().rename(columns={"opp_franchise": "franchise"})
    defn = defn.merge(def_games, on="franchise")
    return off, defn


def build() -> pd.DataFrame:
    tg = load_team_game()
    all_rows = []
    for season, games in tg.groupby("season"):
        for metric, (num_col, den_col) in METRICS.items():
            coefs = fit_season_metric(games, num_col, den_col)
            off_raw, def_raw = raw_means(games, num_col, den_col)

            off = coefs[["franchise", "off_raw_coef"]].merge(off_raw, on="franchise")
            off["adjusted"] = off["off_raw_coef"]
            off["z"] = (off["adjusted"] - off["adjusted"].mean()) / off["adjusted"].std(ddof=0)
            off["unit"] = "offense"

            de = coefs[["franchise", "def_raw_coef"]].merge(def_raw, on="franchise")
            de["adjusted"] = de["def_raw_coef"]  # already signed so higher = better defense
            de["z"] = (de["adjusted"] - de["adjusted"].mean()) / de["adjusted"].std(ddof=0)
            de["unit"] = "defense"

            for df in (off, de):
                df["season"] = season
                df["metric"] = metric
            all_rows.append(off[["season", "franchise", "unit", "metric", "games", "raw_value", "adjusted", "z"]])
            all_rows.append(de[["season", "franchise", "unit", "metric", "games", "raw_value", "adjusted", "z"]])
    out = pd.concat(all_rows, ignore_index=True)
    return out


def sanity_report(out: pd.DataFrame) -> str:
    lines = []
    epa = out[out["metric"] == "epa_per_play"]
    for unit in ("offense", "defense"):
        u = epa[epa["unit"] == unit]
        # for defense, raw_value is opponent epa/play against them: lower raw = better defense
        # so correlate adjusted vs raw with sign flipped for defense to check consistent direction
        raw = u["raw_value"] if unit == "offense" else -u["raw_value"]
        corr = np.corrcoef(u["adjusted"], raw)[0, 1]
        lines.append(f"{unit} epa_per_play: corr(adjusted, raw{'*(-1) for defense' if unit=='defense' else ''}) = {corr:.3f}")

        agg = u.groupby("franchise")["z"].mean().sort_values(ascending=False)
        lines.append(f"Top 5 {unit} (epa z, 1999-2025 avg): " + ", ".join(f"{f}={v:.2f}" for f, v in agg.head(5).items()))
        lines.append(f"Bottom 5 {unit} (epa z, 1999-2025 avg): " + ", ".join(f"{f}={v:.2f}" for f, v in agg.tail(5).items()))
    return "\n".join(lines)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    out = build()
    out.to_csv(OUT / "unit_season_ratings.csv", index=False)
    report = sanity_report(out)
    print(report)
    return out, report


if __name__ == "__main__":
    run()
