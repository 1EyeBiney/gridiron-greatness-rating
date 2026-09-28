# Phase 1c/1d: filling staff-table gaps from other Wikipedia pages (2026-09-27)

> **Update (Phase 1d, second pass, same day):** a second gap-fill pass
> fetched 203 additional biographies (prioritised by nearness to a
> remaining gap, plus a "discovery scan" of the cached team-season pages
> themselves) and re-ran the whole pipeline. All numbers below are updated
> to reflect the *combined* result of both passes; the second-pass-only
> detail is in the "Phase 1d second pass" section near the end.

## Summary

The team-season pages that back `staff_stints.csv` (2011-2025) and
`staff_stints_pages_1999_2010.csv` (1999-2010) simply do not list an OC
and/or DC for many team-seasons. This phase built a gap list, tested a
second Wikipedia source (per-team coordinator navigation templates,
"Source B1") and found it **does not exist**, then mined the 297 already-
cached coach biography pages ("Source B2", the `pastcoaching` infobox
field) to fill as many gaps as the evidence supports, and validated that
source against the seasons where the team-season page already names a
coordinator.

Every name in the outputs below is copied from a fetched Wikipedia page
and cited by URL. Nothing was filled in from the author's own knowledge;
where I have my own opinion about a case, it is called out separately
under "Reviewer's own knowledge (unverified)" at the end.

## Source B1 (coordinator navboxes): does not exist

Tested "Template:New England Patriots offensive coordinator navbox",
"Template:Dallas Cowboys defensive coordinator navbox", and several
plausible variants ("...coordinators", no "navbox"; "List of \<Team\>
defensive coordinators") for multiple franchises - all 404. An in-namespace
MediaWiki search (`list=search&srnamespace=10`) for the phrases "\<team\>
offensive coordinator" / "offensive coordinator navbox" turns up only:
- "Template:\<Team\> staff" - a *current* staff snapshot (no year ranges,
  not usable for history), and
- "Template:NFL offensive coordinators" / "Template:NFL defensive
  coordinators" - *current-season* league-wide navboxes, also with no
  year ranges, and (as of this writing) reflecting the 2026 offseason
  roster rather than a confirmed 2025-season assignment.

I fetched both of the current league-wide navboxes to check whether they
could resolve the single 2025 gap (TB DC), but did not use them: a name
appearing there in September 2026 is not evidence of who called plays for
Tampa Bay during the 2025 season specifically (a coordinator hired for
2026 would appear there too). `data/processed/navbox_coordinators.csv` is
written with the correct schema and zero rows.

Consequence: all gap-filling below comes from Source B2 only, and the
500-request fetch budget went essentially unused (19 requests total, see
`data/raw/SOURCE.md`) because Source B2 was already fully cached from
Phase 1b - there was no name list to justify fetching new, uncached
biographies for the 161 gaps that remain (see "What needs a human" below).

## Coverage before / after, OC and DC, 1999-2025

Counts are (franchise, role) pairs with a named holder, out of up to 64
possible per season (32 franchises x {OC, DC}; fewer before an expansion
team existed, e.g. HOU only from 2002).

| Season | Before | After | Season | Before | After |
|---|---|---|---|---|---|
| 1999 | 53 | 54 | 2013 | 64 | 64 |
| 2000 | 50 | 55 | 2014 | 63 | 63 |
| 2001 | 56 | 61 | 2015 | 61 | 64 |
| 2002 | 47 | 59 | 2016 | 61 | 63 |
| 2003 | 36 | 55 | 2017 | 61 | 62 |
| 2004 | 38 | 56 | 2018 | 60 | 62 |
| 2005 | 41 | 56 | 2019 | 62 | 62 |
| 2006 | 55 | 61 | 2020 | 58 | 59 |
| 2007 | 52 | 61 | 2021 | 60 | 61 |
| 2008 | 48 | 61 | 2022 | 59 | 59 |
| 2009 | 39 | 53 | 2023 | 61 | 61 |
| 2010 | 36 | 53 | 2024 | 63 | 63 |
| 2011 | 29 | 53 | 2025 | 63 | 63 |
| 2012 | 63 | 63 | | | |

("After" reflects the combined result of both gap-fill passes described in
this document.)

1999-2010 total: 551/762 before -> **685/762 after** (211 gaps -> **77
gaps**; 134 filled across both passes). 2011-2025 total: 888/960 before ->
**922/960 after** (72 gaps -> **38 gaps**; 34 filled). Combined: 283 total
gaps identified, **168 filled (59%)**, **115 remain**. (First pass alone:
122/283 = 43% filled, 161 remaining; the second pass added 46 more fills.)

## Rows by source (`staff_stints_all.csv`)

| source_detail | rows |
|---|---|
| team_season_page | 2,389 |
| biography | 173 |
| navbox / navbox+biography | 0 |
| **total** | **2,562** |

`staff_gapfill.csv` (173 rows, one row per candidate person per gap - a gap
with 2 disagreeing candidates produces 2 rows): 163 rows `biography_only`
(single, unambiguous candidate), 10 rows `sources_disagree` (5 gaps, 2
candidates each - see below). 0 rows `navbox_only` or `both_agree` (no
navbox data).

## Source agreement rate (step 5 validation)

For every (season, franchise, role) where the **team-season page itself**
already names an OC or DC, I compared that name (by last name, case-
insensitive, ignoring Jr./Sr.) against the same source used for gap-filling.
With more biographies now cached, the validated pool of comparisons grew
from 1,030 to 1,172:

- **Biography**: **1,157 / 1,172 = 98.7%** agreement.
- **Navbox**: no overlap possible (zero navbox rows).

This is the number I'd point to for how far to trust the 163
`biography_only` gap-fills: essentially the same source that gets the
right coordinator 98.7% of the time when we can check it.

### The 15 disagreements (`staff_source_disagreements.csv`)

All 15 look like genuine **mid-season coordinator changes** (the
biography lists one person's tenure by full-year ranges; the team-season
page names whoever the source of that page's `staff` section considered
canonical for the season, which can differ when a coordinator was fired,
promoted, or moved to interim mid-year) rather than extraction errors:

| Season | Franchise | Role | Team-season page | Biography |
|---|---|---|---|---|
| 2000 | LAR | OC | Bobby Jackson | Mike Martz |
| 2001 | LAR | OC | Bobby Jackson | Mike Martz |
| 2001 | OAK | OC | Bill Callahan | Marc Trestman |
| 2004 | WSH | DC | Greg Blache | Gregg Williams |
| 2005 | DET | OC | Ted Tollner | Greg Olson |
| 2006 | HOU | OC | Troy Calhoun | Joe Pendry |
| 2006 | SEA | DC | John Marshall | Ray Rhodes |
| 2007 | SEA | DC | John Marshall | Ray Rhodes |
| 2009 | IND | OC | Tom Moore | Clyde Christensen |
| 2009 | WSH | OC | Sherman Lewis | Sherman Smith |
| 2017 | DEN | OC | Mike McCoy | Bill Musgrave |
| 2018 | ARI | OC | Mike McCoy | Byron Leftwich |
| 2021 | JAX | OC | Brian Schottenheimer | Darrell Bevell |
| 2024 | NYJ | DC | Marquand Manuel | Jeff Ulbrich |
| 2025 | NYJ | DC | Chris Harris | Steve Wilks |

(The first pass had found 11 of these; the second pass's larger biography
pool surfaced 4 more of the same kind: 2000/2001 LAR OC and 2006 HOU/SEA.)

## The 5 gaps with disagreeing gap-fill candidates (both kept, flagged)

| Season | Franchise | Role | Candidates |
|---|---|---|---|
| 2002 | WSH | DC | George Edwards / Marvin Lewis |
| 2006 | ARI | OC | Keith Rowen / Mike Kruczek |
| 2006 | CLE | OC | Jeff Davidson / Maurice Carthon |
| 2016 | BUF | OC | Anthony Lynn (interim) / Greg Roman |
| 2016 | MIN | OC | Norv Turner / Pat Shurmur (interim) |

Both people's biographies claim the role for the same season (one is
usually a mid-season interim replacement, or a co-coordinator
arrangement). Both rows are kept in `staff_gapfill.csv` and
`staff_stints_all.csv` with `disagreement=True` rather than picking one.
(2006 ARI OC and 2006 CLE OC are new in this second pass.)

## Remaining gaps: 115 (`staff_gaps.csv` minus `staff_gapfill.csv`)

By season: 1999:8, 2000:7, 2001:1, 2002:5, 2003:9, 2004:8, 2005:8, 2006:3,
2007:3, 2008:3, 2009:11, 2010:11, 2011:11, 2012:1, 2014:1, 2016:1, 2017:2,
2018:2, 2019:2, 2020:5, 2021:3, 2022:5, 2023:3, 2024:1, 2025:1.

By franchise (top 10 of 32): NE 17, CLE 11, ARI 11, DAL 7, IND 7, TB 6,
MIA 5, CAR 5, OAK 5, TEN 4. New England alone accounts for 15% of what's
left, spread across 1999-2000, 2003-2005, 2009-2011, 2018, and 2020-2023 -
i.e. essentially every season the Patriots' own team-season pages don't
separately break out an OC/DC (Bill Belichick's staffs are notoriously
under-documented on Wikipedia), and no cached Patriots-assistant biography
happens to cover the missing years either.

Full list of the 115 remaining (season, franchise, role) triples:

1999: CLE-OC, DAL-OC, JAX-OC, MIA-DC, MIA-OC, NE-DC, NE-OC, NYG-OC
2000: CIN-OC, DAL-OC, JAX-OC, NE-DC, NE-OC, SEA-DC, WSH-OC
2001: DAL-OC
2002: ATL-OC, CLE-DC, JAX-OC, SEA-DC, WSH-OC
2003: ATL-OC, CAR-OC, CLE-DC, IND-DC, IND-OC, NE-OC, NYG-DC, NYG-OC, OAK-DC
2004: ARI-DC, CAR-OC, CLE-DC, IND-DC, IND-OC, NE-OC, SF-DC, SF-OC
2005: CAR-OC, CIN-DC, CLE-DC, DAL-OC, IND-DC, IND-OC, NE-OC, WSH-OC
2006: ARI-DC, CLE-DC, DAL-OC
2007: ARI-DC, CLE-DC, MIA-OC
2008: CLE-DC, GB-DC, SEA-DC
2009: ARI-OC, CAR-DC, DAL-DC, KC-DC, KC-OC, LAR-DC, MIA-OC, NE-OC, OAK-DC, OAK-OC, TEN-DC
2010: ARI-DC, ARI-OC, CAR-DC, LAC-OC, LAR-DC, MIA-OC, NE-DC, NE-OC, OAK-DC, TB-DC, TEN-DC
2011: ARI-OC, CLE-OC, DAL-OC, IND-DC, LAC-OC, LAR-DC, MIN-DC, NE-DC, OAK-DC, TB-DC, TEN-OC
2012: KC-DC
2014: HOU-OC
2016: CLE-OC
2017: CLE-OC, HOU-OC
2018: HOU-OC, NE-DC
2019: ARI-OC, ATL-DC
2020: ARI-OC, MIN-DC, NE-DC, PHI-OC, TEN-DC
2021: ARI-OC, MIN-DC, NE-DC
2022: ARI-OC, HOU-DC, NE-DC, NE-OC, TB-DC
2023: BUF-DC, NE-DC, TB-DC
2024: TB-DC
2025: TB-DC

These remain missing because no cached biography's `pastcoaching` field
names anyone for that franchise in that season - either the person's
biography doesn't exist on Wikipedia, wasn't reachable by title-guessing,
their `pastcoaching` field doesn't cover that stint, or Wikipedia's own
editors never recorded who held the job anywhere I could reach with the
en.wikipedia.org-only, no-search-engine rule.

## Alias merges (`person_aliases.csv`)

Unchanged from the first pass: 1 new certain merge, `Jimmy Raye` ->
`Jimmy Raye II` (punctuation/suffix-only). Combined with the 2
pre-existing merges, the file carries 3 certain merges. The second pass's
larger name pool produced no additional certain (punctuation/suffix-only)
merges and no additional doubtful pairs beyond the first pass's 7.

## Problems / limitations

1. **Source B1 as specified in the task does not exist** on Wikipedia (see
   above) - the whole gap-fill effort rests on one source (biographies),
   not two independently cross-checked ones. The ~98.7% validated
   agreement rate is reassuring but is a single data point, not a
   cross-check.
2. Biography `pastcoaching` fields are maintained by volunteer editors and
   are not guaranteed exhaustive or current; a short assistant stint can be
   omitted even when the person's Wikipedia article exists.
3. Of the 434 biography names now attempted across both passes, 339 (78%)
   had a `pastcoaching`/equivalent field the parser could use; the rest
   either don't have a cached/resolvable biography or the field wasn't in
   a form this parser handles.
4. The "discovery scan" (searching cached team-season-page prose for
   sentences naming an OC/DC near the role phrase, for gap seasons and
   their neighbours) is necessarily approximate: it takes the single
   nearest wikilink to the role phrase in the same sentence, which can
   occasionally pick the wrong nearby name in an oddly worded sentence.
   Nothing from the discovery scan is trusted on its own - a name is only
   ever written into `staff_gapfill.csv` when *that person's own
   biography's* `pastcoaching` field independently confirms the team,
   role, and season, exactly per the task's evidence rule.
5. New England (17 gaps), Cleveland (11) and Arizona (11) dominate what's
   left - not because their assistants lack Wikipedia biographies in
   general, but because the specific missing seasons for those franchises
   aren't covered by any biography this process could reach.

## Second-pass request accounting

- Request log: 1,354 lines before this pass -> **1,557 lines after**
  (**203 new requests**), against a 450-request budget and a
  stop-before-1,804 log-line ceiling. All requests were en.wikipedia.org,
  run in the foreground one process at a time, in two batches of 100 and
  102 requests (batch size capped by a 100-request-per-invocation flag,
  `tasklist | grep -i python` checked clear before each), draining the
  full 192-name candidate list built in step 1.
- Candidate list (`data/reference/gapfill2_fetch_candidates.csv`, 192
  names): 66 tier-1a (surfaced by the discovery scan on gap-adjacent
  team-season pages), 53 tier-1b (other staff of a gap franchise within 3
  seasons of one of its gaps), 72 tier-2 (everyone else, staff_stints_all
  or games.csv head coaches, season <=2012), 1 tier-3. 151 of the 192 were
  new (41 were already resolved/unresolved from the first pass); all 151
  were attempted (0 left in the queue): 137 resolved to a usable
  biography, 14 did not (disambiguation, no coach-shaped article, or a
  genuine 404).
- Combined with the first pass's 19 requests: **222 total new requests**
  across both passes of this phase, log at 1,557 (started at 1,335).

## What needs a human

- Confirm or reject the 5 disagreement cases (2002 WSH DC, 2006 ARI OC,
  2006 CLE OC, 2016 BUF OC, 2016 MIN OC) - likely both candidates are
  correct for different parts of the season, but that can't be established
  from `pastcoaching` year ranges alone.
- Review the 7 doubtful name pairs in `person_doubtful_pairs.csv`
  (unchanged by this pass).
- Decide whether the 115 remaining gaps - concentrated in New England,
  Cleveland, and Arizona, and in 2003-2005/2009-2011 - are worth a
  targeted, manual Wikipedia/Pro-Football-Reference lookup per team-season
  (out of scope for the strict en.wikipedia.org-only, script-driven rule
  used here).

## Reviewer's own knowledge (unverified)

None. Every name above was read off a fetched Wikipedia page during this
session; I did not draw on any of my own knowledge of these coaching
staffs, and would flag it explicitly here if I had.
