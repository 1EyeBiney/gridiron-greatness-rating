# Overnight exploration: what the seven questions turned up

Status: exploration only. Nothing committed, nothing on the site. All
numbers below were checked against the CSVs in this folder. Scripts
(exploration_plays.py, exploration_teams.py) re-run in seconds.

## Findings that change or sharpen what the site says

1. **In competitive time, big plays are nearly as decisive as turnovers.**
   Re-running the core win model on plays with win probability between
   5% and 95% only (q6_shift_logit_ng_by_era.csv): standardized
   coefficients 2017-2025 are explosive 1.16 vs turnover 1.33, against
   1.09 vs 1.56 with all plays. The gap shrinks by about two-thirds in
   every era. Garbage-time turnovers (desperation interceptions by
   trailing teams) inflate the turnover coefficient. "Turnovers still
   decide games" survives, but "by a distance" should become "narrowly,
   once garbage time is removed." This is the most important result.

2. **Regular-season big-play edge predicts playoff wins; turnover edge
   doesn't.** q7a_playoff_logit.csv, 309 playoff games: explosive
   differential coefficient +0.23 (SE 0.12), turnover differential -0.02
   (SE 0.12). Within playoff games, turnovers still win the head-to-head
   (32% win rate when winning explosives but losing turnovers). Super
   Bowl champions rank a median 8th in explosive differential and 7th in
   turnover differential - a tie. This extends "big plays decide seasons"
   through January and is worth a paragraph.

3. **Explosiveness travels with the quarterback.** Year-to-year
   persistence of team explosive-pass rate is 0.34 when the same QB
   returns and 0.18 when he changes (q5b). When a QB changes teams his
   explosive rate correlates 0.27 with his new team's; the team he left
   shows ~0 carryover. Small n on the moves (54-56), fine on continuity
   (773 team-seasons). Career leaders in explosive-pass rate per dropback
   (min 1,500): Lamar Jackson 23.3%, Brock Purdy 23.3%, Michael Vick
   21.7%, Robert Griffin 20.9%, Trent Green 20.8% (q5c). Fun, low
   explanation, fits the leaderboard page.

## Findings that explain the recent trend

4. **The 2018-2025 decline in big plays is a passing-efficiency drop, not
   a shift to the run.** Decomposition (q1_decomposition): 90% of the fall
   in explosive rate per play is within-type rate (explosive passes per
   dropback 8.7% -> 8.3%, explosive rushes per attempt 12.7% -> 11.2%);
   the falling pass rate contributes almost nothing. Defenses are taking
   the deep ball away; offenses are not choosing the run instead.

5. **No rise in early-drive shot-taking.** Explosive rate on the first
   play of a drive: 10.4% (2010-2017) vs 11.0% (2018-2025). Garbage-time
   share of explosives flat at ~15%. Simms' described behavior isn't in
   the play selection.

6. **The defensive-play curve rises through the third play of a drive
   and then goes flat** (q4): 8.1% on play 1, 10.3% on play 3, 9.4-9.9%
   on plays 4 through 8+ in 2017-2025, same shape every era, and the
   whole curve has shifted DOWN over time. Points per drive rose while
   the chance of at least one defensive play per drive did not. Long
   drives score; they are not increasingly dangerous. This is the
   cleanest refutation of the mechanism and belongs on the mechanism
   page.

## Findings not worth adding

- Between-team spread and top-5 concentration of explosives: flat across
  eras. Nothing happened.
- Situational rates by down/distance/field position: as expected
  (higher on 3rd-and-long, higher in the open field), explanation-heavy,
  no story.
- EPA per explosive play (+1.96) vs other plays (-0.22): stable for 27
  years. One sentence at most.

## Recommendation (small footprint, ~1 new page + 4 short additions)

- **Findings page**: soften "by a distance" to reflect the competitive-
  time result; one added sentence on playoffs.
- **The shift page**: add the competitive-time table (q6) with two
  sentences.
- **Mechanism page**: add the defensive-play-by-drive-length table (q4)
  and the pass-vs-run decomposition (q1), replacing the current
  strategy-correlation table if space is a concern.
- **Skill or luck page**: add the QB-continuity persistence table (q5b)
  and two sentences on portability.
- **Leaderboard page**: add career explosive-pass-rate leaders (q5c).
- **Head to head page**: add the postseason head-to-head (q7b) and the
  playoff prediction result (q7a) as one short section.
- **What It Means**: one new paragraph, "Where the big plays went"
  (2018 peak, passing efficiency, no early-drive shots), and adjust the
  "Sunday still belongs to the turnover" section to carry the
  competitive-time qualifier honestly.
- Every new number pinned in tests/test_xe_claims.py as before.

Estimated work: one Sonnet pass to move the six analyses into
src/xe_analysis_*.py with tests and tables, then Fable for the prose
and claim checks. About the size of one of today's phases.
