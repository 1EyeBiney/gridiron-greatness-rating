"""
A continuous week index per season, spanning regular season and
postseason, used by src/walkforward.py to build a "games so far this
season" training window with zero future leakage.

For 1999-2025 (nflverse), the source's own `week` column is used
directly - it already numbers postseason rounds as a continuation of the
regular season (e.g. week 19 = Wild Card), so no reconstruction is
needed.

For 1970-1998 (FiveThirtyEight), there is no week column, so week
boundaries are inferred from date gaps: a new week starts wherever the
gap since the previous game is at least GAP_DAYS. That threshold cleanly
separates real week boundaries (>=5 days apart, since these seasons are
almost entirely Sunday games with an occasional Monday nightcap 1 day
later) from within-week gaps, EXCEPT during 1982's post-strike
catch-up schedule, which spread games across weekdays and does not follow
a normal weekly cadence - its inferred week boundaries (and, in one
case, 1970's) are approximate. This does not compromise walk-forward's
no-future-leakage property (a coarser week merges two real weeks into one
training step, it never lets a later game leak into an earlier one's
training data); it only means postseason round boundaries for 1970-1998
are approximate, the same known limitation already flagged in Phase 1 as
carried-forward, unfixed work (reconstructing exact playoff round labels).
"""
import pandas as pd

GAP_DAYS = 4


def assign_week_index(g: pd.DataFrame) -> pd.Series:
    """Week index (1, 2, 3, ...) for every game in g, which must already
    be a single season's games (see models.common.season_games)."""
    if g["week"].notna().all():
        return g["week"].rank(method="dense").astype(int)

    dates = pd.to_datetime(g["date"])
    unique_dates = sorted(dates.unique())
    week_of_date = {}
    week = 1
    for i, d in enumerate(unique_dates):
        if i > 0 and (d - unique_dates[i - 1]).days >= GAP_DAYS:
            week += 1
        week_of_date[d] = week
    return dates.map(week_of_date)
