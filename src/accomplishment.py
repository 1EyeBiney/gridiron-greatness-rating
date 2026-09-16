"""
Accomplishment Rating (ACC), BUILD_PLAN section 3: "A score for how
successful the season was: regular-season record and standing, division
title, playoff wins, conference championship, Super Bowl result,
undefeated season, and postseason dominance. This is where the trophy is
rewarded." The exact point schedule was left open ("to be drafted in
Phase 5", section 11) - this is that draft, computed and documented for
Brian's review, the same "recommendation, not a lock" pattern Phase 4
used for the model family.

Point schedule (every choice below is a documented judgment call, not
fixed by BUILD_PLAN, and open to being changed on review):

  Regular-season base       win_pct * 10          (0-10, continuous)
  Division title            +2                    best win_pct in division*
  Best record in conference +1                    best win_pct in conference*
  Each playoff win          +2                    except a Super Bowl win,
                                                    which gets the bonus below
                                                    instead (no double count)
  Reached the Super Bowl    +4                     win or lose
  Won the Super Bowl        +6 additional
  Undefeated regular season +3                     win_pct == 1.0
  Dominant postseason run   +1                     playoff avg margin >= 10
                                                    (only if the team made
                                                    the playoffs)

  * Division/conference-best ties are broken by regular-season point
    differential, a documented approximation of the NFL's real tiebreaker
    procedure (head-to-head, common games, strength of schedule, etc.),
    which this project does not attempt to reconstruct.

Playoff wins get a flat bonus rather than one that escalates by round
(Wild Card < Divisional < Conference Championship) because 1970-1998
games only carry a generic PLAYOFF flag, not a round label (a carried-
forward Phase 1 item, still open) - escalating pre-1999 wins by round
isn't possible without reconstructing brackets this project hasn't
built. The Super Bowl itself needs no round label to identify: it is
reliably the single game with the latest date in a season (verified
across all 56 seasons, zero exceptions), so its own bonus applies
uniformly regardless of era.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from adversarial_audit import team_season_records
from division_alignment import build_team_season_conference_table
from models.common import load_games

REPO = Path(__file__).resolve().parents[1]

REGULAR_SEASON_BASE_SCALE = 10.0
DIVISION_TITLE_BONUS = 2.0
CONFERENCE_BEST_RECORD_BONUS = 1.0
PLAYOFF_WIN_BONUS = 2.0
SUPER_BOWL_APPEARANCE_BONUS = 4.0
SUPER_BOWL_WIN_BONUS = 6.0
UNDEFEATED_BONUS = 3.0
POSTSEASON_DOMINANCE_MARGIN_THRESHOLD = 10.0
POSTSEASON_DOMINANCE_BONUS = 1.0


def _best_in_group(records: pd.DataFrame, group_cols: list) -> pd.Series:
    """Boolean Series aligned to records' index: True for the team with
    the best win_pct in each group, point differential breaking ties."""
    ranked = records.sort_values(["win_pct", "point_diff"], ascending=False)
    winners = ranked.groupby(group_cols, as_index=False).first()
    winner_keys = set(zip(*[winners[c] for c in group_cols + ["franchise"]]))
    return records.apply(lambda r: tuple(r[c] for c in group_cols + ["franchise"]) in winner_keys, axis=1)


def playoff_win_counts(games: pd.DataFrame) -> pd.DataFrame:
    """Per team-season: total postseason wins, and whether that team won
    or appeared in the Super Bowl (identified as the season's last game -
    see module docstring)."""
    post = games[games["game_type"] != "REG"]
    rows = []
    for season, g in post.groupby("season"):
        sb_date = g["date"].max()
        sb_game = g[g["date"] == sb_date].iloc[0]
        sb_winner = sb_game["home_franchise"] if sb_game["margin"] > 0 else sb_game["away_franchise"]
        sb_loser = sb_game["away_franchise"] if sb_game["margin"] > 0 else sb_game["home_franchise"]

        teams = sorted(set(g["home_franchise"]).union(g["away_franchise"]))
        for team in teams:
            home = g[g["home_franchise"] == team]
            away = g[g["away_franchise"] == team]
            wins = int((home["margin"] > 0).sum() + (away["margin"] < 0).sum())
            rows.append(
                {
                    "season": season,
                    "franchise": team,
                    "playoff_wins": wins,
                    "reached_super_bowl": team in (sb_winner, sb_loser),
                    "won_super_bowl": team == sb_winner,
                }
            )
    return pd.DataFrame(rows)


def compute_acc(games: pd.DataFrame) -> pd.DataFrame:
    records = team_season_records(games)
    conf_table = build_team_season_conference_table(games)
    playoff = playoff_win_counts(games)

    records = records.merge(conf_table, on=["season", "franchise"], how="left")
    records["division_title"] = _best_in_group(records, ["season", "conference", "division"])
    records["conference_best_record"] = _best_in_group(records, ["season", "conference"])

    out = records.merge(playoff, on=["season", "franchise"], how="left")
    out["playoff_wins"] = out["playoff_wins"].fillna(0).astype(int)
    out["reached_super_bowl"] = out["reached_super_bowl"].fillna(False)
    out["won_super_bowl"] = out["won_super_bowl"].fillna(False)

    # Playoff-win bonus counts every win except the one that clinched the
    # Super Bowl (that win is credited via SUPER_BOWL_WIN_BONUS instead).
    non_sb_wins = out["playoff_wins"] - out["won_super_bowl"].astype(int)
    playoff_avg_margin = games.pipe(
        lambda g: pd.concat(
            [
                g.loc[g["game_type"] != "REG", ["season", "home_franchise", "margin"]].rename(
                    columns={"home_franchise": "franchise"}
                ),
                g.loc[g["game_type"] != "REG", ["season", "away_franchise", "margin"]]
                .rename(columns={"away_franchise": "franchise"})
                .assign(margin=lambda d: -d["margin"]),
            ]
        )
        .groupby(["season", "franchise"], as_index=False)["margin"]
        .mean()
        .rename(columns={"margin": "playoff_avg_margin"})
    )
    out = out.merge(playoff_avg_margin, on=["season", "franchise"], how="left")

    out["acc_base"] = out["win_pct"] * REGULAR_SEASON_BASE_SCALE
    out["acc_division_title"] = np.where(out["division_title"], DIVISION_TITLE_BONUS, 0.0)
    out["acc_conference_best"] = np.where(out["conference_best_record"], CONFERENCE_BEST_RECORD_BONUS, 0.0)
    out["acc_playoff_wins"] = non_sb_wins * PLAYOFF_WIN_BONUS
    out["acc_super_bowl_appearance"] = np.where(out["reached_super_bowl"], SUPER_BOWL_APPEARANCE_BONUS, 0.0)
    out["acc_super_bowl_win"] = np.where(out["won_super_bowl"], SUPER_BOWL_WIN_BONUS, 0.0)
    out["acc_undefeated"] = np.where(out["win_pct"] >= 1.0, UNDEFEATED_BONUS, 0.0)
    out["acc_postseason_dominance"] = np.where(
        out["playoff_avg_margin"] >= POSTSEASON_DOMINANCE_MARGIN_THRESHOLD, POSTSEASON_DOMINANCE_BONUS, 0.0
    )

    out["acc"] = out[
        [
            "acc_base",
            "acc_division_title",
            "acc_conference_best",
            "acc_playoff_wins",
            "acc_super_bowl_appearance",
            "acc_super_bowl_win",
            "acc_undefeated",
            "acc_postseason_dominance",
        ]
    ].sum(axis=1)

    return out


if __name__ == "__main__":
    acc = compute_acc(load_games())
    out_path = REPO / "data" / "processed" / "team_season_accomplishment.csv"
    acc.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(acc)} rows)")
    print(acc.sort_values("acc", ascending=False).head(10)[["season", "franchise", "acc"]].to_string(index=False))
