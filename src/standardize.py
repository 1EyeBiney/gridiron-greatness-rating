"""
BUILD_PLAN section 5: convert each season's raw ratings to z-scores using
that season's own mean and standard deviation across all teams, so
seasons of any length, any team count, and any scoring era can be
compared. The z-score is the canonical cross-era value; an optional
0-100 display scale is provided only for presentation.

This is deliberately model-agnostic: it is applied to every candidate
model's ratings (Massey, Bradley-Terry, Bayesian, and Elo, which is a
comparator only but standardized the same way for consistency), because
Phase 4, not this script, decides which model's ratings become the
project's headline True Strength Rating.
"""
import numpy as np
import pandas as pd

RATING_COLUMNS = ["massey_rating", "bt_rating", "bayes_rating", "elo_rating"]


def zscore_within_season(df: pd.DataFrame, columns=RATING_COLUMNS, season_col: str = "season") -> pd.DataFrame:
    """Adds a '<col>_z' column for each rating column: (value - season
    mean) / season standard deviation, computed separately per season."""
    out = df.copy()
    for col in columns:
        grouped = out.groupby(season_col)[col]
        mean = grouped.transform("mean")
        # ddof=0 (population sd): every team that season is the whole
        # population, not a sample of some larger one - pandas' default
        # ddof=1 would be the wrong convention here.
        std = grouped.transform(lambda s: s.std(ddof=0))
        out[f"{col}_z"] = np.where(std > 0, (out[col] - mean) / std, 0.0)
    return out


def display_scale(z: pd.Series, center: float = 50.0, spread: float = 10.0) -> pd.Series:
    """Optional 0-100 presentation scale (BUILD_PLAN section 5): z=0 maps
    to `center`, one standard deviation maps to `center +/- spread`,
    clipped to [0, 100]. The z-score itself remains canonical."""
    return (center + spread * z).clip(0, 100)


def add_display_scales(df: pd.DataFrame, columns=RATING_COLUMNS) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        out[f"{col}_display"] = display_scale(out[f"{col}_z"])
    return out
