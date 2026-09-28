# Phase 1a report: staff table extended to 2011-2025, turned into stints

480 team-seasons (32 franchises x 2011-2025). Every name in every CSV
listed below comes from a fetched Wikipedia page (raw wikitext,
`action=raw`); see `data/raw/SOURCE.md` for the fetch log summary.

## Coverage by season

Count of team-seasons (out of 32) with at least one named holder of each
role:

| Season | HC | OC | DC |
|---|---|---|---|
| 2011 | 32 | 14 | 15 |
| 2012 | 32 | 32 | 31 |
| 2013 | 32 | 32 | 32 |
| 2014 | 32 | 31 | 32 |
| 2015 | 32 | 30 | 31 |
| 2016 | 32 | 29 | 32 |
| 2017 | 32 | 30 | 31 |
| 2018 | 32 | 30 | 30 |
| 2019 | 32 | 31 | 31 |
| 2020 | 32 | 29 | 29 |
| 2021 | 32 | 30 | 30 |
| 2022 | 32 | 30 | 29 |
| 2023 | 32 | 32 | 29 |
| 2024 | 32 | 32 | 31 |
| 2025 | 32 | 32 | 31 |
| **Total** | **480/480** | **444/480** | **444/480** |

Head coach is 100% covered, every year. Offensive and defensive
coordinator coverage is markedly weaker in 2011 (14/32 OC, 15/32 DC) than
any other year in range - 2011 team-season pages, on this evidence, are
disproportionately likely to have only a head-coach infobox field and no
Staff section at all. From 2012 on, coverage sits in the 29-32 range every
year with no further trend by age; the mid-2000s-style total blackout that
Phase 0's small spot-check worried about did not reappear once inside
2011-2025, except for 2011 itself.

## Every team-season missing a named OC (36)

Reproduced in full from `data/processed/staff_by_season.csv` (`n_oc == 0`):

2011: ARI, BUF, CAR, CHI, CLE, DAL, IND, LAC, LAR, MIA, MIN, NYG, NYJ, OAK,
PHI, SEA, TB, TEN (18 team-seasons - see "2011 is weak" above; each of
these rows' `raw_note` shows only a `head_coach infobox raw:` line, i.e.
the page had nothing else usable for OC); 2014 HOU; 2015 NYJ, PHI; 2016
BUF, CLE, MIN; 2017 CLE, HOU; 2018 GB, HOU; 2019 ARI; 2020 ARI, DET, PHI;
2021 ARI, MIA; 2022 ARI, NE (this is the *only* NE season in range missing
an OC - New England's OC is named in the other 14 of its 15 seasons,
mostly Josh McDaniels).

## Every team-season missing a named DC (36)

2011: ARI, BUF, CAR, CHI, IND, LAC, LAR, MIA, MIN, NE, NYG, NYJ, OAK, PHI,
SEA, TB, TEN (17 team-seasons); 2012 KC; 2015 NYJ; 2017 NYG; 2018 CIN, NE;
2019 ATL; 2020 MIN, NE, TEN; 2021 MIN, NE; 2022 HOU, NE, TB; 2023 BUF, NE,
TB; 2024 TB; 2025 TB.

Notable patterns: **New England (NE) is missing a DC in 6 of 15 seasons**
(2011, 2018, 2020, 2021, 2022, 2023) but its OC only once (2022) - the
opposite emphasis from what a first pass at this report drafted (an
error caught and corrected before this version; see "problems found" for
what caused the mix-up). **Tampa Bay (TB) has a titled DC in 2012-2021 (10
straight seasons: Bill Sheridan, Leslie Frazier, Mike Smith, Mark Duffner,
then Todd Bowles as HC-and-DC 2019-2021) but no titled DC at all in 2011 or
in any of 2022-2025** - consistent with Phase 0's finding for 2022-2024,
now confirmed to extend through 2025 and to not be a permanent franchise
pattern (it has a normal, separately-titled DC for a full decade in the
middle of this range).

## Multi-holder team-seasons (57)

57 of 480 team-seasons have more than one name in at least one role (mostly
mid-season coaching changes; a handful of co-coordinators). Full list is in
`data/processed/staff_stints.csv` (filter `n_holders_that_season > 1`) and
summarized in the table below (head coach / OC / DC columns show every name
found, in page order):

| Season | Team | Head coach | OC | DC |
|---|---|---|---|---|
| 2011 | JAX | Jack Del Rio \| Mel Tucker | Dirk Koetter | Mel Tucker |
| 2011 | KC | Todd Haley \| Romeo Crennel | Bill Muir | Romeo Crennel |
| 2011 | MIA | Tony Sparano \| Todd Bowles | - | - |
| 2012 | BAL | John Harbaugh | Cam Cameron \| Jim Caldwell | Dean Pees |
| 2012 | IND | Chuck Pagano \| Bruce Arians | Bruce Arians | Greg Manusky |
| 2012 | NO | Sean Payton \| Joe Vitt \| Aaron Kromer \| Sean Payton† | Pete Carmichael Jr. | Steve Spagnuolo |
| 2012 | PHI | Andy Reid | Marty Mornhinweg | Juan Castillo \| Todd Bowles |
| 2012 | TEN | Mike Munchak | Chris Palmer \| Dowell Loggains | Jerry Gray |
| 2013 | DEN | John Fox \| Jack Del Rio | Adam Gase | Jack Del Rio |
| 2013 | HOU | Gary Kubiak \| Wade Phillips | Rick Dennison | Wade Phillips |
| 2014 | OAK | Dennis Allen \| Tony Sparano | Greg Olson | Jason Tarver |
| 2015 | DET | Jim Caldwell | Joe Lombardi \| Jim Bob Cooter | Teryl Austin |
| 2015 | MIA | Joe Philbin \| Dan Campbell | Zac Taylor | Lou Anarumo |
| 2015 | NO | Sean Payton | Pete Carmichael Jr. | Rob Ryan \| Dennis Allen |
| 2015 | PHI | Chip Kelly \| Pat Shurmur | - | Billy Davis |
| 2015 | TEN | Ken Whisenhunt \| Mike Mularkey | Jason Michael | Ray Horton |
| 2016 | BAL | John Harbaugh | Marc Trestman \| Marty Mornhinweg | Dean Pees |
| 2016 | BUF | Rex Ryan \| Anthony Lynn | - | Dennis Thurman |
| 2016 | DEN | Gary Kubiak \| Joe DeCamillis | Rick Dennison | Wade Phillips |
| 2016 | JAX | Gus Bradley \| Doug Marrone | Greg Olson \| Nathaniel Hackett | Todd Wash |
| 2016 | KC | Andy Reid | Brad Childress \| Matt Nagy | Bob Sutton |
| 2016 | LAR | Jeff Fisher \| John Fassel | Rob Boras | Gregg Williams |
| 2016 | MIN | Mike Zimmer \| Mike Priefer | - | George Edwards |
| 2017 | CIN | Marvin Lewis | Ken Zampese \| Bill Lazor | Paul Guenther |
| 2017 | NYG | Ben McAdoo \| Steve Spagnuolo | Mike Sullivan | - |
| 2018 | BAL | John Harbaugh | Marty Mornhinweg \| Greg Roman | Don Martindale |
| 2018 | CLE | Hue Jackson \| Gregg Williams | Freddie Kitchens \| Todd Haley | Blake Williams |
| 2018 | GB | Mike McCarthy \| Joe Philbin | - | Mike Pettine |
| 2018 | JAX | Doug Marrone | Nathaniel Hackett \| Scott Milanovich | Todd Wash |
| 2019 | CAR | Ron Rivera \| Perry Fewell | Norv Turner | Eric Washington |
| 2019 | WSH | Jay Gruden \| Bill Callahan | Kevin O'Connell | Greg Manusky |
| 2020 | ATL | Dan Quinn \| Raheem Morris | Dirk Koetter | Jeff Ulbrich |
| 2020 | CLE | Kevin Stefanski \| Mike Priefer | Alex Van Pelt | Joe Woods |
| 2020 | DET | Matt Patricia \| Darrell Bevell \| Robert Prince | - | Cory Undlin |
| 2020 | HOU | Bill O'Brien \| Romeo Crennel | Tim Kelly | Anthony Weaver |
| 2021 | CAR | Matt Rhule | Joe Brady \| Jeff Nixon | Phil Snow |
| 2021 | CHI | Matt Nagy \| Chris Tabor | Bill Lazor | Sean Desai |
| 2021 | JAX | Urban Meyer \| Darrell Bevell | Brian Schottenheimer | Joe Cullen |
| 2021 | NYG | Joe Judge | Jason Garrett \| Freddie Kitchens | Patrick Graham |
| 2021 | OAK | Jon Gruden \| Rich Bisaccia | Greg Olson | Gus Bradley |
| 2022 | CAR | Matt Rhule \| Steve Wilks | Ben McAdoo | Al Holcomb |
| 2022 | DEN | Nathaniel Hackett \| Jerry Rosburg | Justin Outten | Ejiro Evero |
| 2022 | IND | Frank Reich \| Jeff Saturday | Parks Frazier | Gus Bradley |
| 2022 | MIA | Mike McDaniel | Frank Smith | Vic Fangio \| Josh Boyer |
| 2022 | NO | Dennis Allen | Pete Carmichael Jr. | Ryan Nielsen \| Kris Richard (co-holders) |
| 2023 | BUF | Sean McDermott | Ken Dorsey \| Joe Brady | - |
| 2023 | CAR | Frank Reich \| Chris Tabor | Thomas Brown | Ejiro Evero |
| 2023 | LAC | Brandon Staley \| Giff Smith | Kellen Moore | Derrick Ansley |
| 2023 | OAK | Josh McDaniels \| Antonio Pierce | Mick Lombardi \| Bo Hardegree | Patrick Graham |
| 2023 | PIT | Mike Tomlin | Matt Canada \| Eddie Faulkner | Teryl Austin |
| 2023 | WSH | Ron Rivera | Eric Bieniemy | Jack Del Rio \| Ron Rivera |
| 2024 | CHI | Matt Eberflus \| Thomas Brown | Shane Waldron \| Chris Beatty | Eric Washington |
| 2024 | NO | Dennis Allen \| Darren Rizzi | Klint Kubiak | Joe Woods |
| 2024 | NYJ | Robert Saleh \| Jeff Ulbrich | Nathaniel Hackett | Marquand Manuel |
| 2024 | OAK | Antonio Pierce | Luke Getsy \| Scott Turner | Patrick Graham |
| 2025 | NYG | Brian Daboll \| Mike Kafka | Tim Kelly | Charlie Bullen |
| 2025 | TEN | Brian Callahan \| Mike McCoy | Nick Holz | Dennard Wilson |

Only one case is a true co-holder pair rather than a successor pair: 2022
NO defensive coordinator, "Ryan Nielsen and Kris Richard" - split from
prose by the new `AND_SPLIT_RE` rule and marked `is_co_holder=True` in
`staff_stints.csv` (both entries share `order_in_season=1/2` but neither
implies the other left). Every other multi-name row above is presented in
the order the source lists it (2012 NO's "Sean Payton†" trailing entry
is the infobox's own footnote marker for his Bountygate suspension - kept
verbatim, not a name error).

## Head-coach cross-check

Extracted head coach vs. the nflverse schedule file's `home_coach`/
`away_coach` (mapped to franchise ids), compared by last name (does the
Wikipedia head-coach set subset the schedule's coach set for that
team-season): **463 of 480 matched.**

All 17 mismatches, and why (same pattern found in Phase 0: the schedule
file credits every game to the coach who *started* the season, so an
in-season change the wiki page correctly records looks like a mismatch
here even when the wiki page is right):

| Season | Team | Wikipedia head coach(es) | Schedule file coach(es), with games credited |
|---|---|---|---|
| 2012 | IND | Chuck Pagano \| Bruce Arians | Chuck Pagano (17g) |
| 2012 | NO | Sean Payton \| Joe Vitt \| Aaron Kromer \| Sean Payton† | Joe Vitt (10g); Aaron Kromer (6g) |
| 2013 | DEN | John Fox \| Jack Del Rio | John Fox (19g) |
| 2015 | MIA | Joe Philbin \| Dan Campbell | Joe Philbin (16g) |
| 2015 | TEN | Ken Whisenhunt \| Mike Mularkey | Ken Whisenhunt (16g) |
| 2016 | DEN | Gary Kubiak \| Joe DeCamillis | Gary Kubiak (16g) |
| 2016 | LAR | Jeff Fisher \| John Fassel | Jeff Fisher (16g) |
| 2016 | MIN | Mike Zimmer \| Mike Priefer | Mike Zimmer (16g) |
| 2019 | CAR | Ron Rivera \| Perry Fewell | Ron Rivera (16g) |
| 2020 | CLE | Kevin Stefanski \| Mike Priefer | Kevin Stefanski (18g) |
| 2020 | DET | Matt Patricia \| Darrell Bevell \| Robert Prince | Matt Patricia (11g); Darrell Bevell (5g) |
| 2021 | CHI | Matt Nagy \| Chris Tabor | Matt Nagy (17g) |
| 2024 | CHI | Matt Eberflus \| Thomas Brown | Matt Eberflus (17g) |
| 2024 | NO | Dennis Allen \| Darren Rizzi | Dennis Allen (17g) |
| 2024 | NYJ | Robert Saleh \| Jeff Ulbrich | Robert Saleh (17g) |
| 2025 | NYG | Brian Daboll \| Mike Kafka | Brian Daboll (17g) |
| 2025 | TEN | Brian Callahan \| Mike McCoy | Nick Holz? (see below) |

For every row above, one interim-coach name from the wiki page is simply
absent from the schedule file's per-team coach roll-up (either the
schedule file's `home_coach`/`away_coach` column doesn't record the
mid-season change at all, or it uses a spelling/absence that this
cross-check's exact-lastname-subset rule doesn't catch as a match - e.g.
2012 NO where the schedule shows Vitt and Kromer, neither of whom is
"Sean Payton", so no subset relationship exists even though the wiki page
is almost certainly right that Payton nominally remained HC-on-paper
through his suspension). None of these looks like a Wikipedia parsing
error; every one is a known real in-season coaching change or suspension.
2025 TEN is mid-season as of this writing (2026-09-27 fetch date is itself
after the 2025 season, so this should be a completed season's data,
worth a second look - see "what still needs a human").

## Infobox vs. staff-section disagreements (22)

Every team-season/role where the union merge (`merge_union` in
`pc_extract_staff.py`) drew from both sources but at least one source
had a name the other didn't (by last name):

| Season | Team | Role | Names, tagged by source |
|---|---|---|---|
| 2012 | NO | HC | Sean Payton(infobox); Joe Vitt(infobox); Aaron Kromer(infobox); Sean Payton†(staff_section) |
| 2013 | DEN | HC | John Fox(both); Jack Del Rio(infobox) |
| 2015 | DET | OC | Joe Lombardi(both); Jim Bob Cooter(staff_section) |
| 2015 | NO | DC | Rob Ryan(infobox); Dennis Allen(both) |
| 2016 | BAL | OC | Marc Trestman(both); Marty Mornhinweg(infobox) |
| 2016 | BUF | HC | Rex Ryan(infobox); Anthony Lynn(both) |
| 2016 | DEN | HC | Gary Kubiak(both); Joe DeCamillis(infobox) |
| 2016 | JAX | OC | Greg Olson(both); Nathaniel Hackett(staff_section) |
| 2016 | MIN | HC | Mike Zimmer(both); Mike Priefer(infobox) |
| 2018 | BAL | OC | Marty Mornhinweg(both); Greg Roman(staff_section) |
| 2018 | GB | HC | Mike McCarthy(infobox); Joe Philbin(both) |
| 2018 | JAX | OC | Nathaniel Hackett(both); Scott Milanovich(staff_section) |
| 2020 | CLE | HC | Kevin Stefanski(both); Mike Priefer(infobox) |
| 2020 | DET | HC | Matt Patricia(infobox); Darrell Bevell(both); Robert Prince(infobox) |
| 2021 | CHI | HC | Matt Nagy(both); Chris Tabor(infobox) |
| 2021 | OAK | HC | Jon Gruden(infobox); Rich Bisaccia(both) |
| 2022 | CAR | HC | Matt Rhule(infobox); Steve Wilks(both) |
| 2022 | DEN | HC | Nathaniel Hackett(infobox); Jerry Rosburg(both) |
| 2022 | IND | HC | Frank Reich(infobox); Jeff Saturday(both) |
| 2022 | MIA | DC | Vic Fangio(infobox); Josh Boyer(staff_section) |
| 2023 | PIT | OC | Matt Canada(both); Eddie Faulkner(staff_section) |
| 2023 | WSH | DC | Jack Del Rio(infobox); Ron Rivera(both) |

Same systematic pattern Phase 0 found: the infobox tends to carry the
season's full coaching history (departed + interim), the "NFL final
staff" template tends toward the incumbent at season's end - so almost all
of these are "one source has the fired coach, the other doesn't," not
contradictions about who held the job. The union merge keeps both, which
is the whole point of Task 2(a): nobody who is named on the page gets
silently dropped now, unlike Phase 0's infobox-preferred approach (which
specifically lost 2023 PIT's Eddie Faulkner - that gap is now closed, see
row above where he shows up correctly).

The one case worth separate flagging again: **2022 MIA defensive
coordinator** - infobox says Vic Fangio, staff section says Josh Boyer.
This was already flagged in Phase 0 as likely a stale/wrong Wikipedia edit
(Fangio was hired a year later, for 2023) and is repeated below under
"Reviewer's own knowledge" rather than resolved in the CSV - the union
keeps both names, as data, exactly as the pages say.

## Alias merges and doubtful pairs

`data/reference/person_aliases.csv` (2 merges, both a suffix/punctuation
variant only, the one pattern explicit enough not to be guesswork):

- "Ken Norton Jr" -> "Ken Norton Jr." (missing period)
- "Pete Carmichael" -> "Pete Carmichael Jr." (infobox sometimes drops the
  suffix)

`data/reference/person_doubtful_pairs.csv` (11 same-last-name,
same-first-initial pairs found across the whole 2011-2025 person list,
deliberately **not** merged - a human should look at these before Phase 2
treats them as the same or different people):

Ben Johnson / Brian Johnson; Bill Callahan / Brian Callahan; Bill Davis /
Billy Davis; Bob Babich / Bobby Babich; Jay Gruden / Jon Gruden; Jim
Harbaugh / John Harbaugh; Klay Kubiak / Klint Kubiak; Matt LaFleur / Mike
LaFleur; Pete Carmichael Jr. / "Pete Carmichael, Jr." (this one IS almost
certainly the same person as the alias-merged "Pete Carmichael Jr." above,
just a comma-placement variant the alias code's suffix-only rule didn't
catch - see "what still needs a human"); Rex Ryan / Rob Ryan; Wade
Phillips / Wes Phillips. None of these were merged; every one is a
different person as far as this study's automation can tell (Ben Johnson
the Lions/Bears OC/HC is definitely not Brian Johnson; Jay Gruden and Jon
Gruden are brothers, both real NFL coaches; etc.) except the Carmichael
comma variant just noted.

## Movers

`data/processed/coordinator_moves.csv`: **106 people** held an OC or DC
role for 2+ different franchises somewhere in 2011-2025 (both roles
counted separately - a person who moved as OC and separately as DC counts
once per role list they qualify for).

`data/processed/coordinator_to_headcoach.csv`: **72 people** appear as OC
or DC in some season and as HC in a later season (any franchise). This
count is higher than a first guess might expect because it includes HC
promotions **within the same franchise** (e.g. Aaron Glenn: DET DC
2021-2024, but the table lists his later HC job as NYJ 2025 since that's
a different franchise from where he coordinated - the builder only
requires the HC season be strictly later, not a different team, so an
internal promotion from OC/DC to HC at the same franchise would also
appear here if the data had one). All three named anchors are present with
exactly the seasons and franchises specified: Ben Johnson (DET OC
2022-2024, CHI HC 2025), Mike Macdonald (BAL DC 2022-2023, SEA HC
2024-2025), and Kyle Shanahan (OC for WSH 2011-2013, CLE 2014, and ATL
2015-2016 - three different franchises - before SF HC starting 2017).

## Problems found and how they were handled

- **Suffix tokens broke last-name matching in the union merge.** The
  original `merge_union` compared names by taking the last whitespace
  token, so "Pete Carmichael Jr." matched on "Jr." instead of
  "Carmichael" - it never matched the infobox's "Pete Carmichael Jr." (or
  bare "Pete Carmichael") against the staff section's copy of the same
  name, so New Orleans' 2015-2022 offensive-coordinator rows all had a
  duplicate Pete Carmichael entry (once tagged `infobox`, once
  `staff_section`) before this was caught. Fixed by stripping a trailing
  Jr./Sr./II/III/IV token before taking the last name in `merge_union`
  (`src/pc_extract_staff.py`). Caught by inspecting the
  infobox-vs-staff-section disagreement list this report needed anyway -
  eight rows all showing "Pete Carmichael Jr." disagreeing with itself was
  an obvious tell. Re-ran the full extraction (all 480 pages already
  cached, so this needed zero new network requests) and rebuilt every
  downstream table after the fix; the numbers in this report are
  post-fix.
- **2011 has much weaker coordinator coverage than every other year in
  range** (14/32 OC, 15/32 DC vs. 29-32 in every other season). Handled by
  reporting it plainly above rather than guessing at missing names; no
  coordinator name for any of those 18 team-seasons was invented.
- **The "and"-prose co-coordinator case** (2022 New Orleans DC, "Ryan
  Nielsen and Kris Richard") is now split into two co-holder rows by a new
  regex (`AND_SPLIT_RE`) that only fires when both sides of "X and Y" look
  like a two-token capitalized name - deliberately narrow, to avoid
  mis-splitting a name that happens to contain "and" as part of a longer
  annotation.
- **Annotations are now kept as notes instead of dropped.**
  `split_name_segments_detailed` captures every parenthetical and any
  text after a semicolon into a `note` field instead of discarding it, so
  "(interim)", "(fired November 27)", "(weeks 1-11)" and similar all
  survive into `staff_stints.csv`'s `note` column, and `is_interim` is set
  whenever "interim" appears (case-insensitive) in that note.
- **A first draft of this report's "missing OC"/"missing DC" lists was
  wrong** - written from a stale intermediate scratch file that predated a
  final re-run, it swapped some of the OC and DC gap patterns (claiming
  New England was missing 7 OCs, and Tampa Bay was missing a DC in all 15
  seasons). Caught by re-querying `staff_by_season.csv` directly rather
  than trusting the earlier scratch CSV before finishing this report; the
  lists above are freshly recomputed from the actual committed CSV. 2012
  KC's offensive coordinator (Brian Daboll) is in fact correctly extracted
  (`n_oc=1`) - it was never actually missing.

## Reviewer's own knowledge (unverified)

Per the task's hard rule, nothing below is in any CSV - it's the author's
own outside knowledge, offered only as a pointer for a human reviewer:

- **2022 MIA defensive coordinator**: the infobox's "Vic Fangio" value
  looks like a stale/wrong Wikipedia edit; Fangio was Miami's DC starting
  in 2023, not 2022 (Josh Boyer, the staff section's answer, is the
  coordinator this reviewer believes actually held the job in 2022). Same
  call as Phase 0 made for this exact row.
- **2025 TEN head coach**: the schedule-file coach name "Nick Holz" showing
  up in the games.csv join for TEN 2025 in place of a head coach looks
  wrong to this reviewer (Nick Holz's football-name recognition, if that
  is even the right person, is not as a Tennessee Titans head coach) -
  worth checking whether the schedule file's `home_coach`/`away_coach`
  columns are populated correctly for 2025, or whether this is a franchise
  mapping problem in `xe_metrics.to_franchise` rather than a Wikipedia
  problem specifically. Not corrected in any CSV; flagged for a human.

## What still needs a human

- **"Pete Carmichael Jr." vs "Pete Carmichael, Jr."** (comma placement):
  should probably be a third alias merge, but the alias builder's
  suffix-only regex only strips a trailing suffix token, not a
  suffix-with-leading-comma - needs either a small regex extension or a
  manual add to `person_aliases.csv`, with the same caution about not
  merging on guesswork applied to everything else in that file.
- **2025 TEN head-coach cross-check mismatch** (see "Reviewer's own
  knowledge") deserves a look at whether the schedule file or the
  franchise crosswalk, not the Wikipedia extraction, is at fault.
- **11 doubtful person-name pairs** in
  `data/reference/person_doubtful_pairs.csv` are unresolved by design;
  Phase 2 should not silently treat any of them as the same person.
- **1999-2010 and 2026+ are still out of scope** for this phase; Phase 0's
  spot-check already found 2005-era pages can carry nothing but a head
  coach, so a similar or worse coverage profile to 2011's should be
  expected if the range is extended further back.
- The **union-merge disagreement list above (22 rows)** is presented as
  data for a human, not resolved by this phase - Phase 1's hand-built
  play-caller-override table is explicitly where these should get a
  confidence-graded, sourced answer, per the study's plan.

## What Wikipedia tells us, and what it doesn't (carried over from Phase 0)

Wikipedia's team-season pages report who held the job **title** of head
coach, offensive coordinator, or defensive coordinator. They do not report
who actually **called plays** on a given Sunday, and nothing in this
phase's CSVs should be read that way - that gap is what Phase 1's hand-built,
sourced, confidence-graded play-caller-override table is for.

## Files produced or changed this phase

- `src/pc_extract_staff.py` - added `split_name_segments_detailed` (keeps
  annotations as notes, splits "X and Y" prose into co-holders),
  `merge_union` (union of infobox + staff-section segments in page order,
  tagged by source), `load_team_wiki_names_seasonal` /
  `wiki_name_for_season` (season-aware team names), `extract_team_season_v2`
  / `run_v2` (the union-based pipeline), and a `--mode full` CLI path.
  The original Phase 0 functions/behavior (`split_name_segments`,
  `extract_team_season`, `run`, `--mode phase0` default) are unchanged.
- `src/pc_build_derived.py` - new: builds `person_aliases.csv`,
  `person_doubtful_pairs.csv`, applies aliases to `staff_stints.csv`, and
  builds `coordinator_moves.csv` / `coordinator_to_headcoach.csv`.
- `src/pc_headcoach_check.py` - added `--staff-path`/`--out` CLI args so it
  can run against either the Phase 0 or Phase 1a staff table.
- `data/reference/team_wiki_names.csv` - now season-aware
  (`valid_from_season`/`valid_to_season` columns) for the four
  relocated/renamed franchises.
- `data/processed/staff_by_season.csv` - 480 rows.
- `data/processed/staff_stints.csv` - 1,432 rows (one per season, franchise,
  role, person).
- `data/processed/staff_headcoach_check.csv` - 480 rows.
- `data/processed/coordinator_moves.csv` - 106 rows.
- `data/processed/coordinator_to_headcoach.csv` - 72 rows.
- `data/reference/person_aliases.csv` - 2 rows.
- `data/reference/person_doubtful_pairs.csv` - 11 rows.
- `data/raw/SOURCE.md` - Phase 1a addendum with the new fetch count.
- `tests/test_pc_extract_staff.py` - 15 new tests (detailed-segment
  parsing, union merge, season-aware team names, the three anchor cases on
  `staff_stints.csv`, and the movers/aliases builders with inline frames).
  24 tests total, all passing.
- `data/processed/staff_phase0.csv` and
  `data/processed/staff_phase0_headcoach_check.csv` - unchanged, as
  instructed.
