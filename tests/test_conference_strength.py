import numpy as np
import pandas as pd

from conference_strength import compute_csi_for_season


def _round_robin(strengths, rounds, seed=0):
    teams = list(strengths)
    rng = np.random.default_rng(seed)
    rows = []
    for rnd in range(rounds):
        for i, a in enumerate(teams):
            for b in teams[i + 1 :]:
                home, away = (a, b) if rnd % 2 == 0 else (b, a)
                margin = strengths[home] - strengths[away] + rng.normal(0, 3.0)
                rows.append({"home_franchise": home, "away_franchise": away, "margin": margin, "neutral_site": True})
    return pd.DataFrame(rows)


def test_csi_detects_a_systematically_stronger_conference():
    # AFC teams (A, B) strong; NFC teams (C, D) weak.
    strengths = {"A": 8.0, "B": 6.0, "C": -6.0, "D": -8.0}
    conf = {"A": "AFC", "B": "AFC", "C": "NFC", "D": "NFC"}
    g = _round_robin(strengths, rounds=6, seed=1)
    result = compute_csi_for_season(g, conf)
    assert result["csi"] > 5.0
    assert result["ci95_lower"] > 0  # confident interval excludes zero


def test_csi_is_near_zero_for_evenly_matched_conferences():
    strengths = {"A": 5.0, "B": -5.0, "C": 5.0, "D": -5.0}
    conf = {"A": "AFC", "B": "AFC", "C": "NFC", "D": "NFC"}
    g = _round_robin(strengths, rounds=6, seed=2)
    result = compute_csi_for_season(g, conf)
    assert abs(result["csi"]) < 3.0
    assert result["ci95_lower"] < 0 < result["ci95_upper"]
