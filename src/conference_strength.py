"""
Conference Strength Index (CSI), BUILD_PLAN section 3: "The estimated
difference in average team strength between the two conferences in a
given season, derived from the network model (interconference games are
the informative edges). Reported with an uncertainty range because each
team plays only a few interconference games."

CSI = mean(AFC team ratings) - mean(NFC team ratings), positive means the
AFC was stronger that season. Since the locked model (Bayesian
hierarchical margin, BUILD_PLAN section 2 item 9) already fits every
team's rating jointly from every game that season - inter- and
intra-conference alike - this is a direct read of the fitted ratings:
intra-conference games pin down each team's rating *relative to its own
conference*, and interconference games are the only games that can pin
down the two conferences' relative *levels*, which is exactly the
BUILD_PLAN language above.

The uncertainty range comes from the same posterior the ratings
themselves come from, not a separate calculation: CSI is a linear
contrast of the fitted rating vector (mean of one group of coefficients
minus the mean of another), so its variance follows the standard formula
for a linear combination of jointly-normal parameters,
Var(w'beta) = sigma^2 * w' Cov_unscaled w, using the same
beta_cov_unscaled models.bayesian_margin.fit_bayesian_margin returns for
predictive_sigma. This naturally widens in a season with few
interconference games or lopsided conference sizes (pre-1970 is out of
scope; 1976/1995/1999 expansion seasons briefly had uneven conference
sizes here too), without needing to special-case any of that.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from division_alignment import build_team_season_conference_table
from models.bayesian_margin import fit_bayesian_margin
from models.common import load_games, season_games

REPO = Path(__file__).resolve().parents[1]


def compute_csi_for_season(g: pd.DataFrame, conference_by_team: dict) -> dict:
    fit = fit_bayesian_margin(g)
    idx = fit["team_index"]
    teams = list(idx.keys())
    n_teams = len(teams)

    afc = np.array([conference_by_team[t] == "AFC" for t in teams])
    nfc = ~afc
    n_afc, n_nfc = int(afc.sum()), int(nfc.sum())

    w_teams = afc / n_afc - nfc / n_nfc
    w = np.zeros(fit["beta_cov_unscaled"].shape[0])
    w[:n_teams] = w_teams

    beta_full = np.zeros_like(w)
    beta_full[:n_teams] = fit["ratings"].reindex(teams).to_numpy()

    csi = float(w @ beta_full)
    variance = float(fit["sigma"] ** 2 * (w @ fit["beta_cov_unscaled"] @ w))
    se = float(np.sqrt(max(variance, 0.0)))

    z = norm.ppf(0.975)
    return {
        "csi": csi,
        "csi_se": se,
        "ci95_lower": csi - z * se,
        "ci95_upper": csi + z * se,
        "n_afc": n_afc,
        "n_nfc": n_nfc,
    }


def build_csi_table(seasons) -> pd.DataFrame:
    games = load_games()
    conf_table = build_team_season_conference_table(games)

    rows = []
    for season in seasons:
        g = season_games(games, season)
        conf_by_team = (
            conf_table[conf_table["season"] == season].set_index("franchise")["conference"].to_dict()
        )
        result = compute_csi_for_season(g, conf_by_team)
        result["season"] = season
        rows.append(result)
    return pd.DataFrame(rows)[["season", "csi", "csi_se", "ci95_lower", "ci95_upper", "n_afc", "n_nfc"]]


if __name__ == "__main__":
    table = build_csi_table(range(1970, 2026))
    out_path = REPO / "data" / "processed" / "conference_strength_index.csv"
    table.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(table)} rows)")
