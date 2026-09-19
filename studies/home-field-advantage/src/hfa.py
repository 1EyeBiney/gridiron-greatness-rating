"""
Home-field advantage in the NFL, 1970-2025, from final scores only.

Everything here is built on one quantity: the *adjusted home margin*.
For each season, an ordinary-least-squares model fits every regular-season
game's margin as

    home_score - away_score = r_home - r_away + h * is_home_field

with one rating r per team (constrained to sum to zero) and one shared
home-field term h. The adjusted home margin of a game is then

    margin - (r_home - r_away)

i.e. how much the home team beat expectation by, before any home-field
credit. Averaging it over any group of games estimates the home-field
advantage for that group in points. Slicing the same number by season
phase, decade, roof type, or franchise is most of the analysis.

The playoff-race analysis needs one more step. A team's race status is
defined by its earlier results, so games grouped by status are selected
on outcomes, and a full-season rating is contaminated by exactly those
outcomes (a team picked for a bad start beats its full-season rating late
in the year almost by construction). For that analysis the status is
frozen entering a late-season window and ratings are refit on that
window's games alone, so the residuals carry no information about the
results that defined the status. See late_window().
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]          # studies/home-field-advantage
MAIN = REPO.parents[1]                                # the Gridiron Greatness repo root
RAW = REPO / "data" / "raw"                           # this study's own nflverse copy (roof, div flags, current season)
GAMES_CSV = MAIN / "data" / "processed" / "games.csv"  # the unified games table, built by the main pipeline
REF = MAIN / "data" / "reference"                     # conference table and franchise crosswalk
REPLACEMENT_FLAGS = MAIN / "data" / "processed" / "era_flags_1987_replacement_games.csv"
OUT = REPO / "data" / "processed"

PHASES = {1: "Early (first third)", 2: "Middle third", 3: "Late (final third)"}
LONGSHOT_GAMES_BACK = 3.0
EXCLUDED_SEASONS = {1982}  # strike season: 9 games, irregular schedule, 16-team tournament
GB_BINS = [-np.inf, -0.01, 0.99, 2.99, np.inf]
GB_LABELS = ["Holding a spot", "Within 1 game", "1 to 3 games back", "3+ games back"]


def playoff_spots_per_conference(season: int) -> int:
    """Playoff berths per conference by era."""
    if season <= 1977:
        return 4
    if season <= 1989:
        return 5
    if season <= 2019:
        return 6
    return 7


def decade_label(season: int) -> str:
    return f"{season // 10 * 10}s"


# ---------------------------------------------------------------- loading


def _assign_week_index(g: pd.DataFrame) -> pd.Series:
    """1, 2, 3, ... within one season's regular-season games. nflverse
    seasons carry a week column. Earlier seasons get weeks from the
    calendar: an NFL week runs Tuesday to Monday, so each game's week is
    the number of Tuesdays between the Tuesday on or before the season's
    first game and the game date. That places Thursday, Saturday, Sunday
    and Monday games of one slate in the same week."""
    if g["week"].notna().all():
        return g["week"].rank(method="dense").astype(int)
    dates = pd.to_datetime(g["date"])
    first = dates.min()
    anchor = first - pd.Timedelta(days=(first.weekday() - 1) % 7)  # Tuesday on/before first game
    return ((dates - anchor).dt.days // 7 + 1).astype(int)


def load_games() -> pd.DataFrame:
    """Regular-season games 1970-2025 (1982 excluded) with week index,
    season phase, conference of each side, and (1999+) roof / divisional
    flags. Neutral-site games are kept (they anchor ratings) but get no
    adjusted margin; the 1987 replacement games are dropped."""
    g = pd.read_csv(GAMES_CSV)
    g = g[(g["game_type"] == "REG") & ~g["season"].isin(EXCLUDED_SEASONS)].copy()
    replacement = set(pd.read_csv(REPLACEMENT_FLAGS)["game_uid"])
    g = g[~g["game_uid"].isin(replacement)].copy()

    g["week_index"] = 0
    for season, idx in g.groupby("season").groups.items():
        g.loc[idx, "week_index"] = _assign_week_index(g.loc[idx])
    g["n_weeks"] = g.groupby("season")["week_index"].transform("max")
    g["phase"] = np.ceil(3 * g["week_index"] / g["n_weeks"]).astype(int).clip(1, 3)

    conf = pd.read_csv(REF / "team_season_conference.csv")
    conf_map = conf.set_index(["season", "franchise"])["conference"]
    g["home_conf"] = pd.MultiIndex.from_frame(g[["season", "home_franchise"]]).map(conf_map)
    g["away_conf"] = pd.MultiIndex.from_frame(g[["season", "away_franchise"]]).map(conf_map)

    g = g.merge(_nflverse_extras(), on=["season", "date", "home_franchise", "away_franchise"], how="left")
    g["margin"] = g["home_score"] - g["away_score"]
    g["home_win"] = (g["margin"] > 0).astype(float)
    g.loc[g["margin"] == 0, "home_win"] = 0.5
    g["decade"] = g["season"].map(decade_label)
    g["phase_label"] = g["phase"].map(PHASES)
    return g.reset_index(drop=True)


def _nflverse_extras() -> pd.DataFrame:
    """roof and div_game per game, 1999+, keyed by season, date and the two
    franchise-stable codes (nflverse team codes mapped through the same
    crosswalk the unified table was built with)."""
    nv = pd.read_csv(RAW / "nflverse" / "games.csv")
    nv = nv[(nv["game_type"] == "REG") & nv["home_score"].notna()].copy()
    cw = pd.read_csv(REF / "franchise_crosswalk.csv")
    cw = cw[cw["source"] == "nflverse"]
    cw["valid_to_season"] = cw["valid_to_season"].fillna(9999)

    def to_franchise(code: str, season: int) -> str:
        hit = cw[(cw["source_code"] == code) & (cw["valid_from_season"] <= season) & (cw["valid_to_season"] >= season)]
        return hit["franchise_id"].iloc[0] if len(hit) else code

    nv["home_franchise"] = [to_franchise(c, s) for c, s in zip(nv["home_team"], nv["season"])]
    nv["away_franchise"] = [to_franchise(c, s) for c, s in zip(nv["away_team"], nv["season"])]
    nv["date"] = nv["gameday"]
    nv["indoor"] = nv["roof"].isin(["dome", "closed"]).astype(float)
    nv.loc[nv["roof"].isna(), "indoor"] = np.nan
    nv["div_game"] = nv["div_game"].astype(float)
    key = ["season", "date", "home_franchise", "away_franchise"]
    return nv.drop_duplicates(subset=key)[key + ["indoor", "div_game"]]


# ------------------------------------------------------------------ model


def fit_season(g: pd.DataFrame) -> dict:
    """OLS: margin = r_home - r_away + h * home_field, ratings sum to zero.
    Returns ratings (Series), h, its standard error, and the residual sd."""
    teams = sorted(set(g["home_franchise"]) | set(g["away_franchise"]))
    idx = {t: i for i, t in enumerate(teams)}
    n, k = len(g), len(teams)
    X = np.zeros((n + 1, k + 1))
    rows = np.arange(n)
    X[rows, g["home_franchise"].map(idx).to_numpy()] = 1.0
    X[rows, g["away_franchise"].map(idx).to_numpy()] = -1.0
    X[rows, k] = (~g["neutral_site"].to_numpy(bool)).astype(float)
    X[n, :k] = 1.0  # sum-to-zero constraint row
    y = np.append(g["margin"].to_numpy(float), 0.0)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y[:n] - X[:n] @ beta
    dof = max(n - k, 1)  # k-1 free ratings + 1 home term
    sigma2 = float(resid @ resid / dof)
    cov = sigma2 * np.linalg.pinv(X[:n].T @ X[:n])
    return {
        "ratings": pd.Series(beta[:k], index=teams),
        "home_adv": float(beta[k]),
        "home_adv_se": float(np.sqrt(cov[k, k])),
        "sigma": float(np.sqrt(sigma2)),
        "n_games": n,
        "dof": n - k,
    }


def adjusted_margin(g: pd.DataFrame, ratings: pd.Series) -> pd.Series:
    adj = g["margin"] - (g["home_franchise"].map(ratings) - g["away_franchise"].map(ratings))
    adj[g["neutral_site"].astype(bool)] = np.nan
    return adj


def add_adjusted_margins(g: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit every season on all its games; return games with adj_margin and
    a per-season table of the fits."""
    g = g.copy()
    g["adj_margin"] = np.nan
    fits = []
    for season, gs in g.groupby("season"):
        f = fit_season(gs)
        g.loc[gs.index, "adj_margin"] = adjusted_margin(gs, f["ratings"])
        fits.append({"season": season, "home_adv": f["home_adv"], "home_adv_se": f["home_adv_se"],
                     "sigma": f["sigma"], "n_games": f["n_games"]})
    return g, pd.DataFrame(fits)


def summarize(df: pd.DataFrame, by: list[str], col: str = "adj_margin") -> pd.DataFrame:
    """Mean adjusted home margin (= home-field advantage in points), its
    standard error, raw home win %, and game count for each group."""
    d = df[df[col].notna()]
    out = d.groupby(by, dropna=False, observed=True).agg(
        n=(col, "size"), hfa=(col, "mean"), sd=(col, "std"),
        home_win_pct=("home_win", "mean"), raw_margin=("margin", "mean"),
    ).reset_index()
    out["hfa_se"] = out["sd"] / np.sqrt(out["n"])
    return out.drop(columns="sd")


# ------------------------------------------------------------- contention


def playoff_race_status(g: pd.DataFrame) -> pd.DataFrame:
    """For every game, each side's standing entering that week:
    'clinched' (no more than spots-1 other conference teams can still match
    its point total), 'alive', 'longshot' (LONGSHOT_GAMES_BACK or more games
    behind the last playoff spot in its conference), or 'eliminated' (cannot
    reach the current point total of the last team holding a spot). All of
    it ignores tiebreakers; ties count half a win; regular season only.
    Also records games_back (negative = holding a spot by that margin)."""
    out_home = pd.Series("alive", index=g.index, dtype=object)
    out_away = out_home.copy()
    gb_home = pd.Series(np.nan, index=g.index)
    gb_away = pd.Series(np.nan, index=g.index)
    for season, gs in g.groupby("season"):
        spots = playoff_spots_per_conference(season)
        teams = sorted(set(gs["home_franchise"]) | set(gs["away_franchise"]))
        conf = {}
        for h, a, hc, ac in zip(gs["home_franchise"], gs["away_franchise"], gs["home_conf"], gs["away_conf"]):
            conf[h] = hc
            conf[a] = ac
        total_games = {t: int(((gs["home_franchise"] == t) | (gs["away_franchise"] == t)).sum()) for t in teams}
        points = {t: 0.0 for t in teams}
        played = {t: 0 for t in teams}
        for week, gw in gs.sort_values("week_index").groupby("week_index"):
            status, gback = {}, {}
            for c in set(conf.values()):
                members = [t for t in teams if conf[t] == c]
                for t in members:
                    others = sorted((points[o] for o in members if o != t), reverse=True)
                    threshold = others[spots - 1] if len(others) >= spots else -np.inf
                    remaining = total_games[t] - played[t]
                    gb = threshold - points[t]
                    gback[t] = gb
                    can_catch = sum(points[o] + (total_games[o] - played[o]) >= points[t]
                                    for o in members if o != t)
                    if points[t] + remaining < threshold:
                        status[t] = "eliminated"
                    elif can_catch <= spots - 1:
                        status[t] = "clinched"
                    elif gb >= LONGSHOT_GAMES_BACK:
                        status[t] = "longshot"
                    else:
                        status[t] = "alive"
            out_home.loc[gw.index] = gw["home_franchise"].map(status)
            out_away.loc[gw.index] = gw["away_franchise"].map(status)
            gb_home.loc[gw.index] = gw["home_franchise"].map(gback)
            gb_away.loc[gw.index] = gw["away_franchise"].map(gback)
            for h, a, m in zip(gw["home_franchise"], gw["away_franchise"], gw["margin"]):
                played[h] += 1
                played[a] += 1
                if m > 0:
                    points[h] += 1
                elif m < 0:
                    points[a] += 1
                else:
                    points[h] += 0.5
                    points[a] += 0.5
    g = g.copy()
    g["home_status"] = out_home
    g["away_status"] = out_away
    g["home_games_back"] = gb_home
    g["away_games_back"] = gb_away
    return g


def late_window(g: pd.DataFrame, last_weeks: int | None = None) -> pd.DataFrame:
    """Games in a late-season window with (a) adj_margin_late from ratings
    fit on the window's games only and (b) each side's race status and
    games-back frozen at the start of the window. last_weeks=None uses the
    final third of the season; an integer uses the last that many weeks.
    Requires playoff_race_status() to have run."""
    frames = []
    for season, gs in g.groupby("season"):
        n_weeks = int(gs["n_weeks"].iloc[0])
        start = int(gs.loc[gs["phase"] == 3, "week_index"].min()) if last_weeks is None else n_weeks - last_weeks + 1
        w = gs[gs["week_index"] >= start].copy()
        w["adj_margin_late"] = adjusted_margin(w, fit_season(w)["ratings"])
        frozen = {}
        for _, row in w.sort_values("week_index").iterrows():
            for side in ("home", "away"):
                frozen.setdefault(row[f"{side}_franchise"], (row[f"{side}_status"], row[f"{side}_games_back"]))
        for side in ("home", "away"):
            w[f"{side}_status_frozen"] = w[f"{side}_franchise"].map(lambda t: frozen[t][0])
            w[f"{side}_games_back_frozen"] = w[f"{side}_franchise"].map(lambda t: frozen[t][1])
            w[f"{side}_gb_frozen"] = pd.cut(w[f"{side}_games_back_frozen"], GB_BINS, labels=GB_LABELS)
        frames.append(w)
    return pd.concat(frames, ignore_index=True)


def contention_summary(late: pd.DataFrame, by: str = "status") -> pd.DataFrame:
    """Home-field advantage in a late-season window by a team's frozen
    status (or games-back bin): as host, as visitor, and across every game
    involving such a team. Only the last is cleanly identified from scores
    (see the methodology page); the first two are shown so the reader can
    see the model spreading any host effect across both roles."""
    col_h, col_a = f"home_{by}_frozen", f"away_{by}_frozen"
    d = late[late["adj_margin_late"].notna()]
    rows = []
    levels = sorted(set(d[col_h].dropna()) | set(d[col_a].dropna()), key=str)
    for level in levels:
        host = d[d[col_h] == level]
        visitor = d[d[col_a] == level]
        both = d[(d[col_h] == level) | (d[col_a] == level)]
        rows.append({
            by: level,
            "n_as_host": len(host), "hfa_as_host": host["adj_margin_late"].mean(),
            "home_win_pct_as_host": host["home_win"].mean(),
            "n_as_visitor": len(visitor), "hfa_as_visitor": visitor["adj_margin_late"].mean(),
            "n_all": len(both), "hfa_all": both["adj_margin_late"].mean(),
            "hfa_all_se": both["adj_margin_late"].std() / np.sqrt(max(len(both), 1)),
        })
    return pd.DataFrame(rows)


# -------------------------------------------------------------- franchise


def franchise_swing(g: pd.DataFrame, first: int | None = None, last: int | None = None) -> pd.DataFrame:
    """Each franchise's average adjusted margin at home and on the road
    (from its own point of view), and the swing between them. The league
    average swing is twice the league home-field advantage. A small swing
    means a team plays nearly as well away as at home."""
    d = g[g["adj_margin"].notna()]
    if first is not None:
        d = d[(d["season"] >= first) & (d["season"] <= last)]
    home = d[["season", "home_franchise", "adj_margin"]].rename(columns={"home_franchise": "franchise"})
    away = d[["season", "away_franchise", "adj_margin"]].rename(columns={"away_franchise": "franchise"})
    away["adj_margin"] = -away["adj_margin"]
    both = pd.concat([home, away])
    h = home.groupby("franchise")["adj_margin"].agg(["mean", "var", "size"])
    a = away.groupby("franchise")["adj_margin"].agg(["mean", "var", "size"])
    out = pd.DataFrame({
        "seasons": both.groupby("franchise")["season"].nunique(),
        "home_games": h["size"], "home_adj_margin": h["mean"],
        "road_games": a["size"], "road_adj_margin": a["mean"],
    })
    out["swing"] = out["home_adj_margin"] - out["road_adj_margin"]
    out["swing_se"] = np.sqrt(h["var"] / h["size"] + a["var"] / a["size"])
    league = 2 * d["adj_margin"].mean()
    out["swing_vs_league"] = out["swing"] - league
    out["z"] = out["swing_vs_league"] / out["swing_se"]
    return out.reset_index().sort_values("swing").reset_index(drop=True)


# -------------------------------------------------------------- pipeline


def current_season_note() -> dict:
    nv = pd.read_csv(RAW / "nflverse" / "games.csv")
    latest = int(nv["season"].max())
    c = nv[(nv["season"] == latest) & (nv["game_type"] == "REG") & nv["home_score"].notna()
           & (nv["location"] == "Home")]
    return {
        "season": latest, "games": int(len(c)),
        "home_wins": int((c["home_score"] > c["away_score"]).sum()),
        "ties": int((c["home_score"] == c["away_score"]).sum()),
        "weeks": int(c["week"].max()) if len(c) else 0,
        "mean_margin": float((c["home_score"] - c["away_score"]).mean()) if len(c) else float("nan"),
    }


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in list(OUT.glob("*.csv")) + list(OUT.glob("*.json")):
        stale.unlink()  # every table is regenerated; nothing from an earlier run survives
    g = load_games()
    g, fits = add_adjusted_margins(g)
    g = playoff_race_status(g)
    g.to_csv(OUT / "games_adjusted.csv", index=False)

    t = {}
    by_season = summarize(g, ["season"]).merge(fits[["season", "home_adv", "home_adv_se", "sigma"]], on="season")
    phase_wide = summarize(g, ["season", "phase"]).pivot(index="season", columns="phase", values="hfa")
    phase_wide.columns = [f"hfa_phase{c}" for c in phase_wide.columns]
    t["by_season"] = by_season.merge(phase_wide.reset_index(), on="season")
    t["by_decade_phase"] = summarize(g, ["decade", "phase"])
    t["by_decade"] = summarize(g, ["decade"])
    t["by_phase"] = summarize(g, ["phase"])
    t["by_week_1999"] = summarize(g[g["season"] >= 1999], ["week_index"])
    t["final_week_vs_rest"] = summarize(
        g.assign(final=np.where(g["week_index"] == g["n_weeks"], "Final week", "Weeks before")), ["final"])

    # Playoff race: two windows, status frozen at window start, ratings from window games only.
    t["contention_late_naive"] = summarize(g[g["phase"] == 3], ["home_status"])
    third = late_window(g)
    last3 = late_window(g, last_weeks=3)
    t["contention_third"] = contention_summary(third, "status")
    t["contention_third_games_back"] = contention_summary(third, "gb")
    t["contention_last3"] = contention_summary(last3, "status")
    t["contention_last3_games_back"] = contention_summary(last3, "gb")
    eras = []
    for label, lo, hi in [("1970-1989", 1970, 1989), ("1990-2009", 1990, 2009), ("2010-2025", 2010, 2025)]:
        e = contention_summary(last3[last3["season"].between(lo, hi)], "status")
        e.insert(0, "era", label)
        eras.append(e)
    t["contention_last3_by_era"] = pd.concat(eras, ignore_index=True)

    modern = g[g["season"] >= 1999]
    t["roof_phase"] = summarize(modern[modern["indoor"].notna()], ["indoor", "phase"])
    t["division_phase"] = summarize(modern[modern["div_game"].notna()], ["div_game", "phase"])
    recent = g[g["season"].between(2015, 2025)].copy()
    recent["window"] = np.select([recent["season"] < 2020, recent["season"] == 2020],
                                 ["2015-2019", "2020 (limited or no fans)"], "2021-2025")
    t["covid"] = summarize(recent, ["window"])
    t["franchise_swing"] = franchise_swing(g)
    t["franchise_swing_2000_2025"] = franchise_swing(g, 2000, 2025)
    t["franchise_swing_1970_1999"] = franchise_swing(g, 1970, 1999)
    for name, tab in t.items():
        tab.to_csv(OUT / f"{name}.csv", index=False)

    note = current_season_note()
    with open(OUT / "current_season.json", "w") as f:
        json.dump(note, f, indent=2)
    return {"games": g, "tables": t, "current": note, "third": third, "last3": last3}


if __name__ == "__main__":
    res = run()
    pd.set_option("display.width", 220)
    for k in ["by_decade", "by_phase", "by_decade_phase", "final_week_vs_rest", "contention_late_naive",
              "contention_third", "contention_third_games_back", "contention_last3", "contention_last3_games_back",
              "contention_last3_by_era", "roof_phase", "division_phase", "covid"]:
        print(f"\n== {k}")
        print(res["tables"][k].round(2).to_string(index=False))
    print("\n== franchise swing (all)")
    print(res["tables"]["franchise_swing"].round(2).to_string(index=False))
    print("\n== current")
    print(res["current"])
    print(res["games"].groupby("season")["n_weeks"].first().value_counts().sort_index().to_dict())
