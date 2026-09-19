"""
Explosive Edge, Phase 2 analyses D (persistence), E (head-to-head), and F
(team-season leaderboard). See docs/PLAN.md sections 0, 3, 4.

Everything here starts from data/processed/team_game.csv (built by
xe_metrics.team_game / xe_metrics.run), restricted to regular-season rows
(game_type == "REG"), 1999-2025. It is one row per team per game; the
`*_diff` columns are already team-minus-opponent (see xe_metrics.py's
module docstring). A "turnover differential" or "turnovers_diff" value
here keeps that same sign convention: POSITIVE means the team gave the
ball away MORE than its opponent (i.e. is worse for the team), matching
the raw column name in team_game.csv. Analysis F's "turnover differential
per game" is reported the same way, for consistency with column D and E.

Eras (fixed, matches the third boundaries PLAN.md's three-era language
implies): 1999-2007, 2008-2016, 2017-2025.

A known data quirk, not fixed here: nflverse's play-by-play `posteam`/
`defteam`/`home_team`/`away_team` columns use each franchise's CURRENT
team code for its entire history (e.g. the 1999 Raiders appear as "LV",
not "OAK"; the 1999-2015 Rams appear as "LA", not "STL"). xe_metrics.py's
franchise crosswalk maps by the code that was actually in use in a given
season, so a franchise-code row like ("LV", 1999) doesn't match any
crosswalk window and is left as "LV" instead of becoming "OAK" - the
early-era rows for the Raiders and Rams/Chargers-adjacent "LA" code carry
an un-normalized franchise id. This shows up as unmatched franchise codes
in the leaderboard/TSR merge (reported in leaderboard_unmatched.csv) and
as apparently-separate "LV"/"OAK" or "LA"/"STL" team-seasons in the
persistence and head-to-head tables. It is upstream of this module (in
xe_metrics.py, owned by a different phase) and is called out in the
run() report rather than patched here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]            # studies/explosive-edge
MAIN = REPO.parents[1]                                  # gridiron-greatness-rating repo root
TEAM_GAME_CSV = REPO / "data" / "processed" / "team_game.csv"
TSR_CSV = MAIN / "data" / "processed" / "team_season_full_profile.csv"
OUT = REPO / "data" / "processed"

ERAS = [(1999, 2007, "1999-2007"), (2008, 2016, "2008-2016"), (2017, 2025, "2017-2025")]
FIRST_SEASON, LAST_SEASON = 1999, 2025

# metric_key -> (numerator column(s), how to compute per team-season group)
PERSISTENCE_METRICS = [
    "explosive_rate_per_play",
    "explosive_diff_per_game",
    "turnovers_per_game",
    "turnover_diff_per_game",
    "margin_per_game",
    "yards_per_play",
]


def era_label(season) -> str:
    for lo, hi, label in ERAS:
        if lo <= season <= hi:
            return label
    return "other"


# ----------------------------------------------------------------- loading


def load_team_game() -> pd.DataFrame:
    """Regular-season team-game rows, 1999-2025, sorted by team-season and
    week (the order D's split-half needs)."""
    df = pd.read_csv(TEAM_GAME_CSV)
    df = df[(df["game_type"] == "REG") & df["season"].between(FIRST_SEASON, LAST_SEASON)].copy()
    df["era"] = df["season"].map(era_label)
    return df.sort_values(["franchise", "season", "week"]).reset_index(drop=True)


def load_tsr() -> pd.DataFrame:
    tsr = pd.read_csv(TSR_CSV)
    return tsr[["season", "franchise", "bayes_rating_z", "won_super_bowl", "reached_super_bowl"]]


# ---------------------------------------------------------- shared helpers


def _half_rates(g: pd.DataFrame) -> dict:
    """Per-game/per-play rates for one half of one team-season's games
    (already sliced by week order)."""
    plays = g["plays"].sum()
    return {
        "n_games": len(g),
        "explosive_rate_per_play": g["explosive_20_10"].sum() / plays if plays else np.nan,
        "explosive_diff_per_game": g["explosive_20_10_diff"].mean(),
        "turnovers_per_game": g["turnovers"].mean(),
        "turnover_diff_per_game": g["turnovers_diff"].mean(),
        "margin_per_game": g["margin"].mean(),
        "yards_per_play": g["yards"].sum() / plays if plays else np.nan,
    }


def split_half(games: pd.DataFrame) -> dict | None:
    """One team-season's games, already sorted by week. Splits into the
    first floor(n/2) games and the remaining games (second half may have
    one more game than the first when n is odd), and returns per-half
    rates for each PERSISTENCE_METRICS entry. None if n < 2 (no split
    possible)."""
    n = len(games)
    half = n // 2
    if half < 1 or n - half < 1:
        return None
    first, second = games.iloc[:half], games.iloc[half:]
    return {"n_games": n, "first": _half_rates(first), "second": _half_rates(second)}


def team_season_splits(team_game: pd.DataFrame) -> pd.DataFrame:
    """One row per team-season with first/second-half values for every
    PERSISTENCE_METRICS metric (columns "<metric>_first", "<metric>_second"),
    season, franchise, era, and n_games. Team-seasons with fewer than 2
    games are dropped (nothing to split)."""
    rows = []
    for (franchise, season), g in team_game.groupby(["franchise", "season"], sort=False):
        g = g.sort_values("week")
        split = split_half(g)
        if split is None:
            continue
        row = {"franchise": franchise, "season": season, "era": era_label(season), "n_games": split["n_games"]}
        for m in PERSISTENCE_METRICS:
            row[f"{m}_first"] = split["first"][m]
            row[f"{m}_second"] = split["second"][m]
        rows.append(row)
    return pd.DataFrame(rows)


def pearson_ci(x: np.ndarray, y: np.ndarray) -> dict:
    """Pearson r with n and a Fisher-z 95% CI. NaNs dropped pairwise.
    Returns n=0/r=NaN when fewer than 4 usable pairs (CI undefined for
    n<=3, since Fisher-z's SE uses 1/sqrt(n-3))."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4 or np.std(x) == 0 or np.std(y) == 0:
        return {"n": n, "r": np.nan, "ci_lo": np.nan, "ci_hi": np.nan}
    r = float(np.corrcoef(x, y)[0, 1])
    r_clamped = max(min(r, 0.999999), -0.999999)
    z = np.arctanh(r_clamped)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = z - 1.959963984540054 * se, z + 1.959963984540054 * se
    return {"n": n, "r": r, "ci_lo": float(np.tanh(lo)), "ci_hi": float(np.tanh(hi))}


# -------------------------------------------------------------------- D


def persistence_table(splits: pd.DataFrame, group_col: str | None) -> pd.DataFrame:
    """Split-half Pearson correlations of first-half vs second-half value,
    per PERSISTENCE_METRICS metric, grouped by `group_col` (e.g. "era" or
    "season"); group_col=None gives one "ALL" row per metric."""
    rows = []
    groups = [("ALL", splits)] if group_col is None else list(splits.groupby(group_col))
    for key, g in groups:
        for m in PERSISTENCE_METRICS:
            stats = pearson_ci(g[f"{m}_first"], g[f"{m}_second"])
            rows.append({group_col or "group": key, "metric": m, **stats})
    return pd.DataFrame(rows)


def persistence_by_era(splits: pd.DataFrame) -> pd.DataFrame:
    by_era = persistence_table(splits, "era")
    overall = persistence_table(splits, None).rename(columns={"group": "era"})
    return pd.concat([by_era, overall], ignore_index=True)


def persistence_by_season(splits: pd.DataFrame) -> pd.DataFrame:
    return persistence_table(splits, "season")


def team_season_full(team_game: pd.DataFrame) -> pd.DataFrame:
    """One row per team-season with full-season (not split) rates, for
    year-to-year persistence."""
    rows = []
    for (franchise, season), g in team_game.groupby(["franchise", "season"], sort=False):
        row = {"franchise": franchise, "season": season, "era": era_label(season), "n_games": len(g)}
        row.update(_half_rates(g))
        rows.append(row)
    return pd.DataFrame(rows)


def persistence_year_to_year(team_game: pd.DataFrame) -> pd.DataFrame:
    """Same-franchise season s vs s+1, full-season rates, correlated by
    the era of season s."""
    full = team_season_full(team_game)
    nxt = full.copy()
    nxt["season"] = nxt["season"] - 1  # so a join on (franchise, season) attaches season s+1's values to season s
    merged = full.merge(nxt, on=["franchise", "season"], suffixes=("_s", "_s1"))
    rows = []
    for era_lbl, g in merged.groupby("era_s"):
        for m in PERSISTENCE_METRICS:
            stats = pearson_ci(g[f"{m}_s"], g[f"{m}_s1"])
            rows.append({"era": era_lbl, "metric": m, **stats})
    overall = merged
    for m in PERSISTENCE_METRICS:
        stats = pearson_ci(overall[f"{m}_s"], overall[f"{m}_s1"])
        rows.append({"era": "ALL", "metric": m, **stats})
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- E


def _classify_head_to_head(games: pd.DataFrame, exp_col: str, tov_col: str) -> pd.DataFrame:
    """One row per game_id (home-team perspective), classified into the
    four PLAN.md categories plus "both_even"/"other" for the rest. Every
    game gets exactly one category and one `team_win` value (0/0.5/1) for
    whichever single team the category describes, so categories partition
    all games and win rates come from one row per game."""
    home = games[games["is_home"]].drop_duplicates(subset="game_id").set_index("game_id")
    exp_sign = np.sign(home[exp_col])
    tov_sign = np.sign(-home[tov_col])  # positive => home team WON the turnover battle (fewer giveaways)
    win = home["win"]  # 1 home win, 0 home loss, 0.5 tie

    category = pd.Series("other", index=home.index)
    team_win = pd.Series(np.nan, index=home.index)

    both_pos = (exp_sign > 0) & (tov_sign > 0)
    both_neg = (exp_sign < 0) & (tov_sign < 0)
    category[both_pos | both_neg] = "won_both"
    team_win[both_pos] = win[both_pos]
    team_win[both_neg] = (1 - win[both_neg]).where(win[both_neg] != 0.5, 0.5)

    exp_win_tov_lose = (exp_sign > 0) & (tov_sign < 0)
    tov_win_exp_lose = (exp_sign < 0) & (tov_sign > 0)
    category[exp_win_tov_lose | tov_win_exp_lose] = "won_explosive_lost_turnover"
    team_win[exp_win_tov_lose] = win[exp_win_tov_lose]
    team_win[tov_win_exp_lose] = (1 - win[tov_win_exp_lose]).where(win[tov_win_exp_lose] != 0.5, 0.5)

    exp_only_home = (exp_sign > 0) & (tov_sign == 0)
    exp_only_away = (exp_sign < 0) & (tov_sign == 0)
    category[exp_only_home | exp_only_away] = "explosive_only"
    team_win[exp_only_home] = win[exp_only_home]
    team_win[exp_only_away] = (1 - win[exp_only_away]).where(win[exp_only_away] != 0.5, 0.5)

    tov_only_home = (exp_sign == 0) & (tov_sign > 0)
    tov_only_away = (exp_sign == 0) & (tov_sign < 0)
    category[tov_only_home | tov_only_away] = "turnover_only"
    team_win[tov_only_home] = win[tov_only_home]
    team_win[tov_only_away] = (1 - win[tov_only_away]).where(win[tov_only_away] != 0.5, 0.5)

    category[(exp_sign == 0) & (tov_sign == 0)] = "both_even"

    out = home[["season"]].copy()
    out["era"] = out["season"].map(era_label)
    out["category"] = category
    out["team_win"] = team_win
    return out.reset_index()


def head_to_head_table(classified: pd.DataFrame, group_col: str | None) -> pd.DataFrame:
    categories = ["won_both", "won_explosive_lost_turnover", "explosive_only", "turnover_only", "both_even"]
    groups = [("ALL", classified)] if group_col is None else list(classified.groupby(group_col))
    rows = []
    for key, g in groups:
        for cat in categories:
            sub = g[g["category"] == cat]
            n = len(sub)
            win_rate = sub["team_win"].mean() if n and cat != "both_even" else np.nan
            rows.append({group_col or "group": key, "category": cat, "n_games": n, "win_rate": win_rate})
    return pd.DataFrame(rows)


def head_to_head_by_era(team_game: pd.DataFrame, exp_col: str = "explosive_20_10_diff",
                         tov_col: str = "turnovers_diff") -> pd.DataFrame:
    classified = _classify_head_to_head(team_game, exp_col, tov_col)
    by_era = head_to_head_table(classified, "era")
    overall = head_to_head_table(classified, None).rename(columns={"group": "era"})
    return pd.concat([by_era, overall], ignore_index=True)


def head_to_head_by_season(team_game: pd.DataFrame, exp_col: str = "explosive_20_10_diff",
                            tov_col: str = "turnovers_diff") -> pd.DataFrame:
    classified = _classify_head_to_head(team_game, exp_col, tov_col)
    return head_to_head_table(classified, "season")


# -------------------------------------------------------------------- F


def leaderboard(team_game: pd.DataFrame, tsr: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Per-team-season leaderboard merged with the main project's True
    Strength Rating. Returns (leaderboard_df, unmatched_franchise_codes) -
    unmatched codes are team-seasons present in team_game but with no TSR
    match on (season, franchise) (see module docstring on the nflverse
    current-code quirk)."""
    rows = []
    for (franchise, season), g in team_game.groupby(["franchise", "season"], sort=False):
        plays = g["plays"].sum()
        opp_explosive = g["explosive_20_10"] - g["explosive_20_10_diff"]
        wins = (g["win"] == 1).sum()
        losses = (g["win"] == 0).sum()
        ties = (g["win"] == 0.5).sum()
        rows.append({
            "franchise": franchise, "season": season, "era": era_label(season),
            "games": len(g), "wins": wins, "losses": losses, "ties": ties,
            "record": f"{wins}-{losses}-{ties}",
            "explosive_per_game": g["explosive_20_10"].mean(),
            "explosive_allowed_per_game": opp_explosive.mean(),
            "explosive_diff_per_game": g["explosive_20_10_diff"].mean(),
            "explosive_rate_per_play": g["explosive_20_10"].sum() / plays if plays else np.nan,
            "turnover_diff_per_game": g["turnovers_diff"].mean(),
            "points_per_game": g["points_for"].mean(),
            "margin_per_game": g["margin"].mean(),
        })
    board = pd.DataFrame(rows)

    merged = board.merge(tsr, on=["season", "franchise"], how="left")
    unmatched_mask = merged["bayes_rating_z"].isna()
    unmatched = sorted(merged.loc[unmatched_mask, "franchise"].unique().tolist())
    merged = merged.sort_values("explosive_diff_per_game", ascending=False).reset_index(drop=True)
    return merged, unmatched


def leaderboard_correlations(board: pd.DataFrame) -> pd.DataFrame:
    """Per era (and ALL): correlation of bayes_rating_z with explosive
    diff/game and turnover diff/game separately, and R^2 of an OLS of
    bayes_rating_z on both together, over team-seasons with a TSR match."""
    have_tsr = board.dropna(subset=["bayes_rating_z"])
    rows = []
    groups = list(have_tsr.groupby("era")) + [("ALL", have_tsr)]
    for era_lbl, g in groups:
        g = g.dropna(subset=["explosive_diff_per_game", "turnover_diff_per_game", "bayes_rating_z"])
        exp_stats = pearson_ci(g["bayes_rating_z"], g["explosive_diff_per_game"])
        tov_stats = pearson_ci(g["bayes_rating_z"], g["turnover_diff_per_game"])
        r2 = _ols_r2(g[["explosive_diff_per_game", "turnover_diff_per_game"]].to_numpy(), g["bayes_rating_z"].to_numpy())
        rows.append({
            "era": era_lbl, "n": len(g),
            "r_explosive_diff": exp_stats["r"], "r_explosive_diff_ci_lo": exp_stats["ci_lo"],
            "r_explosive_diff_ci_hi": exp_stats["ci_hi"],
            "r_turnover_diff": tov_stats["r"], "r_turnover_diff_ci_lo": tov_stats["ci_lo"],
            "r_turnover_diff_ci_hi": tov_stats["ci_hi"],
            "r2_both": r2,
        })
    return pd.DataFrame(rows)


def _ols_r2(X: np.ndarray, y: np.ndarray) -> float:
    """R^2 of an ordinary least-squares fit of y on X (with intercept)."""
    if len(y) < 4:
        return np.nan
    Xd = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    pred = Xd @ coef
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    if ss_tot == 0:
        return np.nan
    return float(1 - ss_res / ss_tot)


# -------------------------------------------------------------------- run


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    tg = load_team_game()
    tsr = load_tsr()

    splits = team_season_splits(tg)
    p_era = persistence_by_era(splits)
    p_season = persistence_by_season(splits)
    p_yoy = persistence_year_to_year(tg)
    p_era.to_csv(OUT / "persistence_by_era.csv", index=False)
    p_season.to_csv(OUT / "persistence_by_season.csv", index=False)
    p_yoy.to_csv(OUT / "persistence_year_to_year.csv", index=False)

    h_era = head_to_head_by_era(tg)
    h_season = head_to_head_by_season(tg)
    h_ng_era = head_to_head_by_era(tg, exp_col="explosive_20_10_ng_diff", tov_col="turnovers_ng_diff")
    h_era.to_csv(OUT / "head_to_head_by_era.csv", index=False)
    h_season.to_csv(OUT / "head_to_head_by_season.csv", index=False)
    h_ng_era.to_csv(OUT / "head_to_head_ng_by_era.csv", index=False)

    board, unmatched = leaderboard(tg, tsr)
    board.to_csv(OUT / "leaderboard_team_seasons.csv", index=False)
    board.sort_values("explosive_per_game", ascending=False).head(25).to_csv(
        OUT / "leaderboard_top_offenses.csv", index=False)
    board.sort_values("explosive_allowed_per_game", ascending=True).head(25).to_csv(
        OUT / "leaderboard_top_defenses.csv", index=False)
    corr = leaderboard_correlations(board)
    corr.to_csv(OUT / "leaderboard_correlations.csv", index=False)
    pd.DataFrame({"franchise": unmatched}).to_csv(OUT / "leaderboard_unmatched.csv", index=False)

    return {
        "persistence_by_era": p_era, "persistence_by_season": p_season, "persistence_year_to_year": p_yoy,
        "head_to_head_by_era": h_era, "head_to_head_by_season": h_season, "head_to_head_ng_by_era": h_ng_era,
        "leaderboard": board, "leaderboard_correlations": corr, "unmatched_franchise_codes": unmatched,
    }


if __name__ == "__main__":
    res = run()
    print(f"persistence_by_era.csv: {len(res['persistence_by_era'])} rows")
    print(f"head_to_head_by_era.csv: {len(res['head_to_head_by_era'])} rows")
    print(f"leaderboard_team_seasons.csv: {len(res['leaderboard'])} rows")
    if res["unmatched_franchise_codes"]:
        print(f"Unmatched franchise codes vs TSR: {res['unmatched_franchise_codes']}")
