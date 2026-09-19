"""
Download nflverse play-by-play parquet files, 1999-2025, one file per
season, into data/raw/nflverse_pbp/ (gitignored - see SOURCE.md there for
provenance). This module only fetches and does light column selection; all
aggregation to team-game rows lives in xe_metrics.py.

Source: nflverse-data GitHub release "pbp"
(https://github.com/nflverse/nflverse-data/releases/download/pbp/
play_by_play_{season}.parquet), one file per season, ~20-40 MB each,
CC BY 4.0. Files already on disk are skipped unless --refresh is passed,
so a normal run only fetches seasons that are missing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import urllib.request
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]              # studies/explosive-edge
RAW = REPO / "data" / "raw" / "nflverse_pbp"
URL_TEMPLATE = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.parquet"
FIRST_SEASON = 1999
LAST_SEASON = 2025

# Columns pulled from the full play-by-play (which has 370+ columns). Kept
# to what xe_metrics.py needs to build the team-game aggregate, so the
# on-disk footprint and read time stay small.
COLUMNS = [
    "game_id", "season", "week", "game_type", "season_type",
    "home_team", "away_team", "home_score", "away_score",
    "posteam", "defteam", "posteam_type",
    "play_type", "play", "desc",
    "yards_gained", "epa", "wp",
    "interception", "fumble_lost", "fumbled_1_team", "sack", "tackled_for_loss",
    "qb_dropback", "rush_attempt", "pass_attempt",
    "qb_kneel", "qb_spike", "penalty",
    "drive", "drive_play_count", "drive_time_of_possession",
    "game_seconds_remaining",
]


def _download(season: int, dest: Path) -> None:
    url = URL_TEMPLATE.format(season=season)
    tmp = dest.with_suffix(".parquet.tmp")
    urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)


def fetch_season(season: int, refresh: bool = False) -> Path:
    """Download one season's parquet if not already present (or --refresh),
    and return its path."""
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"play_by_play_{season}.parquet"
    if dest.exists() and not refresh:
        return dest
    _download(season, dest)
    return dest


def load_season(season: int) -> pd.DataFrame:
    """Read one season's parquet, selecting only the columns xe_metrics.py
    needs. Falls back to whatever of COLUMNS is actually present, since
    nflverse has renamed a handful of columns across seasons/schema
    versions (see xe_metrics.py module docstring for the ones we hit)."""
    dest = RAW / f"play_by_play_{season}.parquet"
    import pyarrow.parquet as pq
    available = set(pq.ParquetFile(dest).schema.names)
    cols = [c for c in COLUMNS if c in available]
    df = pd.read_parquet(dest, columns=cols)
    for missing in set(COLUMNS) - available:
        df[missing] = pd.NA
    return df


def fetch_all(seasons: range = range(FIRST_SEASON, LAST_SEASON + 1), refresh: bool = False) -> dict:
    """Download every season's file (skipping what's already there unless
    refresh) and return {season: row_count} for the SOURCE.md note."""
    counts = {}
    for season in seasons:
        fetch_season(season, refresh=refresh)
        import pyarrow.parquet as pq
        counts[season] = pq.ParquetFile(RAW / f"play_by_play_{season}.parquet").metadata.num_rows
    return counts


def count_null_wp(seasons) -> dict:
    """Number of plays per season with a null win-probability (`wp`).
    xe_metrics.py's garbage-time filter treats a null wp as garbage time
    (excluded from every `_ng` counter, rather than included) since there's
    no probability to test against [0.05, 0.95]; this is what that
    decision affects, per season."""
    import pyarrow.parquet as pq
    out = {}
    for season in seasons:
        path = RAW / f"play_by_play_{season}.parquet"
        if not path.exists():
            continue
        wp = pd.read_parquet(path, columns=["wp"])["wp"]
        out[season] = int(wp.isna().sum())
    return out


def write_source_md(counts: dict, null_wp: dict | None = None) -> None:
    lines = [
        "# Source: nflverse play-by-play (nflfastR)",
        "",
        f"URL pattern: {URL_TEMPLATE}",
        "Repo: https://github.com/nflverse/nflverse-data (release tag `pbp`), "
        "data built by the nflverse team (nflfastR)",
        f"Fetched: {dt.date.today().isoformat()}",
        "License: CC BY 4.0 (nflverse-data org LICENSE.md). Requires attribution, "
        "a link to the license, and a note if the data is modified. This project "
        "attributes nflverse in README.md, docs/BUILD_PLAN.md and the site footer; "
        "play-by-play is aggregated to one row per team-game before anything is "
        "committed (see data/processed/team_game.csv).",
        f"Coverage: {min(counts)}-{max(counts)}, one parquet file per season.",
        "",
        "Row counts per season (raw plays, all game types):",
        "",
    ]
    for season in sorted(counts):
        lines.append(f"- {season}: {counts[season]:,}")
    if null_wp:
        lines += [
            "",
            "Plays per season with a null win probability (`wp`) - these are treated "
            "as garbage time (excluded) by xe_metrics.py's `_ng` non-garbage-time "
            "counters, since there is no probability to compare against [0.05, 0.95]:",
            "",
        ]
        for season in sorted(null_wp):
            lines.append(f"- {season}: {null_wp[season]:,} of {counts.get(season, 0):,}")
    lines += [
        "",
        "Notes:",
        "- Raw parquet files are NOT committed (data/raw/nflverse_pbp/*.parquet is "
        "gitignored); only the team-game aggregate is. Re-run "
        "`python src/xe_ingest.py --refresh` to re-download.",
        "- Team codes (posteam/defteam/home_team/away_team) are relocation-specific "
        "(e.g. STL vs LAR), mapped to franchise-stable codes via "
        "data/reference/franchise_crosswalk.csv in the main repo, same as the "
        "home-field-advantage study.",
    ]
    (RAW / "SOURCE.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true", help="re-download files already on disk")
    ap.add_argument("--first", type=int, default=FIRST_SEASON)
    ap.add_argument("--last", type=int, default=LAST_SEASON)
    args = ap.parse_args()

    counts = fetch_all(range(args.first, args.last + 1), refresh=args.refresh)
    null_wp = count_null_wp(range(args.first, args.last + 1))
    write_source_md(counts, null_wp)
    total = sum(counts.values())
    print(f"Fetched {len(counts)} seasons, {total:,} total plays.", file=sys.stderr)
    for season in sorted(counts):
        print(f"  {season}: {counts[season]:,}", file=sys.stderr)


if __name__ == "__main__":
    main()
