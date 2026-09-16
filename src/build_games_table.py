"""
Build the unified Core games table for the Gridiron Greatness Rating project.

Combines:
  - FiveThirtyEight nfl-elo-game data (data/raw/fivethirtyeight/nfl_games.csv),
    used for seasons 1970-1998. team1 is the home team (or designated home on
    a neutral site) per FiveThirtyEight's published convention; score1/score2
    correspond to team1/team2.
  - nflverse nfldata games.csv (data/raw/nflverse/games.csv), used for seasons
    1999 through the latest COMPLETED season (rows with a null score are an
    in-progress or future season and are dropped).

Applies the franchise crosswalk (data/reference/franchise_crosswalk.csv) so
every team is identified by one stable franchise_id across relocations.

Output: data/processed/games.csv - one row per game, columns:
  season, date, week, game_type, home_franchise, away_franchise,
  home_score, away_score, neutral_site, overtime, source

game_type is REG or PLAYOFF for 1970-1998 (FiveThirtyEight only flags
playoff as a binary; round detail - WC/DIV/CON/SB - is not yet available
for this span, see docs/BUILD_PLAN.md open items) and REG/WC/DIV/CON/SB for
1999-present (from nflverse directly).
"""
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw"
REF = REPO / "data" / "reference"
OUT = REPO / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

LATEST_COMPLETED_SEASON = 2025  # as of fetch date 2026-09-16; 2026 season in progress


def load_crosswalk():
    cw = pd.read_csv(REF / "franchise_crosswalk.csv")
    return cw


def apply_crosswalk(codes: pd.Series, source: str, season: pd.Series, cw: pd.DataFrame) -> pd.Series:
    """Map raw team codes to stable franchise_id using the crosswalk table.
    Codes not listed in the crosswalk for this source map to themselves."""
    sub = cw[cw["source"] == source]
    out = codes.copy()
    for _, row in sub.iterrows():
        mask = codes == row["source_code"]
        if pd.notna(row["valid_from_season"]):
            mask &= season >= row["valid_from_season"]
        if pd.notna(row["valid_to_season"]):
            mask &= season <= row["valid_to_season"]
        out = out.where(~mask, row["franchise_id"])
    return out


def load_fte(cw: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW / "fivethirtyeight" / "nfl_games.csv")
    df = df[(df["season"] >= 1970) & (df["season"] <= 1998)].copy()

    df["home_franchise"] = apply_crosswalk(df["team1"], "fivethirtyeight", df["season"], cw)
    df["away_franchise"] = apply_crosswalk(df["team2"], "fivethirtyeight", df["season"], cw)
    df["home_score"] = df["score1"]
    df["away_score"] = df["score2"]
    df["neutral_site"] = df["neutral"].astype(bool)
    df["game_type"] = df["playoff"].apply(lambda x: "PLAYOFF" if x == 1 else "REG")
    df["week"] = pd.NA
    df["overtime"] = pd.NA
    df["source"] = "fivethirtyeight"
    df["date"] = df["date"]

    return df[[
        "season", "date", "week", "game_type", "home_franchise", "away_franchise",
        "home_score", "away_score", "neutral_site", "overtime", "source",
    ]]


def load_nflverse(cw: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(RAW / "nflverse" / "games.csv")
    df = df[df["season"] >= 1999].copy()
    # drop unplayed games (in-progress/future season at fetch time)
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df = df[df["season"] <= LATEST_COMPLETED_SEASON].copy()

    df["home_franchise"] = apply_crosswalk(df["home_team"], "nflverse", df["season"], cw)
    df["away_franchise"] = apply_crosswalk(df["away_team"], "nflverse", df["season"], cw)
    df["neutral_site"] = df["location"].astype(str).str.strip().str.lower().eq("neutral")
    df["overtime"] = df["overtime"].astype(bool)
    df["game_type"] = df["game_type"]  # REG, WC, DIV, CON, SB already
    df["source"] = "nflverse"
    df["date"] = df["gameday"]

    return df[[
        "season", "date", "week", "game_type", "home_franchise", "away_franchise",
        "home_score", "away_score", "neutral_site", "overtime", "source",
    ]]


def main():
    cw = load_crosswalk()
    fte = load_fte(cw)
    nfv = load_nflverse(cw)

    games = pd.concat([fte, nfv], ignore_index=True)
    games["home_score"] = games["home_score"].astype(int)
    games["away_score"] = games["away_score"].astype(int)
    games["margin"] = games["home_score"] - games["away_score"]
    games = games.sort_values(["season", "date"]).reset_index(drop=True)
    games["game_uid"] = games.index.map(lambda i: f"G{i:06d}")

    out_path = OUT / "games.csv"
    games.to_csv(out_path, index=False)
    print(f"Wrote {len(games)} games to {out_path}")
    print(f"Season range: {games['season'].min()}-{games['season'].max()}")
    print(f"By source:\n{games['source'].value_counts()}")
    print(f"By game_type:\n{games['game_type'].value_counts()}")


if __name__ == "__main__":
    main()
