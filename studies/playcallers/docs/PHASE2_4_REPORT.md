# The Playcallers — Phases 2-4 report

## Method, in plain language

**Phase 2 (unit ratings).** For every regular-season game 2011-2025, we
know each team's offensive efficiency (EPA per play, explosive-play rate,
yards per play) and the same numbers for whoever they played. We fit one
model per season and per metric: every team gets an offense number and a
defense number, and a team-game's result is explained as "your offense
number, minus your opponent's defense number, plus a small home-field
bump." A small ridge penalty keeps the numbers from blowing up when a team
has an unusual schedule. Offense and defense numbers are converted to
z-scores within season so "0" always means league-average that year, and
defense is flipped in sign so that, like offense, higher is always better.

**Phase 3 (play-caller ratings).** Every included team-season is credited
to a person (the coordinator, or the head coach where the draft table says
he calls the plays). A person who calls plays for several seasons gets an
average rating, but that average is pulled toward the league mean by an
amount that depends on how many seasons of evidence he has and how much
teams vary year to year versus how much people vary from each other
(explained under Variance components below) — a version of "regression to
the mean" done by formula rather than by eye. We also build a QB-adjusted
version for offense: the same team-season EPA gets split into a
caller-credit and a quarterback-credit at the same time, since a caller
who only ever worked with one great QB (or vice versa) cannot otherwise be
told apart from that QB.

**Phase 4 (coaching trees).** Built only from the staff table: an edge
mentor → protégé exists whenever the protégé was a coordinator while the
mentor was head coach of the same team.

## Sanity checks

- Offense EPA/play: correlation of the schedule-adjusted rating with the
  team's raw (unadjusted) EPA/play was 0.967; defense was 0.939 (raw
  flipped in sign so "more adjustment = better defense" lines up).
- Top 5 offenses by career-average EPA z, 2011-2025: **GB (1.02), KC
  (0.82), SEA (0.64), NE (0.62), NO (0.60)**. Bottom 5: NYJ (-1.13), JAX
  (-0.83), CLE (-0.74), NYG (-0.54), HOU (-0.47).
- Top 5 defenses: **DEN (0.76), BAL (0.64), SEA (0.57), LAR (0.54), MIN
  (0.51)**. Bottom 5: OAK/LV (-0.78), ATL (-0.61), TEN (-0.53), WSH
  (-0.50), IND (-0.44).
- These are the offenses and defenses most football fans would name from
  memory for this era, which is the check we set out to pass.

## Variance components and what they imply

One-way random-effects model on career EPA z, fit separately by unit
(`data/processed/playcaller_variance_components.csv`):

| unit | within-person variance (σ²) | between-person variance (τ²) | seasons for half weight |
|---|---|---|---|
| offense | 0.74 | 0.22 | 3.3 |
| defense | 0.87 | 0.13 | 6.7 |

"Seasons for half weight" is σ²/τ²: the sample size at which a person's
raw average gets 50% weight and the league mean gets the other 50%. For
offensive callers that happens at about **3 seasons**; for defensive
callers it takes about **7 seasons**. In plain terms: defensive results
are noisier relative to how much defensive coordinators actually differ
from each other, so it takes roughly twice as long before we trust a
defensive coordinator's track record as much as an offensive
coordinator's. This matches the plan's stated expectation that defense
would be noisier, and it is the main reason four-season careers like Ben
Johnson's and Mike Macdonald's carry wide uncertainty bands below.

## Play-caller ratings — offense (>= 3 seasons, ranked by shrunk rating)

Top 20:

| person | seasons | franchises | mean z (EPA) | rating | SE | % unverified |
|---|---|---|---|---|---|---|
| Andy Reid | 12 | PHI,KC | 1.16 | 0.91 | 0.22 | 100% |
| Josh McDaniels | 12 | NE,OAK | 0.89 | 0.70 | 0.22 | 8% |
| Sean Payton | 13 | NO,DEN | 0.83 | 0.66 | 0.21 | 100% |
| Matt LaFleur | 8 | TEN,GB | 0.88 | 0.63 | 0.26 | 88% |
| Ben Johnson | 4 | DET,CHI | 1.12 | 0.61 | 0.32 | 25% |
| Darrell Bevell | 7 | SEA,DET | 0.84 | 0.57 | 0.27 | 0% |
| Tom Clements | 3 | GB | 1.19 | 0.57 | 0.34 | 0% |
| Todd Haley | 6 | PIT | 0.74 | 0.48 | 0.28 | 0% |
| Greg Roman | 11 | SF,BUF,BAL,LAC | 0.60 | 0.46 | 0.23 | 0% |
| Joe Brady | 3 | CAR,BUF | 0.92 | 0.44 | 0.34 | 0% |
| Bill Callahan | 3 | DAL | 0.88 | 0.42 | 0.34 | 0% |
| Todd Monken | 7 | TB,CLE,BAL | 0.60 | 0.41 | 0.27 | 0% |
| Ken Whisenhunt | 5 | ARI,LAC | 0.67 | 0.40 | 0.30 | 20% |
| Sean McVay | 12 | WSH,LAR | 0.51 | 0.40 | 0.22 | 75% |
| Kyle Shanahan | 15 | WSH,CLE,ATL,SF | 0.49 | 0.40 | 0.20 | 60% |
| Kellen Moore | 5 | DAL,PHI | 0.56 | 0.34 | 0.30 | 0% |
| Byron Leftwich | 4 | TB | 0.61 | 0.33 | 0.32 | 0% |
| Shane Steichen | 7 | LAC,PHI,IND | 0.37 | 0.25 | 0.27 | 43% |
| Edgar Bennett | 3 | GB | 0.53 | 0.25 | 0.34 | 0% |
| Frank Reich | 6 | LAC,IND | 0.33 | 0.21 | 0.28 | 67% |

Bottom 10:

| person | seasons | franchises | mean z | rating | SE | % unverified |
|---|---|---|---|---|---|---|
| Mike Sullivan | 3 | TB,NYG | -0.51 | -0.24 | 0.34 | 0% |
| Pat Shurmur | 4 | CLE,MIN,DEN | -0.47 | -0.26 | 0.32 | 25% |
| Chan Gailey | 3 | BUF,NYJ,MIA | -0.57 | -0.27 | 0.34 | 33% |
| Pep Hamilton | 3 | IND,HOU | -0.57 | -0.27 | 0.34 | 0% |
| Dowell Loggains | 4 | TEN,CHI,MIA | -0.52 | -0.28 | 0.32 | 0% |
| Marty Mornhinweg | 4 | PHI,NYJ,BAL | -0.79 | -0.43 | 0.32 | 0% |
| Scott Turner | 3 | WSH | -0.93 | -0.44 | 0.34 | 0% |
| Nathaniel Hackett | 4 | BUF,JAX,NYJ | -0.83 | -0.46 | 0.32 | 0% |
| Mike McCoy | 4 | DEN,ARI | -1.11 | -0.61 | 0.32 | 0% |
| Greg Olson | 3 | OAK,JAX | -1.31 | -0.62 | 0.34 | 0% |

Notes: Andy Reid's and Sean Payton's rows are 100% "unverified" basis
(`model_knowledge_unverified` — a general-knowledge guess never checked
against a Wikipedia infobox), which is the study's known trade-off: they
are two of football's most-credited play-callers, so the ratings agree
with common knowledge, but strictly by our sourcing rules these are
guesses, not evidence-backed facts.

## Play-caller ratings — defense (>= 3 seasons, ranked by shrunk rating)

Top 20:

| person | seasons | franchises | mean z | rating | SE | % unverified |
|---|---|---|---|---|---|---|
| Jim Schwartz | 9 | BUF,PHI,CLE | 0.92 | 0.53 | 0.24 | 0% |
| Wade Phillips | 6 | HOU,DEN,LAR | 1.09 | 0.52 | 0.26 | 0% |
| Mike Macdonald | 4 | BAL,SEA | 1.24 | 0.46 | 0.29 | 50% |
| DeMeco Ryans | 5 | SF,HOU | 1.00 | 0.43 | 0.27 | 60% |
| Vic Fangio | 14 | SF,CHI,DEN,MIA,PHI | 0.62 | 0.42 | 0.20 | 21% |
| Jack Del Rio | 5 | DEN,WSH | 0.85 | 0.37 | 0.27 | 0% |
| Dan Quinn | 10 | SEA,ATL,DAL | 0.57 | 0.34 | 0.23 | 50% |
| Mike Zimmer | 11 | CIN,MIN,DAL | 0.52 | 0.33 | 0.22 | 64% |
| Keith Butler | 7 | PIT | 0.57 | 0.29 | 0.25 | 0% |
| Dennis Allen | 9 | DEN,NO,CHI | 0.50 | 0.29 | 0.24 | 11% |
| Todd Bowles | 13 | ARI,NYJ,TB | 0.42 | 0.28 | 0.21 | 62% |
| Chuck Pagano | 3 | BAL,CHI | 0.89 | 0.28 | 0.30 | 0% |
| Kris Richard | 3 | SEA | 0.88 | 0.27 | 0.30 | 0% |
| Sean McDermott | 6 | CAR,BUF | 0.56 | 0.26 | 0.26 | 17% |
| Brandon Staley | 4 | LAR,LAC,NO | 0.66 | 0.25 | 0.29 | 50% |
| Romeo Crennel | 6 | KC,HOU | 0.38 | 0.18 | 0.26 | 17% |
| Brian Flores | 6 | MIA,MIN | 0.37 | 0.18 | 0.26 | 50% |
| Gregg Williams | 6 | NO,LAR,CLE,NYJ | 0.34 | 0.16 | 0.26 | 0% |
| Steve Wilks | 3 | CAR,CLE,SF | 0.50 | 0.15 | 0.30 | 0% |
| Joe Woods | 4 | DEN,CLE | 0.41 | 0.15 | 0.29 | 0% |

Bottom 10:

| person | seasons | franchises | mean z | rating | SE | % unverified |
|---|---|---|---|---|---|---|
| Dom Capers | 7 | GB | -0.39 | -0.20 | 0.25 | 0% |
| Lou Anarumo | 7 | CIN,IND | -0.42 | -0.22 | 0.25 | 0% |
| Paul Guenther | 6 | CIN,OAK | -0.49 | -0.23 | 0.26 | 0% |
| Nick Rallis | 3 | ARI | -0.82 | -0.25 | 0.30 | 0% |
| Matt Eberflus | 7 | IND,CHI,DAL | -0.51 | -0.26 | 0.25 | 29% |
| Jim Haslett | 4 | WSH | -0.70 | -0.26 | 0.29 | 0% |
| Bob Babich | 3 | JAX | -0.87 | -0.27 | 0.30 | 0% |
| Mike Nolan | 4 | ATL,DAL | -0.74 | -0.28 | 0.29 | 0% |
| Joe Barry | 5 | WSH,GB | -0.67 | -0.29 | 0.27 | 0% |
| Mel Tucker | 3 | JAX,CHI | -1.33 | -0.41 | 0.30 | 0% |

## Offense, QB-adjusted (top 20)

The crossed model splits each team-season's EPA into a caller effect and a
primary-QB effect at once, with the two ridge penalties (λ_caller=20,
λ_qb=2) chosen by leave-one-season-out cross-validation
(`data/processed/playcaller_qb_model_cv.csv`). That crossed model's CV
error (0.763) beat a caller-only model (0.853) and was about equal to a
QB-only model (0.764) — i.e. across this whole dataset, knowing the QB
predicts next season's offense EPA about as well as knowing the caller
does, and the two together do only marginally better than QB alone. This
is a caution sign for the whole exercise, not just a caveat: a decent share
of what looks like "caller" signal in the unadjusted table above may
really be "which QB he happened to have."

| person | rating (QB-adjusted) | seasons | distinct QBs | separable |
|---|---|---|---|---|
| Andy Reid | 0.162 | 12 | 3 | yes |
| Kyle Shanahan | 0.134 | 15 | 7 | yes |
| Greg Roman | 0.120 | 11 | 5 | yes |
| Ben Johnson | 0.113 | 4 | 2 | yes |
| Josh McDaniels | 0.108 | 12 | 5 | yes |
| Sean McVay | 0.101 | 12 | 4 | yes |
| Todd Haley | 0.087 | 6 | 1 | yes |
| Darrell Bevell | 0.081 | 7 | 2 | yes |
| Chip Kelly | 0.077 | 2 | 2 | yes |
| Ken Whisenhunt | 0.076 | 5 | 2 | yes |
| Todd Monken | 0.075 | 7 | 3 | yes |
| Shane Steichen | 0.074 | 7 | 6 | yes |
| Matt LaFleur | 0.072 | 8 | 3 | yes |
| Joe Brady | 0.065 | 3 | 2 | yes |
| Joe Philbin | 0.064 | 1 | 1 | yes |
| Gary Kubiak | 0.057 | 2 | 2 | yes |
| Mike McDaniel | 0.054 | 4 | 1 | yes |
| Liam Coen | 0.053 | 2 | 2 | yes |
| Shane Waldron | 0.052 | 3 | 2 | yes |
| Bill Callahan | 0.047 | 3 | 1 | yes |

Every one of these top 20 happens to be `separable` in our data (every one
of them shared his primary QB, at some point, with a different caller
elsewhere) — no flagged non-separable cases made the top 20, though the
flag does trigger elsewhere in the full file for one-team, one-QB careers.

How the ranking changes: Andy Reid stays #1 in both versions. The biggest
mover is **Kyle Shanahan**, who jumps from 15th (unadjusted rating 0.40)
to 2nd (QB-adjusted 0.134) — he worked with seven different primary QBs
across four franchises, so the model credits him more once his QB mix
(which includes several below-average starters) is accounted for. The
QB-effects sanity file (`qb_effects_from_caller_model.csv`) puts **Drew
Brees, Patrick Mahomes, Tom Brady, and Aaron Rodgers** at the top — the
recognisable-name check the plan asked for.

## Moves summary — the four-way comparison

(`data/processed/playcaller_moves_summary.csv`, EPA z, mean ± SE)

| unit | quantity | n | mean | SE |
|---|---|---|---|---|
| offense | arrival_change (new team, before → with him) | 52 | +0.19 | 0.16 |
| offense | departure_change (old team, with him → after he left) | 64 | -0.23 | 0.12 |
| offense | baseline: all unit-seasons, year over year | 346 | -0.02 | 0.06 |
| offense | baseline: teams starting in the bottom tercile | 116 | +0.64 | 0.09 |
| offense | baseline: teams starting in the middle tercile | 115 | -0.01 | 0.08 |
| offense | baseline: teams starting in the top tercile | 115 | -0.69 | 0.09 |
| defense | arrival_change | 50 | -0.02 | 0.21 |
| defense | departure_change | 54 | -0.09 | 0.17 |
| defense | baseline: all unit-seasons, year over year | 365 | +0.03 | 0.06 |
| defense | baseline: teams starting in the bottom tercile | 122 | +0.80 | 0.10 |
| defense | baseline: teams starting in the middle tercile | 121 | -0.05 | 0.08 |
| defense | baseline: teams starting in the top tercile | 122 | -0.64 | 0.09 |

Reading this: a team that hires a new offensive play-caller improves by
about 0.19 z on average, but a team in the bottom performance tercile
(which is exactly the situation most hires happen in) improves by 0.64 z
on average *regardless of who they hire* — most of the arrival bump is
regression to the mean, not evidence the new hire himself caused it. The
departure numbers tell a similar story in reverse for offense (-0.23 on
departure vs -0.69 for a top-tercile team generally): teams that lose
their offensive play-caller were often good, and would have regressed
somewhat even if he had stayed. Defense shows almost no net arrival or
departure effect (both close to zero, with wide standard errors) once
you consider that these coordinator moves are a small, noisy sample (50-54
moves) against baselines nearly ten times larger.

## Ben Johnson and Mike Macdonald

- **Ben Johnson**: 4 offense seasons, DET 2022-2024 (OC) then CHI 2025
  (HC, proposed play-caller). Career mean z_epa = 1.12, one of the
  highest in the dataset, but with only 4 seasons the shrunk rating is
  pulled down to 0.61 and carries the widest standard error (0.32) among
  ranked offensive callers — the data supports "excellent by the numbers
  so far" but cannot yet rule out a good deal of luck or a QB effect
  (Jared Goff, then Caleb Williams). QB-adjusted rating is 0.113 (5th
  among ranked offense callers), still strong after removing QB credit.
- **Mike Macdonald**: 4 defense seasons, BAL 2022-2023 (DC) then SEA
  2024-2025 (HC, proposed play-caller). Career mean z_epa = 1.24 — the
  single highest average among defensive coordinators with >= 3 seasons
  — shrunk to 0.46 with SE 0.29, reflecting that defensive shrinkage is
  stronger (defense needs ~7 seasons for half weight vs ~3 for offense).
  With only two franchises and four seasons, the data cannot separate "he
  is an unusually good defensive play-caller" from "he inherited strong
  defensive personnel at both stops" — the study can say his units have
  outperformed expectation every year measured, not that he caused it.

## Coaching trees

Corrected in review (Fable, 2026-09-27). The first version of this table
counted a coordinator as "became head coach" if he was EVER a head coach in
the data, which credited Sean McVay with Wade Phillips and Ron Rivera with
Jack Del Rio, men who had been head coaches before joining those staffs. A
protege now counts only if his head-coaching seasons come after his first
season under the mentor; earlier head coaches are listed separately in
`n_already_head_coach`.

Largest trees by coordinators who later became head coaches (2011-2025,
head coach and coordinator titles only):

| Mentor | Coordinators | Later head coaches | Who |
|---|---|---|---|
| Pete Carroll | 10 | 4 | Brian Schottenheimer; Dan Quinn; Darrell Bevell; Gus Bradley |
| Sean McVay | 8 | 4 | Brandon Staley; Kevin O'Connell; Liam Coen; Matt LaFleur |
| John Fox | 6 | 4 | Adam Gase; Dennis Allen; Mike McCoy; Vic Fangio |
| Mike McCarthy | 10 | 3 | Brian Schottenheimer; Joe Philbin; Kellen Moore |
| Ron Rivera | 9 | 3 | Rob Chudzinski; Sean McDermott; Steve Wilks |
| Dan Campbell | 7 | 3 | Aaron Glenn; Ben Johnson; Zac Taylor |
| Frank Reich | 7 | 3 | Matt Eberflus; Nick Sirianni; Thomas Brown |
| Nick Sirianni | 7 | 3 | Jonathan Gannon; Kellen Moore; Shane Steichen |
| Kyle Shanahan | 6 | 3 | DeMeco Ryans; Mike McDaniel; Robert Saleh |
| Bill Belichick | 4 | 3 | Bill O'Brien; Josh McDaniels; Matt Patricia |

Caveats. Interim head-coaching stints count (Darrell Bevell, Thomas
Brown), and an interim head coach counts as a mentor (Zac Taylor appears
under Dan Campbell because both were interim appointments at Miami in
2015). Head-coaching jobs before 2011 are outside the data, so "already a
head coach" is an undercount. The tree sees only coordinators and head
coaches, not position coaches, so most of any real coaching tree is
invisible here.

## Limitations (candid)

- **Play calling is not separable from players or head coach by scores
  alone.** Every number in this report is associated with a person and a
  team-season, not proven to be caused by his decisions. The QB-adjusted
  model in Phase 3 is a partial attempt to separate caller from
  quarterback, and even it shows the crossed model barely beats a
  QB-only model in cross-validated accuracy — a real limit on how much of
  "offensive rating" can honestly be called the play-caller's doing.
- **Many play-caller assignments are unverified guesses**, not
  Wikipedia-sourced facts: 145 of 960 draft rows are `model_knowledge_
  unverified` and 59 more are `default_no_coordinator_headcoach` (no
  titled coordinator found, so the head coach was assumed by default).
  `share_unverified` is carried on every career row so a reader can see
  how much of a given rating rests on an unchecked guess — several
  well-known names (Reid, Payton) are 100% unverified basis despite
  being obviously correct, and some career averages further down the
  list may rest entirely on defaults that turn out to be wrong.
- **Defensive results are noisier than offensive ones.** The variance
  components show defensive coordinators need roughly twice as many
  seasons (about 7 vs about 3) before their track record earns as much
  trust as an offensive coordinator's, so defensive rankings should be
  read with wider error bars in mind even where an SE column looks
  similar in size to offense's.
- **Small samples dominate the person-level lists.** Most coordinators
  have between 3 and 7 seasons in the role; shrinkage pulls short careers
  toward the league mean, but it cannot manufacture evidence that isn't
  there — a 3-season rating and its 0.30+ standard error should not be
  read as a settled verdict.
- **Mid-season changes were excluded outright** (96 of 960 draft rows),
  along with rows naming more than one play-caller or naming none. This
  keeps the season-level model clean but means some real, sometimes
  informative in-season coaching changes are invisible to every table
  here.
- **The metrics themselves (EPA, explosive rate, yards/play, and the
  points that ultimately follow from them) reflect much more than play
  calling** — the offensive line, the secondary, injuries, luck on
  fumbles and interceptions, and opposing talent all flow through the
  same box score. The opponent adjustment in Phase 2 controls for
  schedule strength, not for any of this.
- **The moves analysis is a small, noisy sample** (50-64 moves per unit)
  set against baselines that are themselves imprecise; the tercile-matched
  baseline is the fairest comparison offered, but even it is built from
  the same 15 seasons of data and shares all of the above limitations.

Everything above is offered as "associated with," never "caused by."
