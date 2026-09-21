# Design notes and decisions

Companion to the README. This records the reasoning, in the order the
decisions were made, so a later session (or reader) doesn't have to
rediscover it.

## 2026-09-19 — Scope and data

Brian's two questions: (1) does home-field advantage wane late in the
season as eliminated teams' fans sell seats on the resale market, and (2)
do some franchises (Steelers, 49ers were the examples) travel well enough
to blunt the home team's edge. Both answered from final scores only. No
attendance or ticket-market data exists in the pipeline, and none was
fetched.

Data reused from Gridiron Greatness: the unified games table (copied, with
provenance) and the conference table. nflverse games.csv re-fetched
(same source and license already approved for that project) for two
columns the unified table lacks - roof type and the divisional-game flag,
both 1999+ - and for a "current season so far" note.

Exclusions: 1982 (nine games, irregular post-strike schedule, sixteen-team
tournament; its final third has fewer games than the model has
parameters), the 1987 replacement games (flagged by the sibling project),
and neutral-site games from every home-field average (they stay in the
rating fits).

## The yardstick

One quantity everywhere: adjusted home margin = actual margin minus the
rating difference from a per-season OLS fit with a shared home term
(Massey with home field). Averaged over any group of true home games it
is that group's home-field advantage in points, with a standard error.
Chose OLS over the sibling project's ridge model deliberately: this study
needs unbiased group means of residuals, not well-calibrated individual
team ratings, and OLS residuals have the clean orthogonality properties
the identification arguments below rely on.

Pre-1999 weeks: the sibling project's date-gap rule (new week after a gap
of 4+ days) under-counts weeks when Thursday games sit 3 days after a
Monday game. Replaced with a calendar rule - week = Tuesdays elapsed since
the Tuesday on or before the first game - which reproduces the real
14/16/17/18-week schedule lengths exactly for every season (tested).

## The selection artifact (the important finding about method)

First pass at the playoff-race question grouped late-season games by the
home team's running status and compared them to full-season ratings.
Result: eliminated hosts "enjoyed" 4.0 points of home field against 2.6
for contenders. Wrong. A team is eliminated because it lost early; its
full-season rating includes those losses; its late games beat that
rating by construction. The same excess appeared for eliminated teams on
the road, which is the tell. Refitting ratings on the final third only
shrank the artifact but didn't remove it, because within-window results
still feed a running status.

Fix: freeze status entering the window, fit ratings on the window's games
only. Then residuals are independent of the label (the label depends only
on earlier games; the ratings only on later ones). The naive table is
kept and shown on the playoff-race page as a worked example, because
anyone who tries this analysis casually will hit it.

## The identification limit (what scores cannot say)

A rating model has no term for a team-specific home effect, so if one
exists it lowers that team's rating and spreads the shortfall evenly
across the team's home and road residuals. Consequence: for any group of
teams, "HFA as host" and "HFA as visitor" come out nearly equal whatever
the truth, and only the average over all games involving the group is
identified. Under the resale hypothesis that average should still drop
(by half the host deficit), so the test has power; it just can't
attribute the deficit to the stadium. Documented on the methodology and
playoff-race pages rather than hidden.

The same limit applies to the franchise question: a small home/road swing
is what traveling fans would produce and also what a weak home crowd
would produce. The swing is reported as the identified quantity; the
cause is left open, explicitly.

## Results (headline)

- Home field about 2.5 points over 1970-2025; ~3.0 in the 1970s-1990s,
  2.5 in the 2000s, 2.2 in the 2010s, 1.7 in the 2020s. 1990s-vs-2020s
  difference is more than 3 SE.
- Late third of the season is the strongest for home teams (3.0 vs 2.3
  early), the highest third in 5 of 6 decades and within 0.03 in the
  2010s. Final week 2.9. Indoors and outdoors both show the late rise, so
  weather is not the (whole) explanation.
- Playoff race, clean design, last three weeks: games involving
  eliminated teams 3.7 ± 0.2, contenders 3.8 ± 0.2. Flat by games back
  too. Same in 2010-2025. Hypothesis not supported.
- 2020 (no fans): 0.1 ± 0.7, against 1.7 before and 2.0 after.
- Franchises: swings run 3.4 (NO) to 6.8 (DET) around a league 5.1; two
  of 32 at |z| >= 2, as chance predicts. Pittsburgh's swing is larger
  than average (z +1.5), the opposite of the traveling-fans prediction;
  San Francisco slightly smaller (z -0.9), not significant.

## Testing prose

As on the sibling site, tests/test_narrative_claims.py pins every
qualitative claim to the tables. It caught two overstatements in the
first draft before anything was published: "the final third is highest
in every decade" (the 2010s early third edges it by 0.03) and "week 1 is
the weakest week" (week 10 is marginally lower). Both sentences were
rewritten to say what the data say. Numbers in the prose are injected
from the tables at render time and cannot drift.

## Carried forward

- Attendance or resale-market data would turn the identified quantity
  into the mechanism. Not fetched: license check and Brian's OK first.
- Distance travelled, rest days, and time-zone crossings are available
  or derivable (nflverse has rest days from 1999) and would sharpen the
  decline story.
- The big-play-versus-turnover question is a separate study needing
  nflverse play-by-play (1999+, CC BY 4.0). Not started; needs Brian's OK
  for the fetch.


## 2026-09-21 -- Outside review (v1.0) and the response

An AI review Brian commissioned made three points about this study; all
three were right and are now on the site.

1. **2020 was oversold.** The venues page said "nothing else changed" and
   the story page called 2020 "the season that proved the crowd matters".
   Our own by_season.csv has 2019 at -0.07 +/- 0.74 with full stadiums, so
   a single near-zero season is not remarkable; 2020 also had no preseason,
   restricted practice, and attendance limits that varied by city and
   month. Prose now: consistent with a crowd effect, suggestive, not proof;
   the missing test (within-2020 games by attendance limit, allowing for
   venue and team) is named. New facts hfa_2019 / se_2019; claim test.
2. **Swing is not a venue estimate.** Denver's 6.5-point swing is home
   minus road across two stadiums and 55 seasons, not "Mile High is worth
   6.5". New "What the swing is not" section on franchises.html with the
   recipe for a real venue study (stadium x era effects, shrinkage,
   travel/rest/altitude/roof, out-of-sample persistence, uncertainty) and
   the fan-vs-venue distinction. New facts den_swing / den_z.
3. **"No fan base shows up" -> "nothing detectable".** Each swing is
   measured to about +/-0.82 points (median SE), so a road effect of ~1
   point per game would sit inside the noise. Stated on index, story and
   franchise pages; new fact swing_se_median.
4. **Elimination labels are approximate.** Conference-wide point totals,
   no tiebreakers or division races. Methodology and the two pages that
   lean on the label now say so.

Tests: 32 after the change (was 31).
