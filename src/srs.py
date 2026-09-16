"""
Simple Rating System (SRS), computed to match Pro Football Reference's
published methodology: regular-season games only, no home-field
adjustment, no margin capping. This is a VALIDATION tool (proves our game
data and computation are clean) - not the project's final True Strength
model, which will use all games including playoffs (see docs/BUILD_PLAN.md
section 5).

SRS solves, for every team i with n_i regular-season games:
    r_i = MoV_i + mean(r_j for each opponent j, one term per game)
which is a linear system r = MoV + M @ r, where M_ij = (# games i played
against j) / n_i. Solved via least squares with an added mean-zero
constraint (the raw system has a 1-dimensional null space along the
all-ones vector, since ratings are only defined up to an additive
constant; PFR's convention is that the league-average team is 0).
"""
import numpy as np
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def compute_srs(games: pd.DataFrame, season: int) -> pd.Series:
    reg = games[(games["season"] == season) & (games["game_type"] == "REG")].copy()
    teams = sorted(set(reg["home_franchise"]).union(set(reg["away_franchise"])))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    mov_sum = np.zeros(n)
    games_played = np.zeros(n)
    M = np.zeros((n, n))  # M[i, j] = count of games between i and j

    for _, row in reg.iterrows():
        hi, ai = idx[row["home_franchise"]], idx[row["away_franchise"]]
        margin = row["home_score"] - row["away_score"]
        mov_sum[hi] += margin
        mov_sum[ai] += -margin
        games_played[hi] += 1
        games_played[ai] += 1
        M[hi, ai] += 1
        M[ai, hi] += 1

    mov = mov_sum / games_played
    M_norm = M / games_played[:, None]

    A = np.eye(n) - M_norm
    b = mov

    # Add mean-zero constraint row to pin the unique solution (the system
    # r = mov + M_norm @ r has a 1-D null space along the all-ones vector).
    A_aug = np.vstack([A, np.ones((1, n))])
    b_aug = np.append(b, 0.0)

    r, *_ = np.linalg.lstsq(A_aug, b_aug, rcond=None)

    return pd.Series(r, index=teams).sort_values(ascending=False), pd.Series(mov, index=teams)


if __name__ == "__main__":
    games = pd.read_csv(REPO / "data" / "processed" / "games.csv")
    for season in [1975, 1985, 1995, 2005, 2015]:
        srs, mov = compute_srs(games, season)
        print(f"\n=== {season} ===")
        print(srs.round(1))
