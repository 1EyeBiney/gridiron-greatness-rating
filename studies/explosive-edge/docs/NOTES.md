# Explosive Edge: design notes and decisions

Companion to PLAN.md. Records what was decided and found, in order.

## 2026-09-19 — Build, Phases 0-2 (Sonnet subagents, Fable review)

Data: nflverse play-by-play 1999-2025 (CC BY 4.0), 27 parquet files
(~466 MB) kept local and gitignored; only the per-team-game aggregate
(team_game.csv, 14,546 rows: 13,928 regular season + 618 postseason) and
the per-season league table are committed. Three real games are absent
from the nflverse release (1999 BAL@STL wk1, 2000 SD@KC wk3, 2000 BUF@MIA
wk6); the game-count test carries them as a documented exception.

Two bugs caught in review before any analysis ran on them:

1. **Fumble attribution.** On punts the punting team is `posteam`, so
   charging lost fumbles to `posteam` credited a returner's fumble to the
   wrong side. Checked on 2023 data: 0% of punt-fumble rows have
   `fumbled_1_team == posteam`, versus ~99-100% on pass/run/kickoff. Fixed
   to charge `fumbled_1_team`; about 28 turnovers per season (3.4% of all
   turnovers) moved sides.
2. **Franchise codes.** nflverse play-by-play labels every season with a
   franchise's *current* code (the 1999 Rams are "LA", the 2005 Raiders
   "LV"), unlike the schedule file the crosswalk windows were written for.
   908 team-games failed to map. Fixed with a season-agnostic fallback for
   any code the crosswalk knows; zero unmatched now.

Definition decisions accepted as made by the ingest agent: postseason
kept but labelled REG/POST only (play-by-play has no round detail);
`def_plays_made` counts plays, not flags (a strip-sack counts once);
plays with null win probability are treated as garbage time in the `_ng`
variants; league_season.csv is regular season only.

## Review checkpoint 1 (Fable) — what the tables say

Association, standardized logistic coefficients, both-variables model:

| era | EPD | TOD | log loss EPD / TOD / both |
|---|---|---|---|
| 1999-2007 | 1.08 | -1.72 | .602 / .503 / .431 |
| 2008-2016 | 1.07 | -1.63 | .604 / .520 / .445 |
| 2017-2025 | 1.09 | -1.56 | .603 / .535 / .454 |

Turnover differential is the stronger per-game predictor in every era.
Its coefficient has eroded slightly (trend +0.009/season toward zero, SE
0.005, borderline); the explosive coefficient is flat. Exchange rate is
stable: one turnover is worth 2.3-2.5 explosive plays in points of
margin (about 4 points vs about 1.7).

Head-to-head: a team that wins the explosive battle but loses the
turnover battle wins 35% (1999-2007), 41%, 38% (2017-2025). Turnovers
win that argument in every era. BUT turnovers per game fell from 3.8 to
2.3, so the turnover battle is tied more often and the share of games
decided by explosives alone (turnovers even) rose from 17% to 21% of
games.

Persistence (split-half r across team-seasons): explosive differential
0.38 / 0.37 / 0.42 by era; turnover differential 0.18 / 0.20 / 0.18;
margin 0.54 / 0.51 / 0.49. Explosive differential is about twice as
repeatable as turnover differential in every era, and correlates with
the main project's True Strength Rating as strongly as turnovers do
(r ≈ 0.64 vs 0.66).

Mechanism: NOT as Simms describes. Plays per drive rose 5.3 -> 6.0,
seconds per drive 146 -> 172, pass rate flat, defensive plays per snap
fell 11.3% -> 9.2%, turnovers per game fell 40%. Explosive rate per play
rose only 9.0% -> 9.6% (per drive 0.44 -> 0.55, mostly because drives
are longer). Across team-seasons, more explosive teams run slightly
*more* plays per drive, not fewer, in every era.

### Framing decision

Headline: **turnovers still decide games; big plays decide seasons.**
Per game, a turnover is the bigger swing and the better predictor, and
that has barely changed. But turnovers are mostly noise from one half
of a season to the next, while explosive-play differential is a
repeatable trait that tracks team quality. Simms is wrong about the
per-game balance and wrong about the mechanism (drives are longer, not
shorter, and defenses make fewer plays per snap than they used to, so
there is no rising per-snap danger to avoid), but right in a way he
didn't argue: if you want a number that tells you which team is good
rather than which team got lucky on Sunday, count the big plays.

Caveats to state on the site:
- Yardage tautology: explosive plays are yards, yards are points. The
  EPA >= 2 sensitivity and the relative framing address it; report the
  sensitivity tables.
- Persistence gap is partly arithmetic: a team has ~9 explosive plays a
  game and ~1.2 turnovers, so a per-game turnover rate is measured with
  more sampling noise. Part of "turnovers are luck" is "turnovers are
  rare." The site should say so; the year-to-year table helps but does
  not remove it.
- 2017-2025 head-to-head (38%) is a shade above 1999-2007 (35%), and the
  turnover coefficient is drifting toward zero. The direction Simms
  describes exists; it is small and not significant on its own.

## Carried forward

- A binomial-noise-adjusted reliability (correct split-half r for event
  counts) would settle how much of the persistence gap is real skill.
- Playoff-round detail would need the schedule file join.
- Graphics are placeholders from the main project until Brian replaces
  them.

## Review checkpoint 2 (Fable) — site and prose

Phase 3 (Sonnet) delivered xe_site.py, nine pages and a link/alt checker
without incident. Fable wrote the Findings and What It Means pages from
the facts dict and pinned every qualitative claim in
tests/test_xe_claims.py. One claim was softened by the test before
publication: the persistence gap's confidence intervals overlap slightly
in 1999-2007 (explosive 0.27-0.47 vs turnover 0.06-0.29), so the prose
says the gap is wide and holds year to year rather than that the intervals
are disjoint. 67 study tests, 122 main tests. Wired into the main build
via STUDIES and a card on the main index; published at
/explosive-edge/ with the rest of the site.

## 2026-09-20 — Overnight exploration and where we left off

Two Sonnet agents ran the seven follow-up questions (~230k tokens total)
as exploration only; scripts, CSVs and findings are in exploration/,
with Fable's review and recommendation in exploration/MORNING_REPORT.md.
Headline additions recommended, none yet built:

1. Competitive-time-only model: turnover-vs-explosive gap shrinks by about
   two-thirds (2017-25: 1.33 vs 1.16). Soften "by a distance" on Findings;
   add the q6 table to the shift page.
2. Regular-season explosive edge predicts playoff wins (+0.23, SE 0.12,
   n=309); turnover edge does not (-0.02). Add to head-to-head page.
3. Explosiveness travels with the QB (persistence 0.34 same QB vs 0.18
   changed; career leaders Lamar Jackson, Brock Purdy 23.3%). Add to
   skill-or-luck and leaderboard pages.
4. 2018->2025 decline in big plays is passing efficiency (~90% of the
   change), not a shift to the run. Mechanism page.
5. No rise in early-drive shot-taking; garbage share flat at ~15%.
6. Defensive-play probability rises through play 3 of a drive then goes
   flat, in every era, and has shifted down. Mechanism page; strongest
   refutation of the shorter-drive story.
Not worth adding: team concentration/spread, situational splits, EPA per
explosive play (all flat).

Plan when we return: one Sonnet pass to move these six analyses into
src/xe_analysis_*.py with tests and tables; Fable writes the prose
changes (Findings, What It Means "Where the big plays went" paragraph)
and pins claims in test_xe_claims.py. Est. one phase of work. Work on the
Purdue basketball study starts in the meantime (studies/ folder pattern).
