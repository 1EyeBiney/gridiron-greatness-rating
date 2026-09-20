"""
Explosive Edge, follow-up analyses promoted from the overnight exploration
(exploration/exploration_plays.py, exploration/exploration_teams.py; see
docs/NOTES.md "2026-09-20 -- Overnight exploration and where we left off"
and exploration/MORNING_REPORT.md for the original findings). This module
lifts the six recommended analyses into tested, production CSVs, matching
the style of xe_analysis_shift.py and xe_analysis_teams.py: pure functions
+ a run() that writes data/processed/*.csv. Regular season unless noted.

Reuses fit_logit_irls / zscore_within_season / era_of / ERAS from
xe_analysis_shift.py rather than reimplementing them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "processed"
PBP_DIR = REPO / "data" / "raw" / "nflverse_pbp"
GAMES_CSV = Path(r"C:\nbs\gridiron-greatness-rating\studies\home-field-advantage\data\raw\nflverse\games.csv")

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
import xe_metrics as xm  # noqa: E402
from xe_analysis_shift import (  # noqa: E402
    ERAS, era_of, fit_logit_irls, zscore_within_season, load_team_game,
)

FIRST_SEASON, LAST_SEASON = 1999, 2025
GARBAGE_WP_LO, GARBAGE_WP_HI = xm.GARBAGE_WP_LO, xm.GARBAGE_WP_HI


# ===================================================================
# 1. Competitive-time-only win logit
# ===================================================================


def competitive_time_logit_by_era(team_game: pd.DataFrame) -> pd.DataFrame:
    """Re-runs the core win-association logit (win ~ standardized explosive
    differential + turnover differential) on ONLY competitive-time plays
    (the _ng, "no garbage", columns: win probability in [0.05, 0.95]),
    pooled and by era, alongside the same-games all-plays coefficients, so
    the gap between the two coefficients (epd_minus_tod_gap) can be
    compared with and without garbage time. One row per (era incl. ALL)."""
    reg = team_game[team_game["game_type"] == "REG"]
    home = reg[reg["is_home"]].copy()
    d = home[home["win"].isin([0.0, 1.0])].copy()
    d["era"] = era_of(d["season"])

    epd_ng, tod_ng = "explosive_20_10_ng_diff", "turnovers_ng_diff"
    epd_all, tod_all = "explosive_20_10_diff", "turnovers_diff"

    def fit_one(sub: pd.DataFrame, epd_col: str, tod_col: str) -> dict:
        sub = zscore_within_season(sub, [epd_col, tod_col])
        y = sub["win"].to_numpy(float)
        X = np.column_stack([np.ones(len(sub)), sub[f"z_{epd_col}"].to_numpy(float), sub[f"z_{tod_col}"].to_numpy(float)])
        fit = fit_logit_irls(X, y)
        return {"b_epd": fit["beta"][1], "se_epd": fit["se"][1],
                "b_tod": fit["beta"][2], "se_tod": fit["se"][2],
                "log_loss": fit["log_loss"], "accuracy": fit["accuracy"]}

    groups = [("ALL", FIRST_SEASON, LAST_SEASON)] + ERAS
    rows = []
    for label, lo, hi in groups:
        sub = d[(d["season"] >= lo) & (d["season"] <= hi)]
        if len(sub) == 0:
            continue
        ng = fit_one(sub, epd_ng, tod_ng)
        allp = fit_one(sub, epd_all, tod_all)
        rows.append({
            "era": label, "n_games": len(sub),
            "ng_b_epd": ng["b_epd"], "ng_se_epd": ng["se_epd"],
            "ng_b_tod": ng["b_tod"], "ng_se_tod": ng["se_tod"],
            "ng_epd_minus_tod_gap": ng["b_epd"] - abs(ng["b_tod"]),
            "ng_log_loss": ng["log_loss"], "ng_accuracy": ng["accuracy"],
            "all_b_epd": allp["b_epd"], "all_se_epd": allp["se_epd"],
            "all_b_tod": allp["b_tod"], "all_se_tod": allp["se_tod"],
            "all_epd_minus_tod_gap": allp["b_epd"] - abs(allp["b_tod"]),
            "all_log_loss": allp["log_loss"], "all_accuracy": allp["accuracy"],
        })
    return pd.DataFrame(rows)


# ===================================================================
# 2. Playoffs
# ===================================================================


def regseason_team_season(team_game: pd.DataFrame) -> pd.DataFrame:
    """Per (franchise, season), regular season: explosive and turnover
    differential per game, used as the playoff predictors."""
    reg = team_game[team_game["game_type"] == "REG"]
    return reg.groupby(["franchise", "season"], as_index=False).agg(
        games=("game_id", "count"),
        explosive_diff_pg=("explosive_20_10_diff", "mean"),
        turnover_diff_pg=("turnovers_diff", "mean"),
    )


def playoff_prediction(team_game: pd.DataFrame, team_season: pd.DataFrame) -> pd.DataFrame:
    """For POST games, logistic regression of the playoff win on the
    difference between the two teams' REGULAR-SEASON explosive diff/game
    and turnover diff/game (standardized), pooled ("ALL") and by era."""
    post = team_game[team_game["game_type"] == "POST"].copy()
    post = post[post["is_home"]].copy()
    post = post.merge(team_season, on=["franchise", "season"], how="left")
    post = post.rename(columns={"explosive_diff_pg": "home_epd_reg", "turnover_diff_pg": "home_tod_reg"})
    post = post.merge(team_season, left_on=["opp_franchise", "season"], right_on=["franchise", "season"],
                       how="left", suffixes=("", "_opp"))
    post = post.rename(columns={"explosive_diff_pg": "away_epd_reg", "turnover_diff_pg": "away_tod_reg"})
    post["d_epd"] = post["home_epd_reg"] - post["away_epd_reg"]
    post["d_tod"] = post["home_tod_reg"] - post["away_tod_reg"]
    post = post.dropna(subset=["d_epd", "d_tod"])
    post = post[post["win"].isin([0.0, 1.0])].copy()

    def zscore(col):
        return (post[col] - post[col].mean()) / post[col].std(ddof=0)
    post["z_d_epd"] = zscore("d_epd")
    post["z_d_tod"] = zscore("d_tod")

    groups = [("ALL", FIRST_SEASON, LAST_SEASON)] + ERAS
    rows = []
    for label, lo, hi in groups:
        sub = post[(post["season"] >= lo) & (post["season"] <= hi)]
        if len(sub) < 20:
            continue
        y = sub["win"].to_numpy(float)
        X = np.column_stack([np.ones(len(sub)), sub["z_d_epd"].to_numpy(float), sub["z_d_tod"].to_numpy(float)])
        fit = fit_logit_irls(X, y)
        rows.append({"era": label, "n_games": len(sub), "b0": fit["beta"][0],
                      "b_epd": fit["beta"][1], "se_epd": fit["se"][1],
                      "b_tod": fit["beta"][2], "se_tod": fit["se"][2],
                      "log_loss": fit["log_loss"], "accuracy": fit["accuracy"]})
    return pd.DataFrame(rows)


def playoff_head_to_head(team_game: pd.DataFrame) -> pd.DataFrame:
    """Head-to-head categories (mirrors xe_analysis_teams.py's
    classification exactly), restricted to POST games, pooled across all
    eras. turnovers_diff sign is flipped since it is team-minus-opponent
    giveaways: negative = won the turnover battle."""
    post = team_game[team_game["game_type"] == "POST"]
    home = post[post["is_home"]].drop_duplicates(subset="game_id").set_index("game_id")
    exp_sign = np.sign(home["explosive_20_10_diff"])
    tov_sign = np.sign(-home["turnovers_diff"])
    win = home["win"]

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

    categories = ["won_both", "won_explosive_lost_turnover", "explosive_only", "turnover_only", "both_even"]
    rows = []
    for cat in categories:
        mask = category == cat
        n = int(mask.sum())
        win_rate = team_win[mask].mean() if n and cat != "both_even" else np.nan
        rows.append({"category": cat, "n_games": n, "win_rate": win_rate})
    return pd.DataFrame(rows)


def super_bowl_ranks(team_game: pd.DataFrame, team_season: pd.DataFrame) -> pd.DataFrame:
    """Each Super Bowl champion's regular-season rank (1 = best) in
    explosive differential/game (higher is better, so rank descending) and
    turnover differential/game (LOWER is better -- fewer giveaways than
    takeaways -- so rank ascending)."""
    post = team_game[team_game["game_type"] == "POST"].copy()
    sb_week = post.groupby("season")["week"].max().rename("sb_week")
    post = post.merge(sb_week, on="season")
    sb = post[post["week"] == post["sb_week"]]
    sb_winner = sb[sb["win"] == 1.0][["season", "franchise"]].drop_duplicates("season")

    ts = team_season.copy()
    ts["epd_rank"] = ts.groupby("season")["explosive_diff_pg"].rank(ascending=False, method="min")
    ts["tod_rank"] = ts.groupby("season")["turnover_diff_pg"].rank(ascending=True, method="min")

    rows = []
    for _, r in sb_winner.iterrows():
        m = ts[(ts["season"] == r["season"]) & (ts["franchise"] == r["franchise"])]
        if len(m) == 0:
            continue
        m = m.iloc[0]
        rows.append({"season": int(r["season"]), "champion": r["franchise"],
                      "n_teams": int(ts[ts["season"] == r["season"]].shape[0]),
                      "explosive_diff_pg": m["explosive_diff_pg"], "epd_rank": m["epd_rank"],
                      "turnover_diff_pg": m["turnover_diff_pg"], "tod_rank": m["tod_rank"]})
    out = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    summary = pd.DataFrame([{
        "season": "median", "champion": "", "n_teams": np.nan,
        "explosive_diff_pg": np.nan, "epd_rank": out["epd_rank"].median() if len(out) else np.nan,
        "turnover_diff_pg": np.nan, "tod_rank": out["tod_rank"].median() if len(out) else np.nan,
    }])
    return pd.concat([out, summary], ignore_index=True)


# ===================================================================
# 3. QB continuity and explosiveness
# ===================================================================


def load_games() -> pd.DataFrame:
    return pd.read_csv(GAMES_CSV, usecols=[
        "game_id", "season", "week", "game_type", "home_team", "away_team",
        "home_qb_id", "away_qb_id", "home_qb_name", "away_qb_name",
    ])


def build_qb_team_game(team_game: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game (REG only) with the starting QB attached, by
    joining the home-field-advantage study's games.csv (which carries
    per-game starting QBs; the explosive-edge pbp does not)."""
    reg = team_game[team_game["game_type"] == "REG"].copy()
    home_qb = games[["game_id", "home_team", "home_qb_id", "home_qb_name"]].rename(
        columns={"home_team": "team", "home_qb_id": "qb_id", "home_qb_name": "qb_name"})
    away_qb = games[["game_id", "away_team", "away_qb_id", "away_qb_name"]].rename(
        columns={"away_team": "team", "away_qb_id": "qb_id", "away_qb_name": "qb_name"})
    qb_long = pd.concat([home_qb, away_qb], ignore_index=True)
    out = reg.merge(qb_long, on=["game_id", "team"], how="left")
    out["explosive_pass_rate"] = np.where(out["dropbacks"] > 0, out["explosive_20_10"] / out["dropbacks"], np.nan)
    return out


def _fisher_ci(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 3 or pd.isna(r):
        return (np.nan, np.nan)
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    se = 1.0 / np.sqrt(n - 3)
    zcrit = 1.959963984540054
    return (float(np.tanh(z - zcrit * se)), float(np.tanh(z + zcrit * se)))


def qb_continuity_persistence(qtg: pd.DataFrame) -> pd.DataFrame:
    """Year-to-year correlation of team explosive-pass rate per dropback,
    split by whether the primary starting QB (most starts that
    team-season) stayed the same team-to-team-season vs changed."""
    reg = qtg.dropna(subset=["qb_id"]).copy()
    starts = reg.groupby(["franchise", "season", "qb_id"], as_index=False)["game_id"].count().rename(
        columns={"game_id": "n_starts"})
    primary = starts.sort_values("n_starts", ascending=False).drop_duplicates(["franchise", "season"])
    ts = reg.groupby(["franchise", "season"], as_index=False).agg(
        dropbacks=("dropbacks", "sum"), explosive_pass=("explosive_20_10", "sum"))
    ts["explosive_pass_rate"] = ts["explosive_pass"] / ts["dropbacks"]
    ts = ts.merge(primary[["franchise", "season", "qb_id"]], on=["franchise", "season"], how="left")
    ts = ts.sort_values(["franchise", "season"])
    ts["prev_rate"] = ts.groupby("franchise")["explosive_pass_rate"].shift(1)
    ts["prev_qb"] = ts.groupby("franchise")["qb_id"].shift(1)
    ts["prev_season"] = ts.groupby("franchise")["season"].shift(1)
    ts = ts[(ts["season"] - ts["prev_season"] == 1)].dropna(subset=["prev_rate"])
    ts["qb_same"] = ts["qb_id"] == ts["prev_qb"]
    rows = []
    for same, grp in ts.groupby("qb_same"):
        n = len(grp)
        r = float(np.corrcoef(grp["prev_rate"], grp["explosive_pass_rate"])[0, 1]) if n > 1 else np.nan
        lo, hi = _fisher_ci(r, n)
        rows.append({"qb_continuity": "same_qb" if same else "changed_qb", "n_team_seasons": n,
                      "correlation": r, "ci_lo": lo, "ci_hi": hi})
    return pd.DataFrame(rows)


def qb_career_explosive_leaders(qtg: pd.DataFrame, min_dropbacks: int = 1500, top: int = 20) -> pd.DataFrame:
    reg = qtg.dropna(subset=["qb_id"]).copy()
    career = reg.groupby(["qb_id", "qb_name"], as_index=False).agg(
        dropbacks=("dropbacks", "sum"), explosive_pass=("explosive_20_10", "sum"),
        games=("game_id", "count"), seasons=("season", "nunique"))
    career["rate"] = career["explosive_pass"] / career["dropbacks"]
    return career[career["dropbacks"] >= min_dropbacks].sort_values("rate", ascending=False).head(top).reset_index(drop=True)[
        ["qb_name", "seasons", "games", "dropbacks", "explosive_pass", "rate"]]


def qb_season_explosive_leaders(qtg: pd.DataFrame, min_dropbacks: int = 300, top: int = 15) -> pd.DataFrame:
    reg = qtg.dropna(subset=["qb_id"]).copy()
    season = reg.groupby(["qb_id", "qb_name", "season"], as_index=False).agg(
        dropbacks=("dropbacks", "sum"), explosive_pass=("explosive_20_10", "sum"), games=("game_id", "count"))
    season["rate"] = season["explosive_pass"] / season["dropbacks"]
    return season[season["dropbacks"] >= min_dropbacks].sort_values("rate", ascending=False).head(top).reset_index(drop=True)[
        ["qb_name", "season", "games", "dropbacks", "explosive_pass", "rate"]]


# ===================================================================
# 4/5/6. Play-level analyses (from play-by-play parquet)
# ===================================================================


def era5(season: int) -> str:
    return "2010-2017" if 2010 <= season <= 2017 else "2018-2025"


def era3(season: int) -> str:
    if season <= 2007:
        return "1999-2007"
    if season <= 2016:
        return "2008-2016"
    return "2017-2025"


def _bucket4(n: pd.Series) -> np.ndarray:
    return np.select([n == 1, n == 2, n == 3, n >= 4], ["1", "2", "3", "4+"], default=None)


def _bucket8(n: pd.Series) -> np.ndarray:
    return np.select(
        [n == 1, n == 2, n == 3, n == 4, n == 5, n == 6, n == 7, n >= 8],
        ["1", "2", "3", "4", "5", "6", "7", "8+"], default=None)


def _order_key(pbp: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(pbp["order_sequence"], errors="coerce").fillna(pd.to_numeric(pbp["play_id"], errors="coerce"))


def _drive_play_number(pbp: pd.DataFrame, scrim: pd.Series) -> pd.Series:
    """1-indexed play number within (game_id, posteam, drive), scrimmage
    plays only, ordered by nflverse's order_sequence (falls back to
    play_id)."""
    order = _order_key(pbp)
    tmp = pd.DataFrame({"game_id": pbp["game_id"], "posteam": pbp["posteam"], "drive": pbp["drive"], "order": order})
    tmp = tmp[scrim & pbp["drive"].notna()].sort_values(["game_id", "posteam", "drive", "order"])
    n = tmp.groupby(["game_id", "posteam", "drive"]).cumcount() + 1
    return n.reindex(pbp.index)


def _pbp_seasons() -> list[int]:
    return sorted(int(f.stem.split("_")[-1]) for f in PBP_DIR.glob("play_by_play_*.parquet"))


def _load_season_pbp(season: int, cols: list[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq
    dest = PBP_DIR / f"play_by_play_{season}.parquet"
    available = set(pq.ParquetFile(dest).schema.names)
    use = [c for c in cols if c in available]
    df = pd.read_parquet(dest, columns=use)
    for missing in set(cols) - available:
        df[missing] = pd.NA
    return df


PLAY_COLS = [
    "game_id", "season", "season_type", "game_type", "posteam", "defteam", "play_type", "play",
    "qb_kneel", "qb_spike", "yards_gained", "wp", "drive", "order_sequence", "play_id",
    "qb_dropback", "rush_attempt", "interception", "fumble_lost", "sack", "tackled_for_loss",
    "fixed_drive_result", "fixed_drive",
]


def pass_run_explosives_by_season(seasons: list[int] | None = None) -> pd.DataFrame:
    """Per season: explosive passes per dropback, explosive rushes per
    attempt, share of explosives that are rushes, pass rate."""
    seasons = seasons or _pbp_seasons()
    rows = []
    for season in seasons:
        pbp = _load_season_pbp(season, PLAY_COLS)
        pbp["game_type"] = xm._game_type_series(pbp)
        pbp = pbp[pbp["game_type"] == "REG"].copy()
        if pbp.empty:
            continue
        scrim = xm._scrimmage_mask(pbp)
        pass_play = scrim & (pbp["play_type"] == "pass")
        rush_play = scrim & (pbp["play_type"] == "run")
        dropback = xm._bool(pbp, "qb_dropback") & scrim
        rush_att = xm._bool(pbp, "rush_attempt") & scrim
        exp_pass = scrim & pass_play & (pbp["yards_gained"] >= 20)
        exp_rush = scrim & rush_play & (pbp["yards_gained"] >= 10)
        rows.append({
            "season": season,
            "pass_plays": int(pass_play.sum()), "rush_plays": int(rush_play.sum()),
            "dropbacks": int(dropback.sum()), "rush_attempts": int(rush_att.sum()),
            "explosive_passes": int(exp_pass.sum()), "explosive_rushes": int(exp_rush.sum()),
        })
    out = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    out["pass_rate"] = out["pass_plays"] / (out["pass_plays"] + out["rush_plays"])
    out["explosive_pass_rate_per_dropback"] = out["explosive_passes"] / out["dropbacks"]
    out["explosive_rush_rate_per_attempt"] = out["explosive_rushes"] / out["rush_attempts"]
    total_exp = out["explosive_passes"] + out["explosive_rushes"]
    out["rush_share_of_explosives"] = out["explosive_rushes"] / total_exp
    return out


def pass_run_decomposition(by_season: pd.DataFrame, y0: int = 2018, y1: int = 2025) -> pd.DataFrame:
    """Shift-share decomposition of the change in explosive-plays-per-
    scrimmage-play from y0 to y1: within-type rate effect (passes and
    rushes each getting more/less explosive) vs pass-rate mix effect
    (offenses throwing more or less often), midpoint-weighted."""
    r0 = by_season[by_season["season"] == y0].iloc[0]
    r1 = by_season[by_season["season"] == y1].iloc[0]
    pr0, pr1 = r0["pass_rate"], r1["pass_rate"]
    rp0, rp1 = r0["explosive_pass_rate_per_dropback"], r1["explosive_pass_rate_per_dropback"]
    rr0, rr1 = r0["explosive_rush_rate_per_attempt"], r1["explosive_rush_rate_per_attempt"]
    tot0 = pr0 * rp0 + (1 - pr0) * rr0
    tot1 = pr1 * rp1 + (1 - pr1) * rr1
    pr_bar = (pr0 + pr1) / 2
    rp_bar_minus_rr_bar = ((rp0 - rr0) + (rp1 - rr1)) / 2
    mix_effect = (pr1 - pr0) * rp_bar_minus_rr_bar
    rate_effect = pr_bar * (rp1 - rp0) + (1 - pr_bar) * (rr1 - rr0)
    total_change = tot1 - tot0
    denom = abs(mix_effect) + abs(rate_effect)
    share_rate = abs(rate_effect) / denom if denom else np.nan
    return pd.DataFrame([{
        "from_season": y0, "to_season": y1,
        "total_rate_per_play_from": tot0, "total_rate_per_play_to": tot1, "total_change": total_change,
        "mix_effect_pass_rate": mix_effect, "rate_effect_within_type": rate_effect,
        "sum_check": mix_effect + rate_effect, "share_of_change_that_is_rate_effect": share_rate,
        "pass_rate_from": pr0, "pass_rate_to": pr1,
        "explosive_pass_rate_from": rp0, "explosive_pass_rate_to": rp1,
        "explosive_rush_rate_from": rr0, "explosive_rush_rate_to": rr1,
    }])


def drive_position_explosive_rate(seasons: list[int] | None = None) -> pd.DataFrame:
    """Explosive rate by play number within drive (1, 2, 3, 4+), split
    2010-2017 vs 2018-2025 (garbage-time included, matches exploration)."""
    seasons = seasons or [s for s in _pbp_seasons() if 2010 <= s <= 2025]
    parts = []
    for season in seasons:
        pbp = _load_season_pbp(season, PLAY_COLS)
        pbp["game_type"] = xm._game_type_series(pbp)
        pbp = pbp[pbp["game_type"] == "REG"].copy()
        if pbp.empty:
            continue
        scrim = xm._scrimmage_mask(pbp)
        pass_play = scrim & (pbp["play_type"] == "pass")
        rush_play = scrim & (pbp["play_type"] == "run")
        exp = scrim & (((pass_play) & (pbp["yards_gained"] >= 20)) | ((rush_play) & (pbp["yards_gained"] >= 10)))
        n = _drive_play_number(pbp, scrim)
        bucket = _bucket4(n)
        tmp = pd.DataFrame({"bucket": bucket, "scrim": scrim, "exp": exp})
        tmp = tmp[tmp["scrim"] & tmp["bucket"].notna()]
        g = tmp.groupby("bucket").agg(plays=("exp", "size"), exp_hits=("exp", "sum")).reset_index()
        g["era"] = era5(season)
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    out = out.groupby(["era", "bucket"], dropna=False).agg(plays=("plays", "sum"), exp_hits=("exp_hits", "sum")).reset_index()
    out["explosive_rate"] = out["exp_hits"] / out["plays"]
    order = {"1": 0, "2": 1, "3": 2, "4+": 3}
    out["_o"] = out["bucket"].map(order)
    return out.sort_values(["era", "_o"]).drop(columns="_o").reset_index(drop=True)


def garbage_share_by_season(seasons: list[int] | None = None) -> pd.DataFrame:
    """Share of explosive plays occurring at win probability outside
    [0.05, 0.95] (null wp treated as garbage time), per season."""
    seasons = seasons or _pbp_seasons()
    rows = []
    for season in seasons:
        pbp = _load_season_pbp(season, PLAY_COLS)
        pbp["game_type"] = xm._game_type_series(pbp)
        pbp = pbp[pbp["game_type"] == "REG"].copy()
        if pbp.empty:
            continue
        scrim = xm._scrimmage_mask(pbp)
        pass_play = scrim & (pbp["play_type"] == "pass")
        rush_play = scrim & (pbp["play_type"] == "run")
        exp = scrim & (((pass_play) & (pbp["yards_gained"] >= 20)) | ((rush_play) & (pbp["yards_gained"] >= 10)))
        wp = pd.to_numeric(pbp["wp"], errors="coerce")
        in_wp = wp.between(GARBAGE_WP_LO, GARBAGE_WP_HI).fillna(False)
        garbage = ~in_wp
        total = int(exp.sum())
        in_garbage = int((exp & garbage).sum())
        rows.append({"season": season, "explosive_plays_total": total, "explosive_plays_garbage": in_garbage,
                      "garbage_share_of_explosives": in_garbage / total if total else np.nan})
    return pd.DataFrame(rows).sort_values("season").reset_index(drop=True)


def defensive_play_by_drive_position(seasons: list[int] | None = None) -> pd.DataFrame:
    """Probability a scrimmage play is a defensive play (sack, tackle for
    loss, or turnover -- the same flags xe_metrics.py's _defense_agg uses,
    here at the play level rather than attributed to a team) by play
    number within drive (1..7, 8+), by era, with n per cell."""
    seasons = seasons or _pbp_seasons()
    parts = []
    for season in seasons:
        pbp = _load_season_pbp(season, PLAY_COLS)
        pbp["game_type"] = xm._game_type_series(pbp)
        pbp = pbp[pbp["game_type"] == "REG"].copy()
        if pbp.empty:
            continue
        scrim = xm._scrimmage_mask(pbp)
        interception = xm._bool(pbp, "interception")
        fumble_lost = xm._bool(pbp, "fumble_lost")
        sack = xm._bool(pbp, "sack")
        tfl = xm._bool(pbp, "tackled_for_loss")
        is_def_play = scrim & (sack | tfl | interception | fumble_lost)
        n = _drive_play_number(pbp, scrim)
        bucket = _bucket8(n)
        tmp = pd.DataFrame({"bucket": bucket, "scrim": scrim, "defp": is_def_play})
        tmp = tmp[tmp["scrim"] & tmp["bucket"].notna()]
        g = tmp.groupby("bucket").agg(plays=("defp", "size"), def_hits=("defp", "sum")).reset_index()
        g["era"] = era3(season)
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    out = out.groupby(["era", "bucket"], dropna=False).agg(plays=("plays", "sum"), def_hits=("def_hits", "sum")).reset_index()
    out["def_play_rate"] = out["def_hits"] / out["plays"]
    order = {str(i): i - 1 for i in range(1, 8)}
    order["8+"] = 7
    out["_o"] = out["bucket"].map(order)
    return out.sort_values(["era", "_o"]).drop(columns="_o").reset_index(drop=True)


def drive_outcomes_by_era(seasons: list[int] | None = None) -> pd.DataFrame:
    """Per era: P(at least one defensive play in a drive), points per
    drive (approximate: TD=6.95, FG=3, safety=-2, else 0), plays per
    drive."""
    seasons = seasons or _pbp_seasons()
    rows = []
    for season in seasons:
        pbp = _load_season_pbp(season, PLAY_COLS)
        pbp["game_type"] = xm._game_type_series(pbp)
        pbp = pbp[pbp["game_type"] == "REG"].copy()
        if pbp.empty:
            continue
        scrim = xm._scrimmage_mask(pbp)
        interception = xm._bool(pbp, "interception")
        fumble_lost = xm._bool(pbp, "fumble_lost")
        sack = xm._bool(pbp, "sack")
        tfl = xm._bool(pbp, "tackled_for_loss")
        is_def_play = scrim & (sack | tfl | interception | fumble_lost)
        dd = pbp.dropna(subset=["drive"]).copy()
        dd["_scrim"] = scrim.loc[dd.index]
        dd["_defp"] = is_def_play.loc[dd.index]
        drv = dd.groupby(["game_id", "posteam", "drive"]).agg(
            length=("_scrim", "sum"), any_def=("_defp", "max"), result=("fixed_drive_result", "first"),
        ).reset_index()
        drv = drv[drv["length"] > 0]
        pts_map = {"Touchdown": 6.95, "Field goal": 3.0, "Safety": -2.0}
        drv["points"] = drv["result"].map(pts_map).fillna(0.0)
        rows.append({"season": season, "era": era3(season), "drives": len(drv),
                     "drives_with_def_play": int(drv["any_def"].sum()),
                     "total_points": drv["points"].sum(), "total_plays": int(drv["length"].sum())})
    es = pd.DataFrame(rows)
    out = es.groupby("era").agg(
        drives=("drives", "sum"), drives_with_def_play=("drives_with_def_play", "sum"),
        total_points=("total_points", "sum"), total_plays=("total_plays", "sum"),
    ).reset_index()
    out["p_at_least_one_def_play_per_drive"] = out["drives_with_def_play"] / out["drives"]
    out["points_per_drive"] = out["total_points"] / out["drives"]
    out["plays_per_drive"] = out["total_plays"] / out["drives"]
    order = {"1999-2007": 0, "2008-2016": 1, "2017-2025": 2}
    out["_o"] = out["era"].map(order)
    return out.sort_values("_o").drop(columns="_o").reset_index(drop=True)


# -------------------------------------------------------------- pipeline


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    tg = load_team_game()
    games = load_games()

    tables: dict[str, pd.DataFrame] = {}

    # 1. Competitive time
    tables["competitive_time_logit_by_era"] = competitive_time_logit_by_era(tg)

    # 2. Playoffs
    team_season = regseason_team_season(tg)
    tables["playoff_prediction"] = playoff_prediction(tg, team_season)
    tables["playoff_head_to_head"] = playoff_head_to_head(tg)
    tables["super_bowl_ranks"] = super_bowl_ranks(tg, team_season)

    # 3. QB continuity
    qtg = build_qb_team_game(tg, games)
    tables["qb_continuity_persistence"] = qb_continuity_persistence(qtg)
    tables["qb_career_explosive_leaders"] = qb_career_explosive_leaders(qtg)
    tables["qb_season_explosive_leaders"] = qb_season_explosive_leaders(qtg)

    # 4. Pass/run decomposition
    pr_season = pass_run_explosives_by_season()
    tables["pass_run_explosives_by_season"] = pr_season
    tables["pass_run_decomposition"] = pass_run_decomposition(pr_season)

    # 5. Drive position / garbage
    tables["drive_position_explosive_rate"] = drive_position_explosive_rate()
    tables["garbage_share_by_season"] = garbage_share_by_season()

    # 6. Defensive mechanism
    tables["defensive_play_by_drive_position"] = defensive_play_by_drive_position()
    tables["drive_outcomes_by_era"] = drive_outcomes_by_era()

    for name, table in tables.items():
        table.to_csv(OUT / f"{name}.csv", index=False)
    return tables


if __name__ == "__main__":
    run()
