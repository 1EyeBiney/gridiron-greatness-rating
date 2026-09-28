# Phase 1b review (Fable, 2026-09-27)

Reviewed the subagent's draft play-caller table. Its numbers and its
process error are reported in PHASE1B_REPORT.md; this note records what the
review changed and what Brian needs to decide.

## What the review changed

- **Added candidate overrides.** The draft covered eight head coaches. It
  missed both of the cases that prompted the study: Mike Macdonald calling
  Seattle's defense (2024-2025) and Ben Johnson calling Chicago's offense
  (2025). Thirty candidate rows were added for head coaches believed to
  call their own plays (LaFleur, Taylor, O'Connell, Stefanski, Reich,
  Steichen, Arians, Kingsbury, Gruden, McDaniels, McCarthy, Zimmer, Fangio,
  Staley and others). Every one is marked `model_knowledge_unverified`,
  confidence low or medium, never high. They are beliefs, not sourced facts.
- **Cleaned names.** Footnote marks had survived on two names ("Sean
  Payton", "Gregg Williams") and "Pete Carmichael, Jr." was split from
  "Pete Carmichael Jr."; fixed in pc_build_derived.py and all tables rebuilt
  from the cached pages (no new requests).
- **Tests.** Two unit tests used Arizona 2015 as their plain-default
  example; Arizona 2015 is now an override candidate (Bruce Arians), so the
  example moved to a team-season with no override. 41 tests pass.

## Where the table stands

| Basis | Unit-seasons (of 960) |
|---|---|
| Coordinator by title (default) | 749 |
| No coordinator listed, head coach assumed | 59 |
| Wikipedia sentence says who called plays | 7 |
| Model belief, unverified | 145 |

Mid-season changes are flagged on 96 unit-seasons. Overrides are not
applied in seasons with more than one head coach; those stay at the default
and carry the flag.

## Honest weaknesses

- **Wikipedia almost never says who called plays.** 147 sentences mention
  play calling; only 7 unit-seasons could be settled from them. The
  override list therefore rests mostly on unverified belief until sources
  are attached.
- **2011 is thin.** 35 of the 59 no-coordinator rows are 2011, because those
  pages lack the staff fields. Either fill 2011 by hand or start the ratings
  in 2012.
- **An override can only name the head coach.** New England 2022 had no
  titled offensive coordinator and the plays are believed to have been
  called by an assistant. It sits at the head-coach default and is wrong.
- **Mid-season changes have no dates.** Ratings need game-level dates for
  the 96 flagged unit-seasons, or those seasons must be split or dropped.
- **Process error by the subagent.** Two fetch processes overlapped for a
  few minutes, so the one-request-per-second rule was briefly exceeded and
  the phase made 474 requests against a budget of 450. Wikipedia only; no
  other site was contacted. Future fetch tasks will run in the foreground.

## What Brian reviews

`data/reference/playcaller_overrides_summary.csv`: 51 rows, one per coach,
team, unit and run of seasons, with the title holders beside it and two
empty columns for his verdict. The season-by-season detail is in
`playcaller_overrides_for_review.csv`.
