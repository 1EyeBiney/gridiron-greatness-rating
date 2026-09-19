"""
Explosive Edge: definitions and the team-game aggregator.

Everything here turns play-by-play rows into ONE ROW PER TEAM-GAME. A
"scrimmage play" is the unit almost every count below is built on:
play_type in ("pass", "run"), the nflverse `play` flag set (excludes
penalty-only/no-play rows), and not a qb_kneel or qb_spike (those have
play_type "run"/"pass" respectively but aren't a real offensive snap).

    scrimmage = play_type.isin(["pass", "run"]) & play==1
                & ~qb_kneel & ~qb_spike

Explosive play, four variants (mirrors PLAN.md section 3):
  - explosive_20_10 (primary): pass >= 20 yards OR rush >= 10 yards.
  - explosive_25_15: pass >= 25 OR rush >= 15.
  - explosive_20_20: pass >= 20 OR rush >= 20.
  - explosive_epa2: any scrimmage play with epa >= 2.0 (yardage-free).
All four are counted on scrimmage plays where the team is on offense
(posteam == team).

Turnover: interception or fumble lost, on ANY play type including special
teams (`turnovers`), plus a scrimmage-only variant (`turnovers_scrimmage`).
Counted against whichever team actually lost the ball, NOT always
`posteam`. On a pass/run/kickoff play `posteam` is (checked against 2023
data) ~99-100% the team that fumbles, so it's a safe attribution there and
for interceptions. But on a PUNT, `posteam` is the punting team while the
ball is live, and it's the returner (`defteam`) who fumbles it away 100% of
the time in the 2023 check - crediting the turnover to `posteam` there
would give the turnover to the wrong team entirely. So the turnover is
attributed to `fumbled_1_team` when it's not null (falling back to
`posteam` only when `fumbled_1_team` is null), and interceptions always
stay with `posteam` (every interception is thrown by the passer, i.e.
posteam, regardless of play type happening to look like something else).
The team that FORCED the turnover - the other side in the game, not
necessarily `defteam` - gets credit in `def_plays_made` (see below).

Defensive "play": now counts PLAYS, not raw flags: a play credits a team's
defense once if it achieved at least one of (sack, forced turnover, tackle
for loss) - so a strip-sack (sack AND forced turnover on the same play)
counts once, not twice. "Forced the turnover" uses the same fumble
attribution as above: the team that benefits is the other team in the
game from whoever the turnover was charged to (matches `defteam` on
pass/run/kickoff turnovers; on a punt where the punting team recovers its
own forced fumble, that credit goes to the punting team even though it was
`posteam`, not `defteam`, on that play row - it is that team's defense/
special-teams forcing the giveaway, and PLAN.md's def_plays_made is framed
around "this team's DEFENSE achieved" without carving out special teams).

Garbage time: every explosive/turnover count above also has an `_ng`
(non-garbage) twin, restricted to plays with the posteam's win probability
(`wp`) in [0.05, 0.95]. PLAN.md only calls out "the same explosive/turnover
counts" for the _ng twin, so drive metrics, sacks_taken, negative_plays and
def_plays_made are not duplicated with _ng suffixes.

Differential columns (`*_diff`, team minus opponent) are added for the
explosive_*, turnovers*, and yards columns (base and _ng) by self-joining
team-game rows on game_id.

Team/opponent codes are nflverse's relocation-specific team codes (e.g.
STL, LA). `franchise`/`opp_franchise` map them through the main repo's
data/reference/franchise_crosswalk.csv, the same crosswalk
home-field-advantage's hfa.py uses; a code with no crosswalk row (i.e. one
whose franchise never moved) maps to itself.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]           # studies/explosive-edge
MAIN = REPO.parents[1]                                 # gridiron-greatness-rating repo root
REF = MAIN / "data" / "reference"

EXPLOSIVE_DEFS = {
    "explosive_20_10": (20, 10),
    "explosive_25_15": (25, 15),
    "explosive_20_20": (20, 20),
}
GARBAGE_WP_LO = 0.05
GARBAGE_WP_HI = 0.95
PLAYOFF_TYPES = {"WC", "DIV", "CON", "SB"}
VALID_GAME_TYPES = {"REG", "POST"} | PLAYOFF_TYPES


# ----------------------------------------------------------------- helpers


def load_crosswalk() -> pd.DataFrame:
    cw = pd.read_csv(REF / "franchise_crosswalk.csv")
    cw = cw[cw["source"] == "nflverse"].copy()
    cw["valid_to_season"] = cw["valid_to_season"].fillna(9999)
    return cw


def to_franchise(codes: pd.Series, seasons: pd.Series, cw: pd.DataFrame | None = None) -> pd.Series:
    """Map nflverse team codes to franchise-stable codes for the given
    seasons. A (code, season) with no matching crosswalk row keeps its
    original code (i.e. franchises that never relocated aren't listed)."""
    if cw is None:
        cw = load_crosswalk()
    out = codes.copy()
    for _, row in cw.iterrows():
        mask = (codes == row["source_code"]) & (seasons >= row["valid_from_season"]) & (seasons <= row["valid_to_season"])
        out = out.where(~mask, row["franchise_id"])
    # nflverse play-by-play labels every season with the franchise's CURRENT
    # code (the 1999 Rams are "LA", the 2005 Raiders "LV"), unlike the
    # schedule file the crosswalk windows were written for. Any code the
    # crosswalk knows at all therefore maps to its franchise regardless of
    # season; only codes the crosswalk has never seen keep their own value.
    known = cw.drop_duplicates("source_code").set_index("source_code")["franchise_id"]
    still_raw = out.isin(known.index) & (out == codes)
    out = out.where(~still_raw, codes.map(known))
    return out


def _game_type_series(pbp: pd.DataFrame) -> pd.Series:
    """The play_by_play parquet files (checked 1999-2025) do not actually
    carry a `game_type` column with WC/DIV/CON/SB round detail - only
    `season_type` with values REG/POST. (The main repo's separate nfldata
    games.csv does carry that detail; it isn't in play-by-play.) So
    team_game.csv's game_type is REG or POST only - "postseason" as PLAN.md
    asks for, without a round breakdown. xe_ingest.py still requests a
    `game_type` column defensively in case nflverse adds one later; if
    present and non-null it wins."""
    if "game_type" in pbp.columns and pbp["game_type"].notna().any():
        return pbp["game_type"]
    return pbp["season_type"]


def _scrimmage_mask(pbp: pd.DataFrame) -> pd.Series:
    play_ok = pbp["play"].fillna(1).astype(float) != 0 if "play" in pbp.columns else pd.Series(True, index=pbp.index)
    kneel = pbp.get("qb_kneel", pd.Series(0, index=pbp.index)).fillna(0).astype(float) != 0
    spike = pbp.get("qb_spike", pd.Series(0, index=pbp.index)).fillna(0).astype(float) != 0
    return pbp["play_type"].isin(["pass", "run"]) & play_ok & ~kneel & ~spike


def _parse_mmss(series: pd.Series) -> pd.Series:
    """'MM:SS' drive time-of-possession strings -> seconds (float, NaN kept)."""
    parts = series.astype(str).str.split(":", expand=True)
    if parts.shape[1] < 2:
        return pd.Series(np.nan, index=series.index)
    minutes = pd.to_numeric(parts[0], errors="coerce")
    seconds = pd.to_numeric(parts[1], errors="coerce")
    out = minutes * 60 + seconds
    out[series.isna() | (series.astype(str).str.lower() == "nan")] = np.nan
    return out


def _bool(pbp: pd.DataFrame, col: str) -> pd.Series:
    return pbp.get(col, pd.Series(0, index=pbp.index)).fillna(0).astype(float) != 0


# --------------------------------------------------------------- aggregate


def team_game(pbp: pd.DataFrame) -> pd.DataFrame:
    """Aggregate one season's (or any collection of games') play-by-play
    rows to one row per team-game. See module docstring for definitions."""
    pbp = pbp.copy()
    pbp["game_type"] = _game_type_series(pbp)
    pbp = pbp[pbp["game_type"].isin(VALID_GAME_TYPES)].copy()

    scrim = _scrimmage_mask(pbp)
    in_wp_window = pbp["wp"].between(GARBAGE_WP_LO, GARBAGE_WP_HI)
    ng = in_wp_window.fillna(False)  # plays with unknown wp are treated as garbage-time (excluded) for _ng counts

    interception = _bool(pbp, "interception")
    fumble_lost = _bool(pbp, "fumble_lost")
    sack = _bool(pbp, "sack")
    tfl = _bool(pbp, "tackled_for_loss")
    turnover = interception | fumble_lost

    # Who the turnover is charged to: posteam for an interception (the
    # passer's team); for a lost fumble, fumbled_1_team (who actually had
    # the ball when it came loose), falling back to posteam only if
    # fumbled_1_team is missing. See module docstring - this matters
    # because posteam is the PUNTING team on a punt, not the returner who
    # fumbles it away.
    fumbled_1_team = pbp.get("fumbled_1_team", pd.Series(pd.NA, index=pbp.index))
    turnover_team = pd.Series(pd.NA, index=pbp.index, dtype=object)
    turnover_team = turnover_team.where(~fumble_lost, fumbled_1_team.where(fumbled_1_team.notna(), pbp["posteam"]))
    turnover_team = turnover_team.where(~interception, pbp["posteam"])
    # Whoever forced it: the other team in the game from turnover_team.
    forced_by_team = pd.Series(pd.NA, index=pbp.index, dtype=object)
    is_home_turnover = turnover_team == pbp["home_team"]
    forced_by_team = forced_by_team.where(~turnover, pbp["away_team"].where(is_home_turnover, pbp["home_team"]))

    pass_play = scrim & (pbp["play_type"] == "pass")
    rush_play = scrim & (pbp["play_type"] == "run")

    explosive = {}
    explosive_ng = {}
    for name, (pass_yd, rush_yd) in EXPLOSIVE_DEFS.items():
        hit = scrim & ((pass_play & (pbp["yards_gained"] >= pass_yd)) | (rush_play & (pbp["yards_gained"] >= rush_yd)))
        explosive[name] = hit
        explosive_ng[name] = hit & ng
    hit_epa = scrim & (pbp["epa"] >= 2.0)
    explosive["explosive_epa2"] = hit_epa
    explosive_ng["explosive_epa2"] = hit_epa & ng

    d = pd.DataFrame({
        "game_id": pbp["game_id"], "season": pbp["season"], "week": pbp["week"], "game_type": pbp["game_type"],
        "posteam": pbp["posteam"], "defteam": pbp["defteam"],
        "home_team": pbp["home_team"], "away_team": pbp["away_team"],
        "scrim": scrim, "pass_play": pass_play, "rush_play": rush_play,
        "dropback": _bool(pbp, "qb_dropback") & scrim,
        "yards_gained": pbp["yards_gained"], "epa": pbp["epa"],
        "sack": sack, "tfl": tfl, "turnover": turnover,
        "turnover_team": turnover_team, "forced_by_team": forced_by_team,
        "turnover_scrim": turnover & scrim,
        "negative_play": scrim & (pbp["yards_gained"] < 0),
        "drive": pbp["drive"], "drive_play_count": pbp["drive_play_count"],
        "drive_seconds": _parse_mmss(pbp["drive_time_of_possession"]),
    })
    for name, hit in explosive.items():
        d[name] = hit
    for name, hit in explosive_ng.items():
        d[f"{name}_ng"] = hit
    d["turnover_ng"] = turnover & ng
    d["turnover_scrim_ng"] = turnover & scrim & ng

    off = _offense_agg(d)
    turnovers = _turnover_agg(d)
    defn = _defense_agg(d)
    drives = _drive_agg(d)

    base = _game_base(pbp)
    out = base.merge(off, on=["game_id", "team"], how="left").merge(turnovers, on=["game_id", "team"], how="left") \
              .merge(defn, on=["game_id", "team"], how="left").merge(drives, on=["game_id", "team"], how="left")
    count_cols = [c for c in out.columns if c not in
                  ("game_id", "season", "week", "game_type", "team", "opponent", "is_home",
                   "points_for", "points_against")]
    out[count_cols] = out[count_cols].fillna(0)

    cw = load_crosswalk()
    out["franchise"] = to_franchise(out["team"], out["season"], cw)
    out["opp_franchise"] = to_franchise(out["opponent"], out["season"], cw)

    out["margin"] = out["points_for"] - out["points_against"]
    out["win"] = np.select([out["margin"] > 0, out["margin"] < 0], [1.0, 0.0], default=0.5)

    out = _add_differentials(out)
    return out.sort_values(["season", "week", "game_id", "is_home"], ascending=[True, True, True, False]).reset_index(drop=True)


def _game_base(pbp: pd.DataFrame) -> pd.DataFrame:
    """One row per (game_id, team) for both the home and away side, with
    season/week/game_type/points/home flag - independent of play filters,
    so every team-game exists even for a game with zero scrimmage plays."""
    g = pbp.drop_duplicates(subset=["game_id"])[
        ["game_id", "season", "week", "game_type", "home_team", "away_team", "home_score", "away_score"]
    ]
    home = g.rename(columns={"home_team": "team", "away_team": "opponent",
                              "home_score": "points_for", "away_score": "points_against"})
    home["is_home"] = True
    away = g.rename(columns={"away_team": "team", "home_team": "opponent",
                              "away_score": "points_for", "home_score": "points_against"})
    away["is_home"] = False
    cols = ["game_id", "season", "week", "game_type", "team", "opponent", "points_for", "points_against", "is_home"]
    return pd.concat([home[cols], away[cols]], ignore_index=True)


def _offense_agg(d: pd.DataFrame) -> pd.DataFrame:
    explosive_cols = list(EXPLOSIVE_DEFS) + ["explosive_epa2"]
    ng_cols = [f"{c}_ng" for c in explosive_cols]
    g = d.groupby(["game_id", "posteam"], dropna=True)
    out = g.agg(
        plays=("scrim", "sum"),
        pass_plays=("pass_play", "sum"),
        rush_plays=("rush_play", "sum"),
        dropbacks=("dropback", "sum"),
        sacks_taken=("sack", lambda s: (s & d.loc[s.index, "scrim"]).sum()),
        negative_plays=("negative_play", "sum"),
        yards=("yards_gained", lambda s: s[d.loc[s.index, "scrim"]].sum()),
        epa_total=("epa", lambda s: s[d.loc[s.index, "scrim"]].sum()),
        **{c: (c, "sum") for c in explosive_cols},
        **{c: (c, "sum") for c in ng_cols},
    ).reset_index().rename(columns={"posteam": "team"})
    return out


def _turnover_agg(d: pd.DataFrame) -> pd.DataFrame:
    """Turnovers charged to the team that actually lost the ball
    (turnover_team - see module docstring), not always posteam."""
    g = d.groupby(["game_id", "turnover_team"], dropna=True)
    out = g.agg(
        turnovers=("turnover", "sum"),
        turnovers_ng=("turnover_ng", "sum"),
        turnovers_scrimmage=("turnover_scrim", "sum"),
        turnovers_scrimmage_ng=("turnover_scrim_ng", "sum"),
    ).reset_index().rename(columns={"turnover_team": "team"})
    return out


def _defense_agg(d: pd.DataFrame) -> pd.DataFrame:
    """def_plays_made counts PLAYS (not summed flags) on which a team's
    defense achieved at least one of: a sack (defteam == team), a tackle
    for loss (defteam == team), or forcing the turnover (forced_by_team ==
    team - see module docstring; usually but not always defteam). A
    strip-sack satisfies both the sack and forced-turnover conditions on
    one play and is counted once."""
    frames = []
    for team_col in ("home_team", "away_team"):
        team = d[team_col]
        credit = ((d["defteam"] == team) & (d["sack"] | d["tfl"])) | (d["forced_by_team"] == team)
        frames.append(pd.DataFrame({"game_id": d["game_id"], "team": team, "credit": credit}))
    long = pd.concat(frames, ignore_index=True)
    out = long.groupby(["game_id", "team"])["credit"].sum().reset_index().rename(columns={"credit": "def_plays_made"})
    return out


def _drive_agg(d: pd.DataFrame) -> pd.DataFrame:
    """Unique drives this team had the ball on (posteam), with total plays
    and seconds summed across those drives (drive_play_count and
    drive_time_of_possession are drive-level constants repeated on every
    play of the drive, so take one row per (game_id, posteam, drive))."""
    dd = d.dropna(subset=["drive"]).drop_duplicates(subset=["game_id", "posteam", "drive"])
    g = dd.groupby(["game_id", "posteam"])
    out = g.agg(
        drives=("drive", "nunique"),
        drive_plays_total=("drive_play_count", "sum"),
        drive_seconds_total=("drive_seconds", "sum"),
    ).reset_index().rename(columns={"posteam": "team"})
    return out


def _add_differentials(out: pd.DataFrame) -> pd.DataFrame:
    """Team-minus-opponent differentials for explosive_*, turnovers*, and
    yards (base and _ng), via a self-join of each team-game row to its
    game partner's row."""
    diff_cols = list(EXPLOSIVE_DEFS) + ["explosive_epa2"]
    diff_cols += [f"{c}_ng" for c in diff_cols]
    diff_cols += ["turnovers", "turnovers_ng", "turnovers_scrimmage", "turnovers_scrimmage_ng", "yards"]
    partner = out[["game_id", "team"] + diff_cols].rename(
        columns={"team": "_opp_team", **{c: f"_opp_{c}" for c in diff_cols}})
    merged = out.merge(partner, on="game_id")
    merged = merged[merged["_opp_team"] != merged["team"]].drop(columns="_opp_team")
    for c in diff_cols:
        merged[f"{c}_diff"] = merged[c] - merged[f"_opp_{c}"]
        merged = merged.drop(columns=f"_opp_{c}")
    return merged


# -------------------------------------------------------------- league table


def league_season(team_game_df: pd.DataFrame) -> pd.DataFrame:
    """Per-season league totals/rates for the mechanism analysis (PLAN.md
    section 4C): explosive rate per play and per drive, plays per drive,
    seconds per drive, pass rate, defensive-play rate per snap, turnovers
    per game. Regular season only (postseason has too few games/season to
    make a stable rate, and mixes with REG unevenly by era)."""
    reg = team_game_df[team_game_df["game_type"] == "REG"]
    g = reg.groupby("season")
    out = pd.DataFrame({
        "team_games": g.size(),
        "plays": g["plays"].sum(),
        "pass_plays": g["pass_plays"].sum(),
        "drives": g["drives"].sum(),
        "explosive_20_10": g["explosive_20_10"].sum(),
        "explosive_20_10_ng": g["explosive_20_10_ng"].sum(),
        "def_plays_made": g["def_plays_made"].sum(),
        "turnovers": g["turnovers"].sum(),
        "drive_plays_total": g["drive_plays_total"].sum(),
        "drive_seconds_total": g["drive_seconds_total"].sum(),
    })
    out["explosive_rate_per_play"] = out["explosive_20_10"] / out["plays"]
    out["explosive_rate_per_play_ng"] = out["explosive_20_10_ng"] / out["plays"]
    out["explosive_rate_per_drive"] = out["explosive_20_10"] / out["drives"]
    out["plays_per_drive"] = out["drive_plays_total"] / out["drives"]
    out["seconds_per_drive"] = out["drive_seconds_total"] / out["drives"]
    out["pass_rate"] = out["pass_plays"] / out["plays"]
    out["def_play_rate_per_snap"] = out["def_plays_made"] / out["plays"]
    out["turnovers_per_game"] = out["turnovers"] / (out["team_games"] / 2)
    return out.reset_index()


# -------------------------------------------------------------- pipeline


OUT = REPO / "data" / "processed"


def build_all_seasons(first: int = 1999, last: int = 2025) -> pd.DataFrame:
    """Load every downloaded season's play-by-play and aggregate each one
    separately (aggregating per-season keeps memory bounded - 27 seasons of
    full play-by-play at once is not necessary since games never cross a
    season boundary), then concatenate."""
    import xe_ingest
    frames = []
    for season in range(first, last + 1):
        path = xe_ingest.RAW / f"play_by_play_{season}.parquet"
        if not path.exists():
            continue
        frames.append(team_game(xe_ingest.load_season(season)))
    return pd.concat(frames, ignore_index=True)


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    tg = build_all_seasons()
    tg.to_csv(OUT / "team_game.csv", index=False)
    ls = league_season(tg)
    ls.to_csv(OUT / "league_season.csv", index=False)
    return {"team_game": tg, "league_season": ls}


if __name__ == "__main__":
    res = run()
    print(f"team_game.csv: {len(res['team_game']):,} rows")
    print(f"league_season.csv: {len(res['league_season']):,} rows")
