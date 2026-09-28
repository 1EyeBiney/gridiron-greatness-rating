"""The Playcallers: case files.

A career rank is one number. For some coaches it needs explaining: the
reputation is better than the rank, or the rank rests on one stop, or on
one quarterback. Each case file shows a coach's record stop by stop and
says, in a few sentences, what the record does and does not support.

Numbers in the prose are injected from `case_facts`; the claims built on
them are pinned in tests/test_pc_case_files.py. Built only from the
committed tables (playcaller_seasons, playcaller_careers,
playcaller_qb_adjusted, playcaller_excluded_unit_seasons).
"""
from __future__ import annotations

import pandas as pd

RECENT_FROM = 2019          # "current form" window: 2019 to the last season
RECENT_MIN_SEASONS = 4

TEAM_NAMES = {
    "ARI": "Arizona", "ATL": "Atlanta", "BAL": "Baltimore", "BUF": "Buffalo", "CAR": "Carolina", "CHI": "Chicago",
    "CIN": "Cincinnati", "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver", "DET": "Detroit", "GB": "Green Bay",
    "HOU": "Houston", "IND": "Indianapolis", "JAX": "Jacksonville", "KC": "Kansas City", "LAC": "Chargers",
    "LAR": "Rams", "MIA": "Miami", "MIN": "Minnesota", "NE": "New England", "NO": "New Orleans", "NYG": "Giants",
    "NYJ": "Jets", "OAK": "Raiders", "PHI": "Philadelphia", "PIT": "Pittsburgh", "SEA": "Seattle",
    "SF": "San Francisco", "TB": "Tampa Bay", "TEN": "Tennessee", "WSH": "Washington",
}

# category, shown as a label on the index
BETTER = "Better than his rank"
ONE_STOP = "One great stop"
QUARTERBACK = "The quarterback question"
TRAVELLED = "A record that travelled"
REPUTATION = "Reputation and record disagree"
PROMPTED = "The two who prompted the study"

CASES = [
    {
        "slug": "kyle-shanahan", "person": "Kyle Shanahan", "unit": "offense", "category": BETTER,
        "verdict": "Ranked {{ k.career.rank }} for his career and {{ k.recent.rank }} since {{ k.recent_from }}. The career number is weighed down by his first years as a coordinator.",
        "body": [
            "Most people who follow the league would put Kyle Shanahan among the best play callers working. The career list has him {{ k.career.rank }} of {{ k.n_ranked }}. Both can be true, and the season table shows how.",
            "His first {{ k.early.n }} rated seasons, in Washington, Cleveland and his first year in Atlanta, averaged {{ k.early.mean|f2 }}: below the league, with Donovan McNabb, Rex Grossman and Brian Hoyer among the quarterbacks. Since {{ k.recent_from }} his offenses average {{ k.recent.mean|f2 }}, which ranks {{ k.recent.rank }} of the {{ k.recent.of }} callers with at least {{ k.recent_min }} seasons in that span. A career average counts 2011 as heavily as 2023.",
            "Two more things favour him. He has produced with {{ k.n_qbs }} different primary quarterbacks, more than almost anyone near the top of the list, and once quarterbacks are accounted for he ranks {{ k.qb_rank }}. And his offenses are better at what he is known for than at the study's main measure: they rank higher on explosive plays and yards per play than on efficiency per play, which is dragged down by sacks and turnovers.",
        ],
    },
    {
        "slug": "sean-mcvay", "person": "Sean McVay", "unit": "offense", "category": BETTER,
        "verdict": "Ranked {{ k.career.rank }} on the career list and {{ k.qb_rank }} once quarterbacks are accounted for.",
        "body": [
            "Sean McVay's Rams offenses average {{ k.stop.LAR.mean|f2 }} over {{ k.stop.LAR.n }} seasons, good and consistent but short of the very top of the list, where the offenses of Manning, Brady, Brees and Mahomes sit.",
            "His three seasons as Washington's coordinator average {{ k.stop.WSH.mean|f2 }}. Those are credited to him by title; the head coach there had an offensive background, and who called which plays is not something this study can confirm.",
            "He moves up to {{ k.qb_rank }} on the quarterback-adjusted list, having produced with Jared Goff and with Matthew Stafford.",
        ],
    },
    {
        "slug": "andy-reid", "person": "Andy Reid", "unit": "offense", "category": QUARTERBACK,
        "verdict": "Ranked {{ k.career.rank }}. His Kansas City offenses average {{ k.stop.KC.mean|f2 }}; his rated Philadelphia offenses average {{ k.stop.PHI.mean|f2 }}.",
        "body": [
            "Andy Reid's record splits in two. In Philadelphia, in the seasons where he is believed to have called the plays himself, his offenses were league average ({{ k.stop.PHI.mean|f2 }} over {{ k.stop.PHI.n }} seasons). In Kansas City they have been among the best in the league ({{ k.stop.KC.mean|f2 }} over {{ k.stop.KC.n }}).",
            "Kansas City includes the Patrick Mahomes years, and no measure built on results can fully separate the two men. But Reid's Kansas City offenses were already good with Alex Smith, and he ranks {{ k.qb_rank }} after the quarterback adjustment, so the record is not only Mahomes.",
            "Every one of his seasons is a belief that he called the plays, not a documented fact. His later Philadelphia seasons are credited to his coordinator and do not appear here.",
        ],
    },
    {
        "slug": "sean-payton", "person": "Sean Payton", "unit": "offense", "category": QUARTERBACK,
        "verdict": "Ranked {{ k.career.rank }}, on the strength of New Orleans ({{ k.stop.NO.mean|f2 }}). Denver so far: {{ k.stop.DEN.mean|f2 }}.",
        "body": [
            "Sean Payton's {{ k.stop.NO.n }} rated seasons in New Orleans average {{ k.stop.NO.mean|f2 }}, nearly all of them with Drew Brees. His three seasons as the Giants' coordinator average {{ k.stop.NYG.mean|f2 }} and his three in Denver {{ k.stop.DEN.mean|f2 }}.",
            "That is why he falls from {{ k.career.rank }} to {{ k.qb_rank }} when quarterbacks are accounted for. The model cannot tell how much of New Orleans was Payton and how much was Brees, and the seasons without Brees have been ordinary. Denver is the test, and it is still early.",
        ],
    },
    {
        "slug": "josh-mcdaniels", "person": "Josh McDaniels", "unit": "offense", "category": QUARTERBACK,
        "verdict": "Ranked {{ k.career.rank }}. New England: {{ k.ne.mean|f2 }} over {{ k.ne.n }} seasons. Everywhere else: {{ k.elsewhere.mean|f2 }} over {{ k.elsewhere.n }}.",
        "body": [
            "Josh McDaniels has one of the best records on the list and almost all of it was made in New England, most of it with Tom Brady. His {{ k.ne.n }} New England seasons average {{ k.ne.mean|f2 }}. His {{ k.elsewhere.n }} rated seasons elsewhere, with the Rams and the Raiders, average {{ k.elsewhere.mean|f2 }}.",
            "Two seasons is too few to call the rest of his record poor, and his seasons as Denver's head coach are not rated here because a coordinator held the title. What can be said is that his record has not yet been repeated away from New England. His 2025 return there, with a young quarterback, scored {{ k.last.z|f2 }}.",
        ],
    },
    {
        "slug": "tom-moore", "person": "Tom Moore", "unit": "offense", "category": QUARTERBACK,
        "verdict": "Ranked {{ k.career.rank }}, with one team and one quarterback.",
        "body": [
            "Tom Moore tops the career list: {{ k.career.seasons }} seasons with Indianapolis averaging {{ k.career.mean|f2 }}. Every one of them was with Peyton Manning, who is widely understood to have run much of that offense at the line of scrimmage.",
            "The study cannot divide the credit. Moore held the job the whole time, the offense was the best in football over that stretch, and the two never worked apart in the years covered. He is first on the list because the list measures results; what it says about play calling in his case is limited.",
            "Three of his seasons, 2003 to 2005, are filled in by assumption: the team's pages list no coordinator for those years, and he held the job before and after.",
        ],
    },
    {
        "slug": "mike-martz", "person": "Mike Martz", "unit": "offense", "category": ONE_STOP,
        "verdict": "Rams: {{ k.stop.LAR.mean|f2 }}. Detroit and Chicago afterwards: {{ k.after.mean|f2 }}.",
        "body": [
            "Mike Martz ran the offense known as the Greatest Show on Turf, and his Rams seasons average {{ k.stop.LAR.mean|f2 }} over {{ k.stop.LAR.n }} years. After St. Louis he was a coordinator in Detroit and Chicago, where his offenses averaged {{ k.after.mean|f2 }} over {{ k.after.n }} rated seasons.",
            "That leaves him {{ k.career.rank }} on the career list. He does better, {{ k.qb_rank }}, once quarterbacks are accounted for, because Jon Kitna and Jay Cutler were not Kurt Warner. His record says the scheme was formidable with the right players and did not make ordinary offenses good.",
        ],
    },
    {
        "slug": "mike-mccarthy", "person": "Mike McCarthy", "unit": "offense", "category": ONE_STOP,
        "verdict": "Green Bay: {{ k.stop.GB.mean|f2 }}. Every other stop combined: {{ k.elsewhere.mean|f2 }}.",
        "body": [
            "Mike McCarthy's Green Bay offenses, with Brett Favre and then Aaron Rodgers, average {{ k.stop.GB.mean|f2 }} over {{ k.stop.GB.n }} rated seasons. His other {{ k.elsewhere.n }} seasons, as coordinator in New Orleans and San Francisco and as head coach in Dallas, average {{ k.elsewhere.mean|f2 }}.",
            "He ranks {{ k.career.rank }} for his career and {{ k.qb_rank }} after the quarterback adjustment. Most of his seasons rest on the belief that he called his own plays as a head coach.",
        ],
    },
    {
        "slug": "jon-gruden", "person": "Jon Gruden", "unit": "offense", "category": REPUTATION,
        "verdict": "Ranked {{ k.career.rank }}. Oakland, first time: {{ k.first_stop.mean|f2 }}. Tampa Bay: {{ k.stop.TB.mean|f2 }}.",
        "body": [
            "Jon Gruden's reputation as an offensive mind was made in Oakland, where his offenses with Rich Gannon averaged {{ k.first_stop.mean|f2 }} over {{ k.first_stop.n }} seasons. In Tampa Bay, where he won a Super Bowl, his offenses averaged {{ k.stop.TB.mean|f2 }} over {{ k.stop.TB.n }} seasons and started five different primary quarterbacks.",
            "That championship was won by one of the best defenses of the era, which the main site rates as the best of any champion. Gruden's offensive record there was below average, and his return to the Raiders was average ({{ k.last_stop.mean|f2 }}).",
        ],
    },
    {
        "slug": "ben-johnson", "person": "Ben Johnson", "unit": "offense", "category": PROMPTED,
        "verdict": "Ranked {{ k.career.rank }} after four seasons. His average is {{ k.mean_rank|ordinal }} of the {{ k.n_ranked }} ranked offensive callers.",
        "body": [
            "Ben Johnson's three Detroit offenses scored {{ k.stop.DET.mean|f2 }} on average and improved each year. In his first season as Chicago's head coach, calling plays for a second-year quarterback, the offense scored {{ k.stop.CHI.mean|f2 }}.",
            "Four seasons is a short record, which is why his career rating ({{ k.career.rating|f2 }}) is well below his average ({{ k.career.mean|f2 }}). He has now produced a good offense with two teams and two quarterbacks, which is the pattern this study was built to look for.",
        ],
    },
    {
        "slug": "gus-bradley", "person": "Gus Bradley", "unit": "defense", "category": REPUTATION,
        "verdict": "Ranked {{ k.career.rank }} of {{ k.n_ranked }}. Seattle: {{ k.stop.SEA.mean|f2 }}. Everything since: {{ k.after.mean|f2 }}.",
        "body": [
            "Gus Bradley is remembered as the coordinator of the Seattle defense that became the Legion of Boom. His four Seattle seasons tell a story in two halves: the first two were well below average ({{ k.first_two.mean|f2 }}), the last two were good ({{ k.last_two_of_first.mean|f2 }}). He left after 2012. Seattle's defense was better still in the two seasons after he left, under Dan Quinn.",
            "Since Seattle his rated defenses, with the Chargers and Indianapolis, average {{ k.after.mean|f2 }} over {{ k.after.n }} seasons: two good years with the Chargers, then four below average. His years as Jacksonville's head coach are not rated here because a coordinator held the title, and two more seasons are left out because the head coach changed during the year.",
            "His record fits the reading that he coached a rising defense in Seattle more than he created one. It is a reading, not a finding: the head coach there came from the defensive side too, and the players were exceptional.",
        ],
    },
    {
        "slug": "dan-quinn", "person": "Dan Quinn", "unit": "defense", "category": ONE_STOP,
        "verdict": "Seattle: {{ k.stop.SEA.mean|f2 }}. Atlanta: {{ k.stop.ATL.mean|f2 }}. Dallas: {{ k.stop.DAL.mean|f2 }}.",
        "body": [
            "Dan Quinn inherited the Seattle defense at its peak and his two seasons there average {{ k.stop.SEA.mean|f2 }}, the highest of any defensive stop of two or more seasons in the study. As Atlanta's head coach, where he is believed to have run the defense, the average was {{ k.stop.ATL.mean|f2 }} over {{ k.stop.ATL.n }} seasons.",
            "What separates him from Gus Bradley is what came next. As Dallas's coordinator his defenses averaged {{ k.stop.DAL.mean|f2 }} over {{ k.stop.DAL.n }} seasons, a second excellent stop with different players. His Atlanta seasons are a belief about who called the defense, and the record looks better if they belong to someone else.",
        ],
    },
    {
        "slug": "vic-fangio", "person": "Vic Fangio", "unit": "defense", "category": BETTER,
        "verdict": "Ranked {{ k.career.rank }} over {{ k.career.seasons }} seasons. Since 2011: {{ k.since2011.mean|f2 }}. Before: {{ k.before2011.mean|f2 }}.",
        "body": [
            "Vic Fangio has the longest record in the study, {{ k.career.seasons }} rated seasons with {{ k.n_stops }} teams. His first seven, with Indianapolis and the expansion Texans, average {{ k.before2011.mean|f2 }}. Everything since 2011 averages {{ k.since2011.mean|f2 }}.",
            "San Francisco ({{ k.stop.SF.mean|f2 }}) and Philadelphia ({{ k.stop.PHI.mean|f2 }}) are among the best stops on the defensive list, and the scheme he is known for has been copied across the league. The career rank, like Kyle Shanahan's, counts the early years as heavily as the late ones.",
        ],
    },
    {
        "slug": "steve-spagnuolo", "person": "Steve Spagnuolo", "unit": "defense", "category": REPUTATION,
        "verdict": "Ranked {{ k.career.rank }}. The study rates the regular season only, and his reputation was made in January and February.",
        "body": [
            "Steve Spagnuolo has coordinated four Super Bowl winners. His regular-season defenses average {{ k.career.mean|f2 }}: {{ k.stop.NYG.mean|f2 }} with the Giants and {{ k.stop.KC.mean|f2 }} with Kansas City.",
            "This is a limit of the study more than a verdict on the coach. Ratings here are built from regular-season games, and a coordinator whose defenses play their best in the playoffs gets no credit for it. His years as the Rams' head coach are not rated.",
        ],
    },
    {
        "slug": "dick-lebeau", "person": "Dick LeBeau", "unit": "defense", "category": ONE_STOP,
        "verdict": "Pittsburgh: {{ k.stop.PIT.mean|f2 }} over {{ k.stop.PIT.n }} seasons. Elsewhere: {{ k.elsewhere.mean|f2 }} over {{ k.elsewhere.n }}.",
        "body": [
            "Dick LeBeau's Pittsburgh defenses were above average for more than a decade ({{ k.stop.PIT.mean|f2 }} over {{ k.stop.PIT.n }} seasons), which is harder than a short peak. His seasons in Cincinnati and Tennessee, at the two ends of the period covered, pull his career rank down to {{ k.career.rank }}.",
            "The study begins in 1999, so the first three decades of his career, including the invention he is best known for, are outside it.",
        ],
    },
    {
        "slug": "rod-marinelli", "person": "Rod Marinelli", "unit": "defense", "category": ONE_STOP,
        "verdict": "Chicago: {{ k.stop.CHI.mean|f2 }}. Dallas and the Raiders: {{ k.after.mean|f2 }}.",
        "body": [
            "Rod Marinelli's three seasons as Chicago's coordinator average {{ k.stop.CHI.mean|f2 }}, under a head coach who was himself a defensive coach and with a veteran defense. His {{ k.after.n }} seasons afterwards average {{ k.after.mean|f2 }}.",
            "He ranks {{ k.career.rank }}. As with Gus Bradley, the best stop came with the best players and a defensive head coach alongside.",
        ],
    },
    {
        "slug": "wade-phillips", "person": "Wade Phillips", "unit": "defense", "category": TRAVELLED,
        "verdict": "Ranked {{ k.career.rank }}. {{ k.n_stops }} teams, and an above-average defense with every one of them.",
        "body": [
            "Wade Phillips is the clearest case in the study of a record that followed the man. He ran the defense for {{ k.n_stops }} teams over {{ k.career.seasons }} rated seasons, and the average was above the league at every stop, from {{ k.worst_stop.mean|f2 }} to {{ k.best_stop.mean|f2 }}.",
            "His best season, with Denver in 2015, ended in a championship. Different players, different head coaches, different decades, the same result: that is what it looks like when the coordinator is a large part of the reason.",
        ],
    },
    {
        "slug": "mike-macdonald", "person": "Mike Macdonald", "unit": "defense", "category": PROMPTED,
        "verdict": "Ranked {{ k.career.rank }} after four seasons. His average is {{ k.mean_rank|ordinal }} of the {{ k.n_ranked }} ranked defensive callers.",
        "body": [
            "Mike Macdonald's two Baltimore defenses average {{ k.stop.BAL.mean|f2 }} and his two Seattle defenses {{ k.stop.SEA.mean|f2 }}. His second season at each stop was much better than his first.",
            "His career rating ({{ k.career.rating|f2 }}) is far below his average ({{ k.career.mean|f2 }}) because defensive records are noisy and four seasons is not many. The Seattle seasons are a belief that he calls the defense as head coach.",
        ],
    },
]


def _runs(g: pd.DataFrame, unit: str) -> list[dict]:
    """Consecutive seasons with the same franchise, in order."""
    runs: list[dict] = []
    for r in g.sort_values("season").itertuples():
        if runs and runs[-1]["franchise"] == r.franchise and r.season - runs[-1]["last"] <= 3:
            run = runs[-1]
            run["z"].append(r.z_epa)
            run["last"] = r.season
        else:
            run = {"franchise": r.franchise, "team": TEAM_NAMES.get(r.franchise, r.franchise),
                   "first": r.season, "last": r.season, "z": [r.z_epa], "qbs": []}
            runs.append(run)
        if unit == "offense" and isinstance(r.primary_qb_name, str) and r.primary_qb_name not in run["qbs"]:
            run["qbs"].append(r.primary_qb_name)
    for run in runs:
        run["n"] = len(run["z"])
        run["mean"] = sum(run["z"]) / run["n"]
    return runs


def _agg(g: pd.DataFrame) -> dict:
    return {"n": int(len(g)), "mean": float(g["z_epa"].mean()) if len(g) else float("nan")}


def case_facts(person: str, unit: str, t: dict[str, pd.DataFrame]) -> dict:
    seasons = t["playcaller_seasons"]
    careers = t["playcaller_careers"]
    g = seasons[(seasons["person"] == person) & (seasons["unit"] == unit)].sort_values("season")
    cr = careers[(careers["person"] == person) & (careers["unit"] == unit)].iloc[0]
    ranked = careers[(careers["unit"] == unit) & careers["rank_in_unit"].notna()]
    runs = _runs(g, unit)

    by_fr = g.groupby("franchise")
    stop = {fr: {"n": int(len(x)), "mean": float(x["z_epa"].mean())} for fr, x in by_fr}
    best_fr = max(stop, key=lambda f: stop[f]["mean"])
    worst_fr = min(stop, key=lambda f: stop[f]["mean"])

    recent_all = seasons[(seasons["unit"] == unit) & (seasons["season"] >= RECENT_FROM)]
    rec = recent_all.groupby("person")["z_epa"].agg(["size", "mean"])
    rec = rec[rec["size"] >= RECENT_MIN_SEASONS].sort_values("mean", ascending=False)
    recent = {"n": int((g["season"] >= RECENT_FROM).sum()),
              "mean": float(g.loc[g["season"] >= RECENT_FROM, "z_epa"].mean()) if (g["season"] >= RECENT_FROM).any() else float("nan"),
              "rank": int(list(rec.index).index(person) + 1) if person in rec.index else None, "of": int(len(rec))}

    qb_rank = None
    n_qbs = None
    if unit == "offense":
        q = t["playcaller_qb_adjusted"]
        rq = q[q["person"].isin(ranked["person"])].sort_values("rating_qb_adjusted", ascending=False).reset_index(drop=True)
        hit = rq.index[rq["person"] == person]
        qb_rank = int(hit[0] + 1) if len(hit) else None
        n_qbs = int(g["primary_qb_name"].nunique())

    excl = t["playcaller_excluded_unit_seasons"]
    excluded = excl[(excl["unit"] == unit) & excl["proposed_playcaller"].astype(str).str.contains(person, regex=False)]

    first_run, last_run = runs[0], runs[-1]
    first_fr = first_run["franchise"]
    after = g[g["season"] > first_run["last"]]
    # early = seasons before the first above-average three-year stretch is hard to define; use first third
    n_early = max(1, len(g) * 3 // 8)
    mean_rank = int((ranked["mean_z_epa"] > cr["mean_z_epa"]).sum() + 1)
    k = {
        "person": person, "unit": unit, "n_ranked": int(len(ranked)), "recent_from": RECENT_FROM,
        "mean_rank": mean_rank,
        "recent_min": RECENT_MIN_SEASONS,
        "career": {"rank": int(cr["rank_in_unit"]) if pd.notna(cr["rank_in_unit"]) else None,
                   "mean": float(cr["mean_z_epa"]), "rating": float(cr["rating"]), "se": float(cr["rating_se"]),
                   "seasons": int(cr["seasons"]), "share_unverified": float(cr["share_unverified"]),
                   "mean_explosive": float(cr["mean_z_explosive"]), "mean_ypp": float(cr["mean_z_ypp"])},
        "runs": runs, "stop": stop, "n_stops": len(stop),
        "best_stop": {"franchise": best_fr, **stop[best_fr]}, "worst_stop": {"franchise": worst_fr, **stop[worst_fr]},
        "first_stop": {"franchise": first_fr, "n": first_run["n"], "mean": first_run["mean"]},
        "last_stop": {"franchise": last_run["franchise"], "n": last_run["n"], "mean": last_run["mean"]},
        "after": _agg(after), "early": _agg(g.head(n_early)),
        "first_two": _agg(g.head(2)), "last_two_of_first": _agg(g[g["season"] <= first_run["last"]].tail(2)),
        "elsewhere": _agg(g[g["franchise"] != best_fr]),
        "ne": _agg(g[g["franchise"] == "NE"]),
        "before2011": _agg(g[g["season"] < 2011]), "since2011": _agg(g[g["season"] >= 2011]),
        "last": {"season": int(g["season"].iloc[-1]), "z": float(g["z_epa"].iloc[-1])},
        "recent": recent, "qb_rank": qb_rank, "n_qbs": n_qbs,
        "excluded": [{"season": int(r.season), "franchise": r.franchise, "reason": r.reason}
                     for r in excluded.sort_values("season").itertuples()],
        "seasons_table": g,
    }
    if person == "Josh McDaniels":
        k["elsewhere"] = _agg(g[g["franchise"] != "NE"])
    return k


def build_cases(t: dict[str, pd.DataFrame]) -> list[dict]:
    out = []
    for case in CASES:
        k = case_facts(case["person"], case["unit"], t)
        out.append({**case, "k": k})
    return out
