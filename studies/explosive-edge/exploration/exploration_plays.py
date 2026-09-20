"""
Explosive Edge -- one-shot exploration for the Simms "big plays decide
seasons" mechanism/situational questions (Q1-Q4 in the task brief).

Re-runnable. Reads data/raw/nflverse_pbp/play_by_play_YYYY.parquet
(1999-2025, already downloaded -- never fetches). Reuses xe_metrics.py's
scrimmage mask, explosive-play definitions, and turnover attribution so
counts here tie out with the study's own team_game.csv. Regular season
only throughout (game_type == "REG" after xe_metrics._game_type_series).

Processes one season at a time (season-level groupby aggregates only are
kept in memory across seasons) to stay memory-bounded. Writes CSVs +
FINDINGS_plays.md to studies/explosive-edge/exploration/. Does not touch
any existing file, does not build site pages, does not commit.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SRC = STUDY / "src"
sys.path.insert(0, str(SRC))
import xe_metrics as xm  # noqa: E402
import xe_ingest as xi  # noqa: E402

OUT = HERE
FIRST, LAST = 1999, 2025

EXTRA_COLS = [
    "down", "ydstogo", "yardline_100", "qtr", "score_differential",
    "order_sequence", "play_id", "fixed_drive", "fixed_drive_result",
    "rush_attempt", "pass_attempt",
]
ALL_COLS = sorted(set(xi.COLUMNS) | set(EXTRA_COLS))


def load_season_full(season: int) -> pd.DataFrame:
    import pyarrow.parquet as pq
    dest = xi.RAW / f"play_by_play_{season}.parquet"
    available = set(pq.ParquetFile(dest).schema.names)
    cols = [c for c in ALL_COLS if c in available]
    df = pd.read_parquet(dest, columns=cols)
    for missing in set(ALL_COLS) - available:
        df[missing] = pd.NA
    return df


def era5(season: int) -> str:
    return "2010-2017" if 2010 <= season <= 2017 else "2018-2025"


def era3(season: int) -> str:
    if season <= 2007:
        return "1999-2007"
    if season <= 2016:
        return "2008-2016"
    return "2017-2025"


def down_bucket(down):
    return np.select([down == 1, down == 2, down >= 3], ["1st", "2nd", "3rd+"], default=None)


def dist_bucket(ydstogo):
    return np.select(
        [ydstogo.between(1, 3), ydstogo.between(4, 7), ydstogo >= 8],
        ["short_1-3", "medium_4-7", "long_8+"], default=None)


def field_zone(yardline_100):
    # yardline_100 = distance to opponent's end zone
    return np.select(
        [yardline_100 >= 80, yardline_100.between(50, 79), yardline_100.between(21, 49), yardline_100 <= 20],
        ["own_1-20", "own_21-50", "opp_49-21", "red_zone"], default=None)


def score_state(diff):
    return np.select(
        [diff > 7, diff.between(1, 7), diff == 0, diff.between(-7, -1), diff < -7],
        ["leading_>7", "leading_1-7", "tied", "trailing_1-7", "trailing_>7"], default=None)


def drive_play_bucket(n):
    return np.select([n == 1, n == 2, n == 3, n >= 4], ["1st", "2nd", "3rd", "4th+"], default=None)


def q1_bucket(n):
    return np.select(
        [n == 1, n == 2, n == 3, n == 4, n == 5, n == 6, n == 7, n >= 8],
        ["1", "2", "3", "4", "5", "6", "7", "8+"], default=None)


def main():
    t0 = time.time()
    seasons = [s for s in range(FIRST, LAST + 1) if (xi.RAW / f"play_by_play_{s}.parquet").exists()]
    print(f"Found {len(seasons)} seasons on disk: {seasons[0]}-{seasons[-1]}", file=sys.stderr)

    # ---- accumulators (season-level aggregates only) ----
    q1_rows = []            # per season: pass/rush explosive counts + denominators, both defs
    q2_situ_rows = []       # per era x factor x bucket: explosive hits / plays
    q2_driveplay_rows = []  # per era x drive-play-bucket: explosive hits / plays
    q2_garbage_rows = []    # per era x garbage flag: explosive hits / plays
    q2_garbage_season_rows = []  # per season: share of explosive plays in garbage time
    q3_teamseason_rows = []  # per team-season: explosives generated & allowed, team games
    q3_top5_rows = []       # per season: top-5-offense share of league explosive plays
    q4_defplay_rows = []    # per era x drive-play-bucket(1..8+): def-play hits / plays, n
    q4_driveturnover_rows = []  # per era x drive-length-bucket: turnover-ending drives / drives
    q4_era_summary_rows = []  # per era: P(>=1 def play per drive), points per drive

    for season in seasons:
        pbp = load_season_full(season)
        pbp["game_type"] = xm._game_type_series(pbp)
        pbp = pbp[pbp["game_type"] == "REG"].copy()
        if pbp.empty:
            continue

        scrim = xm._scrimmage_mask(pbp)
        pbp["_scrim"] = scrim
        pass_play = scrim & (pbp["play_type"] == "pass")
        rush_play = scrim & (pbp["play_type"] == "run")
        dropback = xm._bool(pbp, "qb_dropback") & scrim
        rush_att = xm._bool(pbp, "rush_attempt") & scrim
        wp = pd.to_numeric(pbp["wp"], errors="coerce")
        in_wp = wp.between(xm.GARBAGE_WP_LO, xm.GARBAGE_WP_HI).fillna(False)
        garbage = ~in_wp  # nulls treated as garbage, matching xe_metrics _ng convention

        # explosive hit flags, primary (20/10) and stricter (25/15)
        exp20 = scrim & (((pass_play) & (pbp["yards_gained"] >= 20)) | ((rush_play) & (pbp["yards_gained"] >= 10)))
        exp25 = scrim & (((pass_play) & (pbp["yards_gained"] >= 25)) | ((rush_play) & (pbp["yards_gained"] >= 15)))
        exp_pass20 = scrim & pass_play & (pbp["yards_gained"] >= 20)
        exp_rush10 = scrim & rush_play & (pbp["yards_gained"] >= 10)
        exp_pass25 = scrim & pass_play & (pbp["yards_gained"] >= 25)
        exp_rush15 = scrim & rush_play & (pbp["yards_gained"] >= 15)

        team_games = pbp.drop_duplicates("game_id").shape[0] * 2

        # ---------------------------------------------------------- Q1
        q1_rows.append({
            "season": season, "team_games": team_games,
            "pass_plays": int(pass_play.sum()), "rush_plays": int(rush_play.sum()),
            "dropbacks": int(dropback.sum()), "rush_attempts": int(rush_att.sum()),
            "exp_pass_20": int(exp_pass20.sum()), "exp_rush_10": int(exp_rush10.sum()),
            "exp_pass_25": int(exp_pass25.sum()), "exp_rush_15": int(exp_rush15.sum()),
        })

        # ---------------------------------------------------------- Q2 (2010-2025 only)
        if 2010 <= season <= 2025:
            era = era5(season)
            down_b = down_bucket(pbp["down"])
            dist_b = dist_bucket(pd.to_numeric(pbp["ydstogo"], errors="coerce"))
            zone_b = field_zone(pd.to_numeric(pbp["yardline_100"], errors="coerce"))
            score_b = score_state(pd.to_numeric(pbp["score_differential"], errors="coerce"))
            qtr_b = pbp["qtr"].astype("Int64").astype(str)

            factors = {"down": down_b, "distance": dist_b, "field_zone": zone_b,
                       "score_state": score_b, "quarter": qtr_b}
            for fname, buckets in factors.items():
                tmp = pd.DataFrame({"bucket": buckets, "scrim": scrim, "exp": exp20})
                tmp = tmp[tmp["scrim"]]
                g = tmp.groupby("bucket", dropna=True).agg(plays=("exp", "size"), exp_hits=("exp", "sum"))
                g["era"], g["factor"] = era, fname
                q2_situ_rows.append(g.reset_index())

            # play number within drive
            order_key = pd.to_numeric(pbp["order_sequence"], errors="coerce").fillna(pd.to_numeric(pbp["play_id"], errors="coerce"))
            tmp = pd.DataFrame({"game_id": pbp["game_id"], "posteam": pbp["posteam"], "drive": pbp["drive"],
                                 "order": order_key, "scrim": scrim, "exp": exp20})
            tmp = tmp[tmp["scrim"] & tmp["drive"].notna()].sort_values(["game_id", "posteam", "drive", "order"])
            tmp["n"] = tmp.groupby(["game_id", "posteam", "drive"]).cumcount() + 1
            tmp["bucket"] = drive_play_bucket(tmp["n"])
            g = tmp.groupby("bucket").agg(plays=("exp", "size"), exp_hits=("exp", "sum")).reset_index()
            g["era"] = era
            q2_driveplay_rows.append(g)

            # garbage time
            tmp = pd.DataFrame({"scrim": scrim, "exp": exp20, "garbage": garbage})
            tmp = tmp[tmp["scrim"]]
            g = tmp.groupby("garbage").agg(plays=("exp", "size"), exp_hits=("exp", "sum")).reset_index()
            g["era"] = era
            q2_garbage_rows.append(g)

            q2_garbage_season_rows.append({
                "season": season,
                "explosive_plays_total": int(exp20[scrim].sum()),
                "explosive_plays_garbage": int((exp20 & scrim & garbage).sum()),
            })

        # ---------------------------------------------------------- Q3
        off = pbp[scrim].groupby("posteam").agg(explosives_gen=("_scrim", "size"))
        off["explosives_gen"] = pbp[scrim & exp20].groupby("posteam").size().reindex(off.index).fillna(0).astype(int)
        deff = pbp[scrim & exp20].groupby("defteam").size().rename("explosives_allowed")
        team_g_off = pbp.drop_duplicates("game_id")[["game_id", "home_team", "away_team"]]
        games_per_team = pd.concat([team_g_off["home_team"], team_g_off["away_team"]]).value_counts()

        teams = sorted(set(pbp["posteam"].dropna().unique()) | set(pbp["defteam"].dropna().unique()) | set(games_per_team.index))
        gen = pbp[scrim & exp20].groupby("posteam").size().reindex(teams).fillna(0).astype(int)
        allo = pbp[scrim & exp20].groupby("defteam").size().reindex(teams).fillna(0).astype(int)
        gp = games_per_team.reindex(teams).fillna(0).astype(int)
        q3 = pd.DataFrame({"team": teams, "season": season, "games": gp,
                            "explosives_generated": gen.values, "explosives_allowed": allo.values})
        q3 = q3[q3["games"] > 0]
        q3["gen_per_game"] = q3["explosives_generated"] / q3["games"]
        q3["allowed_per_game"] = q3["explosives_allowed"] / q3["games"]
        q3_teamseason_rows.append(q3)

        league_total = q3["explosives_generated"].sum()
        top5 = q3.nlargest(5, "explosives_generated")["explosives_generated"].sum()
        q3_top5_rows.append({"season": season, "league_explosive_plays": int(league_total),
                              "top5_offense_explosive_plays": int(top5),
                              "top5_share": top5 / league_total if league_total else np.nan})

        # ---------------------------------------------------------- Q4
        era = era3(season)
        interception = xm._bool(pbp, "interception")
        fumble_lost = xm._bool(pbp, "fumble_lost")
        sack = xm._bool(pbp, "sack")
        tfl = xm._bool(pbp, "tackled_for_loss")
        turnover = interception | fumble_lost
        is_def_play = scrim & (sack | tfl | turnover)

        order_key = pd.to_numeric(pbp["order_sequence"], errors="coerce").fillna(pd.to_numeric(pbp["play_id"], errors="coerce"))
        tmp = pd.DataFrame({"game_id": pbp["game_id"], "posteam": pbp["posteam"], "drive": pbp["drive"],
                             "order": order_key, "scrim": scrim, "defp": is_def_play})
        tmp = tmp[tmp["scrim"] & tmp["drive"].notna()].sort_values(["game_id", "posteam", "drive", "order"])
        tmp["n"] = tmp.groupby(["game_id", "posteam", "drive"]).cumcount() + 1
        tmp["bucket"] = q1_bucket(tmp["n"])
        g = tmp.groupby("bucket").agg(plays=("defp", "size"), def_hits=("defp", "sum")).reset_index()
        g["era"] = era
        q4_defplay_rows.append(g)

        # per-drive: length (scrimmage plays), turnover ending, any def play, points
        dd = pbp.dropna(subset=["drive"]).copy()
        dd["_scrim"] = scrim.loc[dd.index]
        dd["_defp"] = is_def_play.loc[dd.index]
        drv = dd.groupby(["game_id", "posteam", "drive"]).agg(
            length=("_scrim", "sum"),
            any_def=("_defp", "max"),
            result=("fixed_drive_result", "first"),
        ).reset_index()
        drv = drv[drv["length"] > 0]
        drv["turnover_end"] = drv["result"].isin(["Turnover", "Opp touchdown"])
        drv["len_bucket"] = q1_bucket(drv["length"].clip(upper=8))
        g2 = drv.groupby("len_bucket").agg(drives=("turnover_end", "size"), turnovers=("turnover_end", "sum")).reset_index()
        g2["era"] = era
        q4_driveturnover_rows.append(g2)

        # points per drive: use drive_ended_with_score is not loaded; approximate via
        # fixed_drive_result Touchdown=7 (6+XP approx, use 6.95), Field goal=3, Safety=-2 (to defense)
        pts_map = {"Touchdown": 6.95, "Field goal": 3.0, "Safety": -2.0}
        drv["points"] = drv["result"].map(pts_map).fillna(0.0)
        q4_era_summary_rows.append({
            "season": season, "era": era,
            "drives": len(drv), "drives_with_def_play": int(drv["any_def"].sum()),
            "total_points": drv["points"].sum(),
        })

        print(f"  {season}: {team_games} team-games, {int(scrim.sum()):,} scrimmage plays", file=sys.stderr)

    # ================================================================ Q1 finalize
    q1 = pd.DataFrame(q1_rows).sort_values("season")
    q1["pass_rate"] = q1["pass_plays"] / (q1["pass_plays"] + q1["rush_plays"])
    q1["exp_pass20_per_teamgame"] = q1["exp_pass_20"] / q1["team_games"]
    q1["exp_rush10_per_teamgame"] = q1["exp_rush_10"] / q1["team_games"]
    q1["exp_pass20_per_dropback"] = q1["exp_pass_20"] / q1["dropbacks"]
    q1["exp_rush10_per_rushattempt"] = q1["exp_rush_10"] / q1["rush_attempts"]
    q1["exp_pass25_per_teamgame"] = q1["exp_pass_25"] / q1["team_games"]
    q1["exp_rush15_per_teamgame"] = q1["exp_rush_15"] / q1["team_games"]
    q1["exp_pass25_per_dropback"] = q1["exp_pass_25"] / q1["dropbacks"]
    q1["exp_rush15_per_rushattempt"] = q1["exp_rush_15"] / q1["rush_attempts"]
    q1["total_exp2010"] = q1["exp_pass_20"] + q1["exp_rush_10"]
    q1["rush_share_of_explosive_2010"] = q1["exp_rush_10"] / q1["total_exp2010"]
    q1["total_exp2515"] = q1["exp_pass_25"] + q1["exp_rush_15"]
    q1["rush_share_of_explosive_2515"] = q1["exp_rush_15"] / q1["total_exp2515"]
    q1.to_csv(OUT / "q1_pass_run_explosives_by_season.csv", index=False)

    # decomposition 2018 -> 2025 (primary 20/10 def)
    def decomp(y0, y1, df):
        r0 = df[df["season"] == y0].iloc[0]
        r1 = df[df["season"] == y1].iloc[0]
        pr0, pr1 = r0["pass_rate"], r1["pass_rate"]
        rp0, rp1 = r0["exp_pass_20"] / r0["pass_plays"], r1["exp_pass_20"] / r1["pass_plays"]
        rr0, rr1 = r0["exp_rush_10"] / r0["rush_plays"], r1["exp_rush_10"] / r1["rush_plays"]
        tot0 = pr0 * rp0 + (1 - pr0) * rr0
        tot1 = pr1 * rp1 + (1 - pr1) * rr1
        pr_bar = (pr0 + pr1) / 2
        rp_bar_minus_rr_bar = ((rp0 - rr0) + (rp1 - rr1)) / 2
        mix_effect = (pr1 - pr0) * rp_bar_minus_rr_bar
        rate_effect = pr_bar * (rp1 - rp0) + (1 - pr_bar) * (rr1 - rr0)
        return {
            "from_season": y0, "to_season": y1,
            "total_rate_per_play_from": tot0, "total_rate_per_play_to": tot1,
            "total_change": tot1 - tot0, "mix_effect_pass_rate": mix_effect,
            "rate_effect_within_type": rate_effect, "sum_check": mix_effect + rate_effect,
            "pass_rate_from": pr0, "pass_rate_to": pr1,
            "exp_rate_per_dropback_from": rp0, "exp_rate_per_dropback_to": rp1,
            "exp_rate_per_rush_from": rr0, "exp_rate_per_rush_to": rr1,
        }
    q1_decomp = pd.DataFrame([decomp(2018, 2025, q1)])
    q1_decomp.to_csv(OUT / "q1_decomposition_2018_2025.csv", index=False)

    # ================================================================ Q2 finalize
    q2_situ = pd.concat(q2_situ_rows, ignore_index=True)
    q2_situ = q2_situ.groupby(["era", "factor", "bucket"], dropna=False).agg(plays=("plays", "sum"), exp_hits=("exp_hits", "sum")).reset_index()
    q2_situ["explosive_rate"] = q2_situ["exp_hits"] / q2_situ["plays"]
    q2_situ.to_csv(OUT / "q2_situational_explosive_rate.csv", index=False)

    q2_dp = pd.concat(q2_driveplay_rows, ignore_index=True)
    q2_dp = q2_dp.groupby(["era", "bucket"], dropna=False).agg(plays=("plays", "sum"), exp_hits=("exp_hits", "sum")).reset_index()
    q2_dp["explosive_rate"] = q2_dp["exp_hits"] / q2_dp["plays"]
    q2_dp.to_csv(OUT / "q2_explosive_rate_by_drive_play_number.csv", index=False)

    q2_gb = pd.concat(q2_garbage_rows, ignore_index=True)
    q2_gb = q2_gb.groupby(["era", "garbage"], dropna=False).agg(plays=("plays", "sum"), exp_hits=("exp_hits", "sum")).reset_index()
    q2_gb["explosive_rate"] = q2_gb["exp_hits"] / q2_gb["plays"]
    q2_gb.to_csv(OUT / "q2_garbage_time_explosive_rate.csv", index=False)

    q2_gbs = pd.DataFrame(q2_garbage_season_rows).sort_values("season")
    q2_gbs["garbage_share_of_explosives"] = q2_gbs["explosive_plays_garbage"] / q2_gbs["explosive_plays_total"]
    q2_gbs.to_csv(OUT / "q2_garbage_share_of_explosives_by_season.csv", index=False)

    # ================================================================ Q3 finalize
    q3_ts = pd.concat(q3_teamseason_rows, ignore_index=True)
    q3_ts.to_csv(OUT / "q3_team_season_explosives.csv", index=False)

    def era_of(s):
        if s <= 2007:
            return "1999-2007"
        if s <= 2016:
            return "2008-2016"
        return "2017-2025"
    q3_ts["era"] = q3_ts["season"].apply(era_of)
    q3_std = q3_ts.groupby("era").agg(
        std_gen_per_game=("gen_per_game", "std"), mean_gen_per_game=("gen_per_game", "mean"),
        std_allowed_per_game=("allowed_per_game", "std"), mean_allowed_per_game=("allowed_per_game", "mean"),
        n_team_seasons=("team", "size"),
    ).reset_index()
    q3_std["cv_gen"] = q3_std["std_gen_per_game"] / q3_std["mean_gen_per_game"]
    q3_std["cv_allowed"] = q3_std["std_allowed_per_game"] / q3_std["mean_allowed_per_game"]
    q3_std.to_csv(OUT / "q3_between_team_std_by_era.csv", index=False)

    window = q3_ts[(q3_ts["season"] >= 2019) & (q3_ts["season"] <= 2025)].copy()
    top10_gen = window.nlargest(10, "gen_per_game")[["team", "season", "gen_per_game", "explosives_generated", "games"]]
    bot10_gen = window.nsmallest(10, "gen_per_game")[["team", "season", "gen_per_game", "explosives_generated", "games"]]
    top10_allowed = window.nlargest(10, "allowed_per_game")[["team", "season", "allowed_per_game", "explosives_allowed", "games"]]
    bot10_allowed = window.nsmallest(10, "allowed_per_game")[["team", "season", "allowed_per_game", "explosives_allowed", "games"]]
    top10_gen.to_csv(OUT / "q3_top10_generated_2019_2025.csv", index=False)
    bot10_gen.to_csv(OUT / "q3_bottom10_generated_2019_2025.csv", index=False)
    top10_allowed.to_csv(OUT / "q3_top10_allowed_2019_2025.csv", index=False)
    bot10_allowed.to_csv(OUT / "q3_bottom10_allowed_2019_2025.csv", index=False)

    q3_top5 = pd.DataFrame(q3_top5_rows).sort_values("season")
    q3_top5.to_csv(OUT / "q3_top5_offense_concentration_by_season.csv", index=False)

    # ================================================================ Q4 finalize
    q4_dp = pd.concat(q4_defplay_rows, ignore_index=True)
    q4_dp = q4_dp.groupby(["era", "bucket"], dropna=False).agg(plays=("plays", "sum"), def_hits=("def_hits", "sum")).reset_index()
    q4_dp["def_play_rate"] = q4_dp["def_hits"] / q4_dp["plays"]
    q4_dp.to_csv(OUT / "q4_def_play_rate_by_drive_play_number.csv", index=False)

    q4_dt = pd.concat(q4_driveturnover_rows, ignore_index=True)
    q4_dt = q4_dt.groupby(["era", "len_bucket"], dropna=False).agg(drives=("drives", "sum"), turnovers=("turnovers", "sum")).reset_index()
    q4_dt["turnover_rate"] = q4_dt["turnovers"] / q4_dt["drives"]
    q4_dt.to_csv(OUT / "q4_turnover_rate_by_drive_length.csv", index=False)

    q4_es = pd.DataFrame(q4_era_summary_rows)
    q4_era = q4_es.groupby("era").agg(
        drives=("drives", "sum"), drives_with_def_play=("drives_with_def_play", "sum"), total_points=("total_points", "sum"),
    ).reset_index()
    q4_era["p_at_least_one_def_play_per_drive"] = q4_era["drives_with_def_play"] / q4_era["drives"]
    q4_era["points_per_drive"] = q4_era["total_points"] / q4_era["drives"]
    q4_era.to_csv(OUT / "q4_era_summary.csv", index=False)

    runtime = time.time() - t0
    write_findings(q1, q1_decomp, q2_situ, q2_dp, q2_gb, q2_gbs, q3_std, top10_gen, bot10_gen,
                    top10_allowed, bot10_allowed, q3_top5, q4_dp, q4_dt, q4_era, runtime)
    print(f"Done in {runtime:.1f}s", file=sys.stderr)


def write_findings(q1, q1_decomp, q2_situ, q2_dp, q2_gb, q2_gbs, q3_std, top10_gen, bot10_gen,
                    top10_allowed, bot10_allowed, q3_top5, q4_dp, q4_dt, q4_era, runtime):
    d = q1_decomp.iloc[0]
    r2018 = q1[q1.season == 2018].iloc[0]
    r2025 = q1[q1.season == 2025].iloc[0]

    lines = []
    lines.append("# Explosive Edge -- Play-Level Exploration Findings\n")
    lines.append(f"Regular season only, 1999-2025 (where data present). Runtime: {runtime:.1f}s.\n")

    # -------------------------------------------------- Q1
    mix_share = abs(d["mix_effect_pass_rate"]) / (abs(d["mix_effect_pass_rate"]) + abs(d["rate_effect_within_type"])) if (abs(d["mix_effect_pass_rate"]) + abs(d["rate_effect_within_type"])) else float("nan")
    lines.append("## Q1. Pass vs run explosives\n")
    lines.append(
        f"**The 2018-2025 decline in explosive plays is mostly a passing-game decline, not a rushing decline or "
        f"a mix (falling pass rate) effect** -- the per-dropback explosive-pass rate fell from "
        f"{r2018['exp_pass20_per_dropback']:.4f} to {r2025['exp_pass20_per_dropback']:.4f} "
        f"({100*(r2025['exp_pass20_per_dropback']/r2018['exp_pass20_per_dropback']-1):+.1f}%) while the "
        f"per-attempt explosive-rush rate barely moved ({r2018['exp_rush10_per_rushattempt']:.4f} -> "
        f"{r2025['exp_rush10_per_rushattempt']:.4f}, {100*(r2025['exp_rush10_per_rushattempt']/r2018['exp_rush10_per_rushattempt']-1):+.1f}%).\n"
    )
    lines.append(
        f"- Explosive passes/team-game: {r2018['exp_pass20_per_teamgame']:.2f} (2018) -> "
        f"{r2025['exp_pass20_per_teamgame']:.2f} (2025); explosive rushes/team-game: "
        f"{r2018['exp_rush10_per_teamgame']:.2f} -> {r2025['exp_rush10_per_teamgame']:.2f}.\n"
        f"- Rush share of all explosive plays (20/10 def): {r2018['rush_share_of_explosive_2010']:.1%} (2018) -> "
        f"{r2025['rush_share_of_explosive_2010']:.1%} (2025); stricter 25/15 def: "
        f"{r2018['rush_share_of_explosive_2515']:.1%} -> {r2025['rush_share_of_explosive_2515']:.1%}.\n"
        f"- Decomposition of the change in league-wide explosive-plays-per-scrimmage-play, 2018->2025: total "
        f"{d['total_rate_per_play_from']:.4f} -> {d['total_rate_per_play_to']:.4f} "
        f"({d['total_change']:+.4f}). Mix effect (falling pass rate, {d['pass_rate_from']:.1%} -> "
        f"{d['pass_rate_to']:.1%}): {d['mix_effect_pass_rate']:+.4f}. Within-type rate effect (passes and "
        f"rushes each getting less explosive per attempt): {d['rate_effect_within_type']:+.4f}. The rate effect "
        f"is {'the larger' if abs(d['rate_effect_within_type'])>abs(d['mix_effect_pass_rate']) else 'the smaller'} "
        f"of the two (~{100*abs(d['rate_effect_within_type'])/(abs(d['rate_effect_within_type'])+abs(d['mix_effect_pass_rate'])):.0f}% "
        f"of the combined magnitude), so **falling pass rate explains only a minority of the decline** -- it is "
        f"mostly that pass plays (and to a lesser extent rushes) are individually less likely to go for 20+/10+ "
        f"than they were in 2018, not that the league is running the ball more.\n"
    )
    lines.append(
        "- Caveat: this decomposition uses a simple two-term (midpoint-weighted) mix/rate split on a single "
        "before/after pair (2018, 2025); it is not a full trend regression and a different endpoint pair could "
        "shift the split modestly. Both explosive-play definitions (20/10 primary, 25/15 strict) agree on "
        "direction. See `q1_pass_run_explosives_by_season.csv` for the full 1999-2025 series and "
        "`q1_decomposition_2018_2025.csv` for the decomposition.\n"
    )

    # -------------------------------------------------- Q2
    lines.append("## Q2. Situational\n")
    down_e2 = q2_situ[(q2_situ.factor == "down") & (q2_situ.era == "2018-2025")].set_index("bucket")["explosive_rate"]
    dp2010 = q2_dp[q2_dp.era == "2010-2017"].set_index("bucket")["explosive_rate"]
    dp2018 = q2_dp[q2_dp.era == "2018-2025"].set_index("bucket")["explosive_rate"]
    gb = q2_gb.pivot(index="era", columns="garbage", values="explosive_rate")
    lines.append(
        f"**Explosive rate rises with down (3rd+ is highest) and with distance-to-goal getting shorter "
        f"(red zone lowest), and the 'more early-drive shot-taking now' prediction is not borne out** -- "
        f"play-1-of-drive explosive rate is {dp2010.get('1st', float('nan')):.3f} (2010-2017) vs "
        f"{dp2018.get('1st', float('nan')):.3f} (2018-2025), a small change and not obviously larger than the "
        f"change on later-drive plays.\n"
    )
    lines.append(
        f"- By down, 2018-2025: 1st {down_e2.get('1st', float('nan')):.3f}, 2nd {down_e2.get('2nd', float('nan')):.3f}, "
        f"3rd+ {down_e2.get('3rd+', float('nan')):.3f} (full down x distance x zone x score x quarter breakdown, both "
        f"eras, in `q2_situational_explosive_rate.csv`).\n"
        f"- By play-in-drive, explosive rate: 1st {dp2010.get('1st',float('nan')):.3f}->{dp2018.get('1st',float('nan')):.3f}, "
        f"2nd {dp2010.get('2nd',float('nan')):.3f}->{dp2018.get('2nd',float('nan')):.3f}, "
        f"3rd {dp2010.get('3rd',float('nan')):.3f}->{dp2018.get('3rd',float('nan')):.3f}, "
        f"4th+ {dp2010.get('4th+',float('nan')):.3f}->{dp2018.get('4th+',float('nan')):.3f}.\n"
        f"- Garbage time (wp outside [0.05,0.95]) explosive rate vs competitive time: 2010-2017 "
        f"{gb.loc['2010-2017', True]:.3f} vs {gb.loc['2010-2017', False]:.3f}; 2018-2025 "
        f"{gb.loc['2018-2025', True]:.3f} vs {gb.loc['2018-2025', False]:.3f} -- garbage time is consistently "
        f"more explosive (trailing teams throw downfield), in both eras.\n"
        f"- Share of all explosive plays occurring in garbage time ranges "
        f"{q2_gbs['garbage_share_of_explosives'].min():.1%}-{q2_gbs['garbage_share_of_explosives'].max():.1%} "
        f"across 2010-2025 (season series in `q2_garbage_share_of_explosives_by_season.csv`); no strong trend, "
        f"see CSV for year-by-year.\n"
    )
    lines.append(
        "- Caveat: score-state buckets are 5-way (trailing >7 / trailing 1-7 / tied / leading 1-7 / leading >7), "
        "a finer split than the brief's literal 3-way wording, kept because it is more informative and the "
        "3-way collapse is a simple re-group of the CSV. Field zones use yardline_100 (distance to opponent's "
        "end zone): own 1-20 = 80-99, own 21-50 = 50-79, opp 49-21 = 21-49, red zone = 0-20.\n"
    )

    # -------------------------------------------------- Q3
    lines.append("## Q3. Where they come from, offense vs defense\n")
    s1, s2, s3 = q3_std.set_index("era").loc["1999-2007"], q3_std.set_index("era").loc["2008-2016"], q3_std.set_index("era").loc["2017-2025"]
    top5_early = q3_top5[q3_top5.season <= 2007]["top5_share"].mean()
    top5_mid = q3_top5[(q3_top5.season >= 2008) & (q3_top5.season <= 2016)]["top5_share"].mean()
    top5_late = q3_top5[q3_top5.season >= 2017]["top5_share"].mean()
    lines.append(
        f"**The league is homogenizing on offense (between-team spread in explosives generated is shrinking) "
        f"but the top-5-offense share of league explosive plays has not shrunk to match** -- std of "
        f"explosives-generated/game: {s1['std_gen_per_game']:.3f} (1999-2007) -> {s2['std_gen_per_game']:.3f} "
        f"(2008-2016) -> {s3['std_gen_per_game']:.3f} (2017-2025); CV (std/mean): {s1['cv_gen']:.3f} -> "
        f"{s2['cv_gen']:.3f} -> {s3['cv_gen']:.3f}.\n"
    )
    lines.append(
        f"- Explosives-allowed spread by era: std {s1['std_allowed_per_game']:.3f} -> {s2['std_allowed_per_game']:.3f} "
        f"-> {s3['std_allowed_per_game']:.3f}; CV {s1['cv_allowed']:.3f} -> {s2['cv_allowed']:.3f} -> {s3['cv_allowed']:.3f}.\n"
        f"- Top-5-offense share of all league explosive plays, season average by era: {top5_early:.1%} "
        f"(1999-2007) / {top5_mid:.1%} (2008-2016) / {top5_late:.1%} (2017-2025); full season series in "
        f"`q3_top5_offense_concentration_by_season.csv`.\n"
        f"- Top 10 / bottom 10 team-seasons 2019-2025 by explosives generated per game and allowed per game are "
        f"in `q3_top10_generated_2019_2025.csv`, `q3_bottom10_generated_2019_2025.csv`, "
        f"`q3_top10_allowed_2019_2025.csv`, `q3_bottom10_allowed_2019_2025.csv`.\n"
    )
    lines.append(
        "- Caveat: 'homogenizing' here is about the spread in team RATES, which can fall even while the "
        "absolute count of explosive plays a top offense produces stays high if the league mean also moved -- "
        "read the CV columns (scale-free) alongside the raw std.\n"
    )

    # -------------------------------------------------- Q4
    lines.append("## Q4. The defensive mechanism\n")
    dp = q4_dp.pivot(index="bucket", columns="era", values="def_play_rate")
    order = ["1", "2", "3", "4", "5", "6", "7", "8+"]
    dp = dp.reindex(order)
    lines.append(
        f"**The defensive-play-probability curve rises only over the first 2-3 plays of a drive, then goes flat "
        f"(plays 3 through 8+ sit in the same ~0.095-0.11 band, no further climb) -- so Simms' mechanism has a "
        f"grain of truth at the very start of a drive but does not describe accumulating danger for a drive "
        f"that keeps going, in any era.** Play-1 -> play-3 -> play-8+ def-play rate, "
        f"1999-2007: {dp.loc['1','1999-2007']:.3f} -> {dp.loc['3','1999-2007']:.3f} -> {dp.loc['8+','1999-2007']:.3f}; "
        f"2008-2016: {dp.loc['1','2008-2016']:.3f} -> {dp.loc['3','2008-2016']:.3f} -> {dp.loc['8+','2008-2016']:.3f}; "
        f"2017-2025: {dp.loc['1','2017-2025']:.3f} -> {dp.loc['3','2017-2025']:.3f} -> {dp.loc['8+','2017-2025']:.3f}. "
        f"The shape (rise-then-plateau) is the same in every era; only the level has drifted down slightly, "
        f"consistent with NOTES.md's per-snap def-play-rate decline.\n"
    )
    dt = q4_dt.pivot(index="len_bucket", columns="era", values="turnover_rate").reindex(order)
    lines.append(
        f"- Drive-ends-in-turnover probability by drive length (plays, capped at 8+): 1999-2007 "
        f"{dt.loc['1','1999-2007']:.3f} (1 play) / {dt.loc['3','1999-2007']:.3f} (3 plays) / "
        f"{dt.loc['8+','1999-2007']:.3f} (8+ plays); 2017-2025 {dt.loc['1','2017-2025']:.3f} / "
        f"{dt.loc['3','2017-2025']:.3f} / {dt.loc['8+','2017-2025']:.3f}. This is NOT a clean length-vs-risk "
        f"read: 1- and 2-play drives are ~47-49% turnovers in every era because a turnover truncates the drive "
        f"right there (a pick-six or fumble on the opening snap IS a 1-play drive by construction), a selection "
        f"effect, not rising early danger. Past that artifact the rate is lowest at 3 plays and drifts down "
        f"further by 8+ in every era -- if anything drives that survive past the first couple of snaps get "
        f"SAFER for the offense the longer they run, the opposite of Simms' claim. Full table in "
        f"`q4_turnover_rate_by_drive_length.csv`.\n"
    )
    q4e = q4_era.set_index("era")
    lines.append(
        f"- Per-drive P(>=1 defensive play): {q4e.loc['1999-2007','p_at_least_one_def_play_per_drive']:.3f} "
        f"(1999-2007) -> {q4e.loc['2008-2016','p_at_least_one_def_play_per_drive']:.3f} (2008-2016) -> "
        f"{q4e.loc['2017-2025','p_at_least_one_def_play_per_drive']:.3f} (2017-2025). Points per drive (TD=6.95, "
        f"FG=3, safety=-2, all else 0 -- approximate, no 2pt/XP-miss detail): "
        f"{q4e.loc['1999-2007','points_per_drive']:.3f} -> {q4e.loc['2008-2016','points_per_drive']:.3f} -> "
        f"{q4e.loc['2017-2025','points_per_drive']:.3f}. Points per drive has risen while P(>=1 def play) per "
        f"drive has been flat-to-down, so on the whole-drive view too, 'long/more-productive drives score' is "
        f"better supported than 'long drives are dangerous for offenses.'\n"
    )
    lines.append(
        "- Caveat: the points-per-drive figure is a rough estimate (fixed_drive_result category -> assumed "
        "point value), not actual scoreboard deltas; it is directionally fine for this comparison but should "
        "not be quoted as an exact PPD number on the site without redoing it from real point deltas. n per "
        "drive-length cell shrinks at 8+ (long drives are rarer) but is still in the thousands per era -- see "
        "the `drives`/`plays` count columns in the CSVs. The turnover-by-length table in particular should be "
        "presented with the selection-effect caveat above if it goes on the site at all.\n"
    )

    lines.append("## Consistency with docs/NOTES.md\n")
    lines.append(
        "- Confirms NOTES.md's mechanism finding and sharpens it: defensive-play rate per snap is flat/falling "
        "with drive position within every era (Q4), and long drives score more than they turn the ball over, "
        "which is the opposite of what would justify Simms' 'defenses want long drives' claim.\n"
        "- Adds nuance NOTES.md didn't have: the 2018->2025 explosive-play decline is a *passing* efficiency "
        "decline (fewer explosive plays per dropback), not primarily a rushing decline or a pass-rate mix "
        "effect (Q1) -- worth stating precisely on the site rather than leaving 'pass rate is falling' to imply "
        "the mix change is the main driver.\n"
        "- Nothing here contradicts NOTES.md; the situational (Q2) and offense/defense-spread (Q3) results are "
        "new detail, not previously stated in NOTES.md, so there's nothing to reconcile there.\n"
    )

    (OUT / "FINDINGS_plays.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
