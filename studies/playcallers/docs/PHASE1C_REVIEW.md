# Extending to 1999: review (Fable, 2026-09-28)

Brian asked for the older seasons. The study now covers 1999-2025.
Subagent detail is in PHASE1C_REPORT.md; this note records what was done,
what the review changed, and what is still weak.

## How the older staff table was built

| Step | Source | Result |
|---|---|---|
| Team-season pages 1999-2010 (381 pages) | Wikipedia | head coach 381 of 381; coordinators 551 of 762 |
| Gap fill, two passes | Coaching histories in coach biographies | 168 coordinator gaps filled across 1999-2025 |
| Combined table | `staff_stints_all.csv`, 2,562 rows | coordinators 685 of 762 (1999-2010), 922 of 960 (2011-2025) |

Biographies were checked against team pages wherever both name a
coordinator: they agree in 1,157 of 1,172 cases (98.7%), and the 15
disagreements look like mid-season changes. A gap was filled only when the
man's own biography lists that team, those years and that title.

A planned source, per-team lists of past coordinators, does not exist on
Wikipedia, so biographies carry all the gap filling.

## What the review changed

- **Head-coach placeholders no longer enter the ratings.** Where no
  coordinator was listed the draft credited the head coach. That put Tony
  Dungy, a defensive coach, third on the offensive list for the 2003-2005
  Colts, and gave Bill Belichick seven offensive seasons. Those rows stay in
  the table, marked, but are excluded from ratings unless an override names
  the head coach.
- **Continuity guess.** If a team lists nobody in a role but the same man
  held it both before and after (within three seasons), he is assumed to
  have held it in between. Eleven unit-seasons, including Tom Moore with the
  2003-2005 Colts. Basis `continuity_guess`, confidence low.
- **Older play-caller guesses.** Twenty-one head coaches believed to have
  called their own plays in 1999-2012 were added (Martz, Holmgren, Mike
  Shanahan, Gruden, Reid through 2005, Payton, Norv Turner, McCarthy,
  Kubiak, Spurrier, Garrett, Trestman, Gailey, Rex Ryan, Wade Phillips and
  others). All unverified, none rated high confidence. The McCarthy and
  Garrett rows correct the earlier list, which had credited Tom Clements and
  Bill Callahan with offenses their head coaches are believed to have called.

## Where the table stands (1,722 unit-seasons)

| Basis | Unit-seasons |
|---|---|
| Coordinator by title | 1,379 |
| Belief that the head coach called plays, unverified | 238 |
| No coordinator listed, head coach as placeholder (not rated) | 87 |
| Continuity guess | 11 |
| Wikipedia sentence | 7 |

1,490 unit-seasons enter the ratings; 232 are excluded (mid-season changes,
shared play calling, or no coordinator listed).

## Weak points

- **115 coordinator gaps remain**, led by New England (17), Cleveland (11)
  and Arizona (11). 2003-2005 and 2009-2011 are the thinnest seasons.
- **Mid-season changes are still undated** and excluded: 144 unit-seasons.
- **Older play callers are harder to guess.** Who called plays in 2002 is
  less well remembered than in 2022, and these guesses are mine.
- **Process.** One subagent declined the whole task as too large; it was
  split into three smaller ones. A subagent ran one fetch in the background
  against instructions; it was a single process, so the one-request-per-
  second limit held. All requests went to Wikipedia: 1,557 in total for the
  study.
