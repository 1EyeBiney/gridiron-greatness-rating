"""
Explosive Edge exploration: Q5 (QB), Q6 (which explosive plays matter),
Q7 (playoffs / championships). Read-only exploration, re-runnable.
Writes CSVs to studies/explosive-edge/exploration/ next to this file.

Does NOT touch exploration_plays.py / FINDINGS_plays.md (owned by a
concurrent agent). Does NOT modify anything under data/ or src/.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]          # studies/explosive-edge
OUT = REPO / "exploration"
sys.path.insert(0, str(REPO / "src"))
from xe_analysis_shift import fit_logit_irls, zscore_within_season, era_of, ERAS  # noqa: E402

GAMES_CSV = Path(r"C:\nbs\gridiron-greatness-rating\studies\home-field-advantage\data\raw\nflverse\games.csv")
PBP_DIR = REPO / "data" / "raw" / "nflverse_pbp"

t0 = time.time()


def load_team_game() -> pd.DataFrame:
    return pd.read_csv(REPO / "data" / "processed" / "team_game.csv")


def load_games() -> pd.DataFrame:
    g = pd.read_csv(GAMES_CSV, usecols=[
        "game_id", "season", "week", "game_type", "home_team", "away_team",
        "home_qb_id", "away_qb_id", "home_qb_name", "away_qb_name",
    ])
    return g


# ===================================================================
# Q5. Explosive plays and the quarterback
# ===================================================================

def build_qb_team_game(tg: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game (REG only) with the starting QB attached."""
    reg = tg[tg["game_type"] == "REG"].copy()
    # long-format QB per (game_id, team)
    home_qb = games[["game_id", "home_team", "home_qb_id", "home_qb_name"]].rename(
        columns={"home_team": "team", "home_qb_id": "qb_id", "home_qb_name": "qb_name"})
    away_qb = games[["game_id", "away_team", "away_qb_id", "away_qb_name"]].rename(
        columns={"away_team": "team", "away_qb_id": "qb_id", "away_qb_name": "qb_name"})
    qb_long = pd.concat([home_qb, away_qb], ignore_index=True)
    out = reg.merge(qb_long, on=["game_id", "team"], how="left")
    n_missing = out["qb_id"].isna().sum()
    print(f"Q5 setup: {len(out)} REG team-games, {n_missing} missing QB join ({n_missing/len(out):.2%})")
    out["explosive_pass_rate"] = np.where(out["dropbacks"] > 0, out["explosive_20_10"] / out["dropbacks"], np.nan)
    return out


def qb_team_season(qtg: pd.DataFrame) -> pd.DataFrame:
    """Per (qb_id, team, season): games started, dropbacks, explosive pass
    rate per dropback, mean explosive differential per game."""
    g = qtg.dropna(subset=["qb_id"]).groupby(["qb_id", "qb_name", "franchise", "season"], as_index=False).agg(
        games=("game_id", "count"),
        dropbacks=("dropbacks", "sum"),
        explosive_pass=("explosive_20_10", "sum"),
        explosive_diff_mean=("explosive_20_10_diff", "mean"),
        turnovers_diff_mean=("turnovers_diff", "mean"),
        win_rate=("win", "mean"),
    )
    g["explosive_pass_rate"] = g["explosive_pass"] / g["dropbacks"]
    return g


def q5a_qb_moves(qts: pd.DataFrame, min_games: int = 8) -> pd.DataFrame:
    """QBs with >=min_games starts for team A in season s and team B
    (B != A) in season s+1, both seasons >= min_games. For each such move,
    also grab team A's aggregate (all QBs) in season s and season s+1
    (with whoever the new primary starter was)."""
    qts = qts[qts["games"] >= min_games].copy()
    qts = qts.sort_values(["qb_id", "season"])
    rows = []
    by_qb = qts.groupby("qb_id")
    for qb_id, grp in by_qb:
        grp = grp.sort_values("season")
        for i in range(len(grp) - 1):
            r0, r1 = grp.iloc[i], grp.iloc[i + 1]
            if r1["season"] == r0["season"] + 1 and r1["franchise"] != r0["franchise"]:
                rows.append({
                    "qb_id": qb_id, "qb_name": r0["qb_name"],
                    "old_team": r0["franchise"], "new_team": r1["franchise"],
                    "season_s": r0["season"], "season_s1": r1["season"],
                    "old_games": r0["games"], "new_games": r1["games"],
                    "old_explosive_pass_rate": r0["explosive_pass_rate"], "new_explosive_pass_rate": r1["explosive_pass_rate"],
                    "old_explosive_diff": r0["explosive_diff_mean"], "new_explosive_diff": r1["explosive_diff_mean"],
                })
    return pd.DataFrame(rows)


def q5a_old_team_new_qb(qts: pd.DataFrame, moves: pd.DataFrame, min_games: int = 8) -> pd.DataFrame:
    """For each QB move (old_team, season_s -> season_s1), what did
    old_team's explosive rate look like in season_s1 under its NEW primary
    starter (if that starter also qualifies with >=min_games)?"""
    rows = []
    for _, mv in moves.iterrows():
        cand = qts[(qts["franchise"] == mv["old_team"]) & (qts["season"] == mv["season_s1"]) & (qts["games"] >= min_games)]
        if len(cand) == 0:
            continue
        new_starter = cand.sort_values("games", ascending=False).iloc[0]
        if new_starter["qb_id"] == mv["qb_id"]:
            continue  # same QB stayed (shouldn't happen given moves filter, but guard)
        rows.append({
            "qb_id": mv["qb_id"], "old_team": mv["old_team"], "season_s": mv["season_s"], "season_s1": mv["season_s1"],
            "team_explosive_rate_s_old_qb": mv["old_explosive_pass_rate"],
            "team_explosive_rate_s1_new_qb": new_starter["explosive_pass_rate"],
            "team_explosive_diff_s_old_qb": mv["old_explosive_diff"],
            "team_explosive_diff_s1_new_qb": new_starter["explosive_diff_mean"],
            "new_starter_qb_id": new_starter["qb_id"], "new_starter_games": new_starter["games"],
        })
    return pd.DataFrame(rows)


def q5b_persistence_by_qb_continuity(qtg: pd.DataFrame) -> pd.DataFrame:
    """Year-to-year persistence (correlation) of team explosive-pass rate
    per dropback, split by whether the primary starting QB (most starts
    that season) stayed the same team-to-team-season vs changed."""
    reg = qtg.dropna(subset=["qb_id"]).copy()
    # team-season aggregate + primary starter id
    starts = reg.groupby(["franchise", "season", "qb_id"], as_index=False)["game_id"].count().rename(columns={"game_id": "n_starts"})
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
        if len(grp) < 5:
            continue
        r = np.corrcoef(grp["prev_rate"], grp["explosive_pass_rate"])[0, 1]
        rows.append({"qb_continuity": "same_qb" if same else "changed_qb", "n_team_seasons": len(grp), "correlation": r})
    return pd.DataFrame(rows)


def q5c_career_and_season_leaders(qtg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    reg = qtg.dropna(subset=["qb_id"]).copy()
    career = reg.groupby(["qb_id", "qb_name"], as_index=False).agg(
        dropbacks=("dropbacks", "sum"), explosive_pass=("explosive_20_10", "sum"),
        games=("game_id", "count"), seasons=("season", "nunique"))
    career["rate"] = career["explosive_pass"] / career["dropbacks"]
    career_top = career[career["dropbacks"] >= 1500].sort_values("rate", ascending=False).head(15)

    season = reg.groupby(["qb_id", "qb_name", "season"], as_index=False).agg(
        dropbacks=("dropbacks", "sum"), explosive_pass=("explosive_20_10", "sum"), games=("game_id", "count"))
    season["rate"] = season["explosive_pass"] / season["dropbacks"]
    season_top = season[season["dropbacks"] >= 300].sort_values("rate", ascending=False).head(10)
    return career_top, season_top


# ===================================================================
# Q6. Which explosive plays matter
# ===================================================================

def q6_pbp_summaries() -> dict[str, pd.DataFrame]:
    cols = ["game_id", "season", "week", "season_type", "posteam", "defteam", "play_type",
            "yards_gained", "epa", "play", "qb_kneel", "qb_spike", "wp", "score_differential"]
    epa_rows, garbage_rows, margin_rows = [], [], []
    for f in sorted(PBP_DIR.glob("play_by_play_*.parquet")):
        season = int(f.stem.split("_")[-1])
        df = pd.read_parquet(f, columns=cols)
        df = df[df["season_type"] == "REG"].copy()
        play_ok = df["play"].fillna(1).astype(float) != 0
        kneel = df["qb_kneel"].fillna(0).astype(float) != 0
        spike = df["qb_spike"].fillna(0).astype(float) != 0
        scrim = df["play_type"].isin(["pass", "run"]) & play_ok & ~kneel & ~spike
        d = df[scrim].copy()
        pass_play = d["play_type"] == "pass"
        rush_play = d["play_type"] == "run"
        explosive = (pass_play & (d["yards_gained"] >= 20)) | (rush_play & (d["yards_gained"] >= 10))
        d["explosive"] = explosive

        epa_exp = d.loc[d["explosive"], "epa"].mean()
        epa_non = d.loc[~d["explosive"], "epa"].mean()
        epa_rows.append({"season": season, "mean_epa_explosive": epa_exp, "mean_epa_nonexplosive": epa_non,
                          "n_explosive": int(d["explosive"].sum()), "n_nonexplosive": int((~d["explosive"]).sum())})

        garbage = ~d["wp"].between(0.05, 0.95)
        garbage = garbage.fillna(True)  # null wp treated as garbage-time, matches xe_metrics _ng convention
        n_exp = int(d["explosive"].sum())
        n_exp_garbage = int((d["explosive"] & garbage).sum())
        garbage_rows.append({"season": season, "explosive_plays": n_exp, "explosive_in_garbage_time": n_exp_garbage,
                              "share_garbage": n_exp_garbage / n_exp if n_exp else np.nan})

        margin = d["score_differential"].abs()
        bucket = pd.cut(margin, bins=[-0.1, 7, 16, 1000], labels=["within_7", "8_16", "17_plus"])
        n_games = d["game_id"].nunique()
        for b, grp in d.groupby(bucket, observed=True):
            margin_rows.append({"season": season, "margin_bucket": str(b),
                                 "explosive_plays": int(grp["explosive"].sum()),
                                 "n_games_season": n_games,
                                 "explosive_per_game": grp["explosive"].sum() / n_games if n_games else np.nan})
        print(f"  Q6 pbp: season {season} done ({time.time()-t0:.0f}s elapsed)")

    return {
        "epa_by_season": pd.DataFrame(epa_rows),
        "garbage_by_season": pd.DataFrame(garbage_rows),
        "margin_by_season": pd.DataFrame(margin_rows),
    }


def q6_shift_logit_ng_by_era(tg: pd.DataFrame) -> pd.DataFrame:
    """Re-run the core association test using ONLY competitive-time
    explosives (_ng columns) vs turnovers_ng, by era."""
    reg = tg[tg["game_type"] == "REG"]
    home = reg[reg["is_home"]].copy()
    epd_col, tod_col = "explosive_20_10_ng_diff", "turnovers_ng_diff"
    d = home[home["win"].isin([0.0, 1.0])].copy()
    d["era"] = era_of(d["season"])
    rows = []
    for label, lo, hi in ERAS:
        sub = d[(d["season"] >= lo) & (d["season"] <= hi)].copy()
        sub = zscore_within_season(sub, [epd_col, tod_col])
        y = sub["win"].to_numpy(float)
        X = np.column_stack([np.ones(len(sub)), sub[f"z_{epd_col}"].to_numpy(float), sub[f"z_{tod_col}"].to_numpy(float)])
        fit = fit_logit_irls(X, y)
        rows.append({"era": label, "n_games": len(sub), "both_b0": fit["beta"][0],
                     "both_b_epd_ng": fit["beta"][1], "both_se_epd_ng": fit["se"][1],
                     "both_b_tod_ng": fit["beta"][2], "both_se_tod_ng": fit["se"][2],
                     "epd_minus_tod_gap": fit["beta"][1] - abs(fit["beta"][2]),
                     "log_loss": fit["log_loss"], "accuracy": fit["accuracy"]})
    return pd.DataFrame(rows)


# ===================================================================
# Q7. Do explosive teams win in January
# ===================================================================

def q7_regseason_team_season(tg: pd.DataFrame) -> pd.DataFrame:
    reg = tg[tg["game_type"] == "REG"]
    ts = reg.groupby(["franchise", "season"], as_index=False).agg(
        games=("game_id", "count"),
        explosive_diff_pg=("explosive_20_10_diff", "mean"),
        turnover_diff_pg=("turnovers_diff", "mean"),
    )
    return ts


def q7a_playoff_logit_margin(tg: pd.DataFrame, ts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    post = tg[tg["game_type"] == "POST"].copy()
    post = post[post["is_home"]].copy()  # one row per game; POST is_home is nominal (higher seed usually), fine for pairing
    post = post.merge(ts, left_on=["franchise", "season"], right_on=["franchise", "season"], how="left",
                       suffixes=("", "_reg"))
    post = post.rename(columns={"explosive_diff_pg": "home_epd_reg", "turnover_diff_pg": "home_tod_reg", "games": "home_reg_games"})
    post = post.merge(ts, left_on=["opp_franchise", "season"], right_on=["franchise", "season"], how="left",
                       suffixes=("", "_opp"))
    post = post.rename(columns={"explosive_diff_pg": "away_epd_reg", "turnover_diff_pg": "away_tod_reg", "games": "away_reg_games"})
    post["d_epd"] = post["home_epd_reg"] - post["away_epd_reg"]
    post["d_tod"] = post["home_tod_reg"] - post["away_tod_reg"]
    post = post.dropna(subset=["d_epd", "d_tod"])
    post = post[post["win"].isin([0.0, 1.0])].copy()

    def zscore(col):
        return (post[col] - post[col].mean()) / post[col].std(ddof=0)
    post["z_d_epd"] = zscore("d_epd")
    post["z_d_tod"] = zscore("d_tod")

    logit_rows = []
    margin_rows = []
    groups = [("ALL", 1999, 2025)] + ERAS
    for label, lo, hi in groups:
        sub = post[(post["season"] >= lo) & (post["season"] <= hi)]
        if len(sub) < 20:
            continue
        y = sub["win"].to_numpy(float)
        X = np.column_stack([np.ones(len(sub)), sub["z_d_epd"].to_numpy(float), sub["z_d_tod"].to_numpy(float)])
        fit = fit_logit_irls(X, y)
        logit_rows.append({"era": label, "n_games": len(sub), "b0": fit["beta"][0],
                            "b_epd": fit["beta"][1], "se_epd": fit["se"][1],
                            "b_tod": fit["beta"][2], "se_tod": fit["se"][2],
                            "log_loss": fit["log_loss"], "accuracy": fit["accuracy"]})
        # margin OLS (raw units, not standardized, for interpretability + standardized betas)
        from xe_analysis_shift import fit_ols
        Xo = np.column_stack([np.ones(len(sub)), sub["z_d_epd"].to_numpy(float), sub["z_d_tod"].to_numpy(float)])
        yo = sub["margin"].to_numpy(float)
        fo = fit_ols(Xo, yo)
        margin_rows.append({"era": label, "n_games": len(sub), "b0": fo["beta"][0],
                             "b_epd": fo["beta"][1], "se_epd": fo["se"][1],
                             "b_tod": fo["beta"][2], "se_tod": fo["se"][2], "r2": fo["r2"]})
    return pd.DataFrame(logit_rows), pd.DataFrame(margin_rows)


def q7b_head_to_head_postseason(tg: pd.DataFrame) -> pd.DataFrame:
    """Mirrors src/xe_analysis_teams.py::_classify_head_to_head exactly
    (one row per game_id from the home-team perspective; turnover sign is
    FLIPPED since turnovers_diff is team-minus-opponent giveaways, so
    negative = won the turnover battle), restricted to POST games."""
    post = tg[tg["game_type"] == "POST"]
    home = post[post["is_home"]].drop_duplicates(subset="game_id").set_index("game_id")
    exp_sign = np.sign(home["explosive_20_10_diff"])
    tov_sign = np.sign(-home["turnovers_diff"])  # positive => home team WON the turnover battle
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


def q7c_super_bowl_ranks(tg: pd.DataFrame, ts: pd.DataFrame) -> pd.DataFrame:
    post = tg[tg["game_type"] == "POST"].copy()
    # Super Bowl = the postseason game with the highest week number that season, winner side.
    sb_week = post.groupby("season")["week"].max().rename("sb_week")
    post = post.merge(sb_week, on="season")
    sb = post[post["week"] == post["sb_week"]]
    sb_winner = sb[sb["win"] == 1.0][["season", "franchise", "opponent"]].drop_duplicates("season")

    ts = ts.copy()
    # Rank 1 = best team on that metric. explosive_diff_pg: higher (more
    # explosive than opponent) is better, so rank descending. turnover_diff_pg
    # is team's turnovers MINUS opponent's, so LOWER (more negative, i.e.
    # fewer giveaways than takeaways) is better -> rank ascending.
    ts["epd_rank"] = ts.groupby("season")["explosive_diff_pg"].rank(ascending=False, method="min")
    ts["tod_rank"] = ts.groupby("season")["turnover_diff_pg"].rank(ascending=True, method="min")

    rows = []
    for _, r in sb_winner.iterrows():
        m = ts[(ts["season"] == r["season"]) & (ts["franchise"] == r["franchise"])]
        if len(m) == 0:
            continue
        m = m.iloc[0]
        rows.append({"season": r["season"], "champion": r["franchise"],
                      "n_teams": ts[ts["season"] == r["season"]].shape[0],
                      "explosive_diff_pg": m["explosive_diff_pg"], "epd_rank": m["epd_rank"],
                      "turnover_diff_pg": m["turnover_diff_pg"], "tod_rank": m["tod_rank"]})
    return pd.DataFrame(rows)


# ===================================================================


def main():
    OUT.mkdir(exist_ok=True)
    tg = load_team_game()
    games = load_games()

    print("== Q5 ==")
    qtg = build_qb_team_game(tg, games)
    qts = qb_team_season(qtg)
    moves = q5a_qb_moves(qts)
    moves.to_csv(OUT / "q5a_qb_moves.csv", index=False)
    old_team_new_qb = q5a_old_team_new_qb(qts, moves)
    old_team_new_qb.to_csv(OUT / "q5a_old_team_new_qb.csv", index=False)
    persistence_split = q5b_persistence_by_qb_continuity(qtg)
    persistence_split.to_csv(OUT / "q5b_persistence_by_qb_continuity.csv", index=False)
    career_top, season_top = q5c_career_and_season_leaders(qtg)
    career_top.to_csv(OUT / "q5c_career_leaders.csv", index=False)
    season_top.to_csv(OUT / "q5c_season_leaders.csv", index=False)
    print(f"Q5 done ({time.time()-t0:.0f}s elapsed)")

    print("== Q6 ==")
    pbp_out = q6_pbp_summaries()
    pbp_out["epa_by_season"].to_csv(OUT / "q6_epa_by_season.csv", index=False)
    pbp_out["garbage_by_season"].to_csv(OUT / "q6_garbage_share_by_season.csv", index=False)
    pbp_out["margin_by_season"].to_csv(OUT / "q6_explosive_by_margin_bucket.csv", index=False)
    shift_ng = q6_shift_logit_ng_by_era(tg)
    shift_ng.to_csv(OUT / "q6_shift_logit_ng_by_era.csv", index=False)
    print(f"Q6 done ({time.time()-t0:.0f}s elapsed)")

    print("== Q7 ==")
    ts = q7_regseason_team_season(tg)
    logit_df, margin_df = q7a_playoff_logit_margin(tg, ts)
    logit_df.to_csv(OUT / "q7a_playoff_logit.csv", index=False)
    margin_df.to_csv(OUT / "q7a_playoff_margin_ols.csv", index=False)
    hth_post = q7b_head_to_head_postseason(tg)
    hth_post.to_csv(OUT / "q7b_head_to_head_postseason.csv", index=False)
    sb_ranks = q7c_super_bowl_ranks(tg, ts)
    sb_ranks.to_csv(OUT / "q7c_super_bowl_ranks.csv", index=False)
    print(f"Q7 done ({time.time()-t0:.0f}s elapsed)")

    print(f"TOTAL runtime: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
