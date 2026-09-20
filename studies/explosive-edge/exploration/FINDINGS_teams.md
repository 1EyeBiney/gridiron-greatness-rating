# Explosive Edge — exploration: QBs, play-level value, and playoffs

Companion to `exploration_plays.py`/`FINDINGS_plays.md` (owned by a
concurrent agent, not touched here). This file covers Q5 (quarterbacks),
Q6 (which explosive plays matter), Q7 (playoffs/championships). Built by
`exploration_teams.py`, re-runnable, runtime ~1-2 seconds. All CSVs are in
this directory.

## Q5. Explosive plays and the quarterback

**One-sentence answer:** explosiveness travels with the quarterback more
than it stays with the team, but the samples are small and the signal is
noisy in both directions — treat this as suggestive, not conclusive.

**(a) QB moves, 1999-2025, >=8 games started for both the old and new
team in consecutive seasons — n = 56 moves** (`q5a_qb_moves.csv`):
correlation of the QB's own explosive-pass rate per dropback, old team
season *s* vs new team season *s+1*, is r = 0.27 (explosive differential
per game: r = 0.23). Mean rate barely moved (0.154 -> 0.158, +0.004).
For the **old team's** explosive rate with a *different* new primary
starter in season *s+1* (n = 54, `q5a_old_team_new_qb.csv`), the
correlation season-to-season is r = -0.05 for rate (essentially zero) but
r = 0.36 for explosive *differential* per game — mixed, because
differential also reflects the opposing defense and overall team talent,
not just the passer. Taken together the QB's own rate is more
self-consistent across a team change (r = 0.27) than the team's rate is
when it swaps QBs (r ~ 0), which favors "travels with the QB," but n=54-56
is small — a dozen outlier trades would move these correlations a lot.

**(b) Year-to-year persistence split by QB continuity**
(`q5b_persistence_by_qb_continuity.csv`): team explosive-pass-rate
correlation season *t* to *t+1* is r = 0.336 (n = 478 team-seasons) when
the same primary starter returns, vs r = 0.177 (n = 295) when the primary
starter changed. Persistence is roughly twice as strong with QB
continuity — consistent with (a): the passer carries some of the
explosive-play tendency, on top of whatever the team/scheme carries.

**(c) Career and season leaders** (`q5c_career_leaders.csv`,
`q5c_season_leaders.csv`): top career explosive-pass rate per dropback
(min 1,500 dropbacks as a starter, 1999-2025) is **Lamar Jackson** (23.3%,
3,592 dropbacks), then Brock Purdy (23.3%), Michael Vick (21.7%), Robert
Griffin III (20.9%), Trent Green (20.8%) — the list is dominated by
mobile/deep-shot QBs, not classic high-volume passers. Top single seasons
(min 300 dropbacks): **Ben Roethlisberger 2004** (31.1%, only 305
dropbacks as a rookie starter on a run-heavy team), Robert Griffin III
2012 (28.6%), Brock Purdy 2023 (28.2%), Lamar Jackson 2019 (27.9%).

**Caveat:** the QB join (schedule file `home_qb_id`/`away_qb_id`) misses
894 of 13,928 REG team-games (6.4%), concentrated in early seasons where
nflverse's QB-id backfill is thinner; this trims the eligible pool for
(a)-(c) but shouldn't bias the direction of the correlations. Q5a's n of
54-56 is the headline caveat — small enough that a few blockbuster trades
(Rodgers to Pittsburgh, Stafford to the Rams) carry real weight in the
correlation.

## Q6. Which explosive plays matter

**One-sentence answer:** explosive plays are worth roughly ten times the
EPA of a normal play regardless of era, about 15% of them happen in
garbage time every season (no trend), the great majority occur in close
games, and stripping out garbage-time plays narrows — but does not erase
— the turnover-vs-explosive gap from the all-plays association test.

Mean EPA per explosive play (20/10 definition) is **+1.96** averaged
1999-2025 (season range 1.88 to 2.01), vs **-0.22** for a non-explosive
scrimmage play (range -0.26 to -0.18) — both essentially flat over 27
seasons (`q6_epa_by_season.csv`). The share of explosive plays occurring
in garbage time (win probability outside [0.05, 0.95]) is **15.4%**
league-wide, ranging 12.4%-18.1% by season with no clear trend (1999:
15.0%, 2025: 14.8%) (`q6_garbage_share_by_season.csv`). Explosive plays
per game by absolute score margin at the time of the play
(`q6_explosive_by_margin_bucket.csv`): **7.53/game within 7 points**,
2.82/game at 8-16, 1.53/game at 17+ — close games generate roughly 5x as
many explosive plays as blowouts, mechanically (more snaps happen in
close games) but also because garbage-time defenses are more likely to
concede a cheap explosive play against a prevent look.

Re-running the core association logit (EPD + TOD, both standardized
within season) using only competitive-time plays (`_ng` columns)
(`q6_shift_logit_ng_by_era.csv`) against the all-plays baseline
(`data/processed/shift_logit_by_era.csv`):

| era | EPD (all) | TOD (all) | gap (all) | EPD (_ng) | TOD (_ng) | gap (_ng) |
|---|---|---|---|---|---|---|
| 1999-2007 | 1.076 | -1.720 | -0.645 | 1.114 | -1.429 | -0.315 |
| 2008-2016 | 1.067 | -1.628 | -0.562 | 1.200 | -1.327 | -0.126 |
| 2017-2025 | 1.091 | -1.562 | -0.471 | 1.160 | -1.329 | -0.169 |

(gap = EPD coefficient minus |TOD coefficient|; more negative means
turnovers dominate more.) Restricting to competitive-time plays roughly
**halves the turnover advantage** in every era: the EPD coefficient rises
modestly (+0.04 to +0.13) and the TOD coefficient shrinks in magnitude
noticeably (from ~-1.6/-1.7 down to ~-1.3 to -1.4). Turnovers still win
the per-game association test in every era, non-garbage-time or not, but
part of their edge over explosive plays in the full-play version comes
from garbage-time turnovers (backup QBs throwing pick-sixes down 24, etc.)
that don't reflect competitive football. This is a real, if secondary,
qualifier on the NOTES.md headline "turnovers still decide games" — worth
a line on the site.

**Caveat:** the era pattern in the gap is non-monotonic (2008-2016 has
the narrowest gap, not 2017-2025), so this isn't a clean "shrinking gap
over time" story on top of the garbage-time effect — it's a level shift
that appears similarly sized in the two later eras.

## Q7. Do explosive teams win in January

**One-sentence answer:** in the playoffs themselves, teams that win the
turnover battle win more often than teams that win the explosive battle
(consistent with the regular-season pattern), but which regular-season
metric better *identifies* the eventual champion is a coin flip — median
ranks are close (8th for explosive differential, 7th for turnover
differential) — so explosive-play differential's edge is about *predicting
during the game*, not picking champions ahead of time.

**(a) Playoff win ~ pre-game regular-season EPD and TOD differences**
(standardized, home-team-perspective differences), pooled and by era
(`q7a_playoff_logit.csv`, n = 309 playoff games pooled, ~99-111 per era):
pooled, the EPD coefficient is **+0.231 (SE 0.120)**, roughly 2-sigma from
zero, while the TOD coefficient is **-0.023 (SE 0.117)**, indistinguishable
from zero. By era the EPD coefficient is positive throughout (0.17-0.34)
and TOD flips sign (-0.12, -0.09, +0.23) without ever reaching
significance. Margin OLS tells the same story (`q7a_playoff_margin_ols.csv`):
EPD beta +2.07 (SE 0.78) pooled, TOD beta -1.71 (SE 0.78) pooled, but R2
is only 0.037 — regular-season form barely explains playoff-game margins
at all. **This flips the regular-season ranking of the two metrics**:
in-season, turnover differential is the stronger single-game predictor
(NOTES.md); here, a team's *regular-season* explosive differential
predicts its *playoff* wins better than its regular-season turnover
differential does. That is plausible (regular-season turnover
differential is noisy and a bad forecast of a specific playoff game's
turnovers, which happen fresh each week) but is a genuinely new and
somewhat surprising result relative to NOTES.md's framing — flag for
Fable/site review.

**(b) Head-to-head, playoff games only, pooled 1999-2025** (n = 309
decided playoff games, `q7b_head_to_head_postseason.csv`, same
categorization as `data/processed/head_to_head_by_era.csv`): a team that
wins the *explosive* battle but loses the *turnover* battle in that
playoff game wins only **31.6%** of the time (n = 98) — actually lower
than the regular-season equivalent (35-41% by era in NOTES.md). Winning
both battles wins 83.7% (n = 123); winning turnovers alone (explosive
even) wins 86.4% (n = 22, small); winning explosives alone (turnovers
even) wins 77.4% (n = 62). So **within playoff games, turnovers dominate
explosives even more than they do in the regular season** — the opposite
direction from (a)'s regular-season-form finding. These are two different
questions (which stat wins the specific game vs. which regular-season
trait forecasts a team's playoff success) and both can be true at once.

**(c) Super Bowl winners' regular-season rank** (1999-2025, 27
champions, `q7c_super_bowl_ranks.csv`): median rank in explosive-play
differential per game was **8th of ~32** teams; median rank in turnover
differential per game was **7th of ~32**. Essentially a tie — neither
metric is a strong standalone "who wins the Super Bowl" signal (both
medians are good-not-great, top-quartile-ish), and several champions
ranked outside the top 20 on one metric or the other (e.g., 2014 Patriots
26th in EPD; 2023 Chiefs 28th in TOD; 2006 Colts 26th in EPD). This
mild finding is worth noting precisely because it's *not* what (a)
would suggest — (a) says regular-season EPD predicts playoff wins better
than TOD does, but the two metrics tie on picking the eventual champion
specifically. The resolution is probably that (a) is about winning
individual playoff games (where a few points of edge compound over 3-4
games) while (c) is a single yes/no outcome per season with only n=27
observations — much higher variance, so a modest true edge in (a) doesn't
reliably show up as a rank gap in (c).

**Caveats for Q7 throughout:** n = 309 postseason games and only n = 27
Super Bowl winners are small samples; every SE and correlation here should
be read as suggestive rather than settled, and (a)'s R2 of 0.037 means
even the "significant" EPD coefficient explains very little of playoff
margin. The is_home flag in team_game.csv for POST games is nominal
(nflverse's home/away designation, not necessarily the higher seed) but
since it's just used to pick one row per game for pairing, that doesn't
bias the regression.

## Files written

- `exploration_teams.py` — re-runnable script, all three questions
- `q5a_qb_moves.csv`, `q5a_old_team_new_qb.csv`
- `q5b_persistence_by_qb_continuity.csv`
- `q5c_career_leaders.csv`, `q5c_season_leaders.csv`
- `q6_epa_by_season.csv`, `q6_garbage_share_by_season.csv`,
  `q6_explosive_by_margin_bucket.csv`, `q6_shift_logit_ng_by_era.csv`
- `q7a_playoff_logit.csv`, `q7a_playoff_margin_ols.csv`
- `q7b_head_to_head_postseason.csv`
- `q7c_super_bowl_ranks.csv`
- `FINDINGS_teams.md` (this file)

Total runtime: ~1-2 seconds per run (printed by the script itself).
