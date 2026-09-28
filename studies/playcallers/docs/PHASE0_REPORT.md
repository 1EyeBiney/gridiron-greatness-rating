# Phase 0 report: can Wikipedia give us HC/OC/DC for 2022-2024?

96 team-seasons (32 franchises x 2022, 2023, 2024). Every name below comes
from a fetched Wikipedia page; see `data/processed/staff_phase0.csv`
(`raw_note` column has the raw field text behind every value) and
`data/raw/SOURCE.md`.

## Coverage

| Role | Named | Missing | % |
|---|---|---|---|
| Head coach | 96 / 96 | 0 | 100% |
| Offensive coordinator | 94 / 96 | 2 | 98% |
| Defensive coordinator | 89 / 96 | 7 | 93% |

This clears the Phase 0 acceptance bar (>=90 of 96 with a named OC and DC,
or an explicit reason).

**Every missing case**, with what the page actually says:

Offensive coordinator missing (2):
- 2022 ARI (Arizona Cardinals) — no "Offensive coordinator" bullet in the
  staff section at all; head coach Kliff Kingsbury is understood to have
  called the offense himself that year, but the page does not say so in
  words — it simply has no titled OC.
- 2022 NE (New England Patriots) — no OC bullet; the 2022 staff page lists
  only "Personnel coordinator" and "Special teams coordinator" among
  coordinator titles. New England ran a coaching-by-committee offense that
  year without a titled OC (widely reported at the time, but that reporting
  is outside Wikipedia and not used here).

Defensive coordinator missing (7):
- 2022 HOU (Houston Texans) — staff section has Offensive coordinator and
  Special teams coordinator bullets but no "Defensive coordinator" bullet.
- 2022 NE — same as above, no DC bullet either.
- 2022 TB, 2023 TB, 2024 TB (Tampa Bay Buccaneers, all three seasons) — no
  "Defensive coordinator" bullet in any of the three years; Todd Bowles
  (head coach) is the defensive playcaller by title in this era at Tampa
  Bay, per the page's role list (no separate DC title is ever used).
- 2023 BUF (Buffalo Bills) — no DC bullet.
- 2023 NE — no DC bullet (Bill Belichick's last Patriots season).

No team-season is missing a head coach. Nobody had to fill in a role from
outside knowledge to reach these counts — the table above is exactly what
was extracted from the pages, gaps included.

## Multi-name team-seasons (mid-season changes / interims / co-titles)

12 of 96 team-seasons have more than one name in at least one role:

| Season | Team | Head coach | Off. coordinator | Def. coordinator |
|---|---|---|---|---|
| 2022 | CAR | Matt Rhule \| Steve Wilks | Ben McAdoo | Al Holcomb |
| 2022 | DEN | Nathaniel Hackett \| Jerry Rosburg | Justin Outten | Ejiro Evero |
| 2022 | IND | Frank Reich \| Jeff Saturday | Parks Frazier | Gus Bradley |
| 2023 | BUF | Sean McDermott | Ken Dorsey \| Joe Brady | (none) |
| 2023 | CAR | Frank Reich \| Chris Tabor | Thomas Brown | Ejiro Evero |
| 2023 | LAC | Brandon Staley \| Giff Smith | Kellen Moore | Derrick Ansley |
| 2023 | OAK (LV) | Josh McDaniels \| Antonio Pierce | Mick Lombardi \| Bo Hardegree | Patrick Graham |
| 2023 | WSH | Ron Rivera | Eric Bieniemy | Jack Del Rio \| Ron Rivera |
| 2024 | CHI | Matt Eberflus \| Thomas Brown | Shane Waldron \| Chris Beatty | Eric Washington |
| 2024 | NO | Dennis Allen \| Darren Rizzi | Klint Kubiak | Joe Woods |
| 2024 | NYJ | Robert Saleh \| Jeff Ulbrich | Nathaniel Hackett | Marquand Manuel |
| 2024 | OAK (LV) | Antonio Pierce | Luke Getsy \| Scott Turner | Patrick Graham |

Names are kept in the order the source lists them (fired/departed coach
first, interim/successor second), which for the head-coach infobox field is
usually explicit ("fired November 27" / "interim"); the extraction keeps
that order but does not carry the parenthetical firing dates into the name
columns — they're preserved in `raw_note`.

One additional case worth flagging even though it only has one name per
role in the CSV: **2023 PIT (Pittsburgh Steelers)**, offensive coordinator.
The infobox lists only "Matt Canada", but the Staff section explicitly says
"Matt Canada; ''fired after Week 11'' ; Eddie Faulkner". Because this
study's extraction prefers the infobox's names when both infobox and staff
section have a value for a role (see "Where infobox and staff disagree"
below), Eddie Faulkner does not appear in `offensive_coordinator` for that
row — a real gap in Phase 0's parsing choice, called out here so it isn't
missed. **2022 NO (New Orleans Saints)** defensive coordinator is stored as
the single string "Ryan Nielsen and Kris Richard" (co-coordinators) rather
than two names split with " | ", because the source wrote it as one prose
phrase, not a `<br>`-separated list — also a known formatting gap, not a
missing name.

## Head-coach cross-check

Extracted head coach vs. the nflverse schedule file's home_coach/away_coach
(mapped to franchise ids the same way `xe_metrics.to_franchise` does),
compared by last name. Result: **93 of 96 matched.**

All 3 mismatches:

| Season | Team | Wikipedia head coach(es) | Schedule file coach(es) |
|---|---|---|---|
| 2024 | CHI | Matt Eberflus \| Thomas Brown | Matt Eberflus (17 games) |
| 2024 | NO | Dennis Allen \| Darren Rizzi | Dennis Allen (17 games) |
| 2024 | NYJ | Robert Saleh \| Jeff Ulbrich | Robert Saleh (17 games) |

All three are real, well-documented in-season head-coaching changes in
2024 (Eberflus fired, replaced by Thomas Brown; Allen fired, replaced by
Darren Rizzi; Saleh fired, replaced by Jeff Ulbrich). The nflverse schedule
file's `home_coach`/`away_coach` columns credit every game of the season to
the coach who started it, not the one who actually paced the sideline that
week — so this is a known limitation of the **cross-check data**, not of
the Wikipedia extraction. It also means the cross-check under-counts how
well Wikipedia agrees with ground truth: the Wikipedia interim names here
are the more accurate ones.

## Where infobox and staff section disagree

7 rows have at least one role where the infobox and staff-section values
disagree by last name (full detail in `raw_note`; extraction keeps the
infobox's names in these cases since it's more likely to reflect the whole
season including departures — see limitation above for the one case,
2023 PIT OC, where that choice drops a name):

- **2022 CAR** (head coach): infobox lists Matt Rhule (fired) then Steve
  Wilks (interim); the "NFL final staff" template — by design, it reflects
  the roster as of season's end — lists only Steve Wilks.
- **2022 DEN** (head coach): same pattern, Nathaniel Hackett (fired) +
  Jerry Rosburg (interim) in the infobox vs. only Jerry Rosburg in staff.
- **2022 IND** (head coach): same pattern, Frank Reich (fired) + Jeff
  Saturday (interim) vs. only Jeff Saturday.
- **2022 MIA** (defensive coordinator): infobox says **Vic Fangio**; the
  staff section says **Josh Boyer**. This is a real disagreement, not a
  formatting artifact — Fangio was hired as Miami's DC in 2023, a year
  later, so the infobox value here looks like a **wrong/stale edit on
  Wikipedia's side**, not a Phase 0 parsing bug. (This is the author's own
  outside-knowledge read of the situation, marked separately as requested —
  it is not baked into any CSV value; the CSV keeps the raw disagreement
  for a human to resolve in Phase 1.)
- **2022 NO** (offensive coordinator): "Pete Carmichael Jr." (infobox) vs.
  "Pete Carmichael" (staff, via a piped wikilink) — same person, cosmetic
  difference only (a suffix), not a real disagreement.
- **2023 PIT** (offensive coordinator): infobox has only "Matt Canada";
  staff section has "Matt Canada; fired after Week 11 ; Eddie Faulkner" —
  see the multi-name section above.
- **2023 WSH** (defensive coordinator): infobox lists Jack Del Rio (fired)
  and Ron Rivera (interim) via a `{{ubl|...}}` template; staff section
  lists only "Ron Rivera (interim)" — same end-of-season-only pattern as
  the head-coach cases above.

Every one of the head-coach-pattern disagreements (2022 CAR/DEN/IND, and
the WSH DC case) is the same systematic thing: the infobox tends to carry
the season's full history (fired coach + replacement), the "NFL final
staff" template only the incumbent at season's end. That's a real, general
difference between the two sources worth knowing before Phase 1, not
scattered noise.

## Parsing problems hit, and how they were handled

- **Three different infobox template names** are in use across pages:
  `{{Infobox NFL team season}}`, `{{Infobox NFL_season}}` (underscore), and
  `{{Infobox gridiron football team season}}` (seen on newer/re-templated
  pages, e.g. 2024 Indianapolis Colts, 2024 Washington Commanders). The
  matching regex was widened to catch all three; field names (`coach`,
  `off_coach`, `def_coach`) are consistent across them.
- **The "Staff" heading is not consistent**: most pages use `==Staff==`,
  but at least one (2022 Denver Broncos) uses `===Staff / Coaches===` (a
  level-3 heading with extra wording). The heading regex now matches any
  `==`-`====` heading containing "Staff".
- **Nested templates inside infobox field values** broke naive parsing
  twice: `{{ubl|A|B}}` used as an inline list value for `def_coach` (2023
  Washington), and `{{winpct|3|5|1|record=y}}` embedded inside a
  parenthetical note on the `coach` field (2022 Indianapolis: "(fired
  November 7; {{winpct|...}} record)"). `{{ubl|...}}` is expanded into a
  pipe-separated name list before splitting; any other leftover `{{...}}`
  template is stripped outright, since its own internal pipes would
  otherwise be mistaken for name separators.
- **Slash-combined staff-section role labels**: e.g. "Assistant head
  coach/offensive coordinator" (2024 NY Giants, Mike Kafka) or "Interim
  head coach/special teams coordinator" (2023 Carolina, Chris Tabor). The
  parser checks every slash-separated part of the label against the known
  role names, not just the first part, so these are still picked up as
  OC/HC respectively.
- **Italic annotations split off as a bogus extra name**: e.g. "Alan
  Williams; <br>''resigned on September 20''" (2023 Chicago DC) turns into
  two segments once `<br>` is treated as a separator; the second
  ("resigned on September 20") is not a name. Segments starting with a
  lowercase word are dropped as annotations rather than kept as a name —
  a heuristic, not a certainty, and worth spot-checking in Phase 1.
- **Character encoding**: the raw wikitext fetch originally decoded en/em
  dashes and non-breaking hyphens as mojibake (`�` replacement
  characters) because `requests` guessed a non-UTF-8 encoding for the raw
  wikitext response. Fixed by forcing `resp.encoding = "utf-8"` before
  reading `.text` in `pc_wiki_fetch.py`. (Caught by inspecting raw bytes of
  a cached page and comparing to the decoded string — the bytes were
  correct UTF-8 all along.)
- **Co-coordinators written as prose** ("Ryan Nielsen and Kris Richard",
  2022 New Orleans DC) are not split into two names; the pipe/`<br>`-based
  splitter only catches list-style co-credits (like the WSH `{{ubl}}`
  case), not an "X and Y" sentence. Left as one string, noted above.

None of these were "papered over" — every fix is visible in
`src/pc_extract_staff.py`, and the disagreements/gaps that couldn't be
resolved automatically are listed above rather than silently picked one
way.

## Does this scale to 1999-2025?

Spot-checked 12 additional pages (Detroit Lions, New England Patriots,
Baltimore Ravens, Seattle Seahawks, each for 1999, 2005, and 2012 — 12
requests, within the 15-page budget) rather than the full 27-year range.
Findings:

- **1999 and 2012 pages generally have both an infobox OC/DC field and a
  Staff section** with OC/DC bullets — Detroit, Baltimore, and Seattle all
  had both in 1999; New England's 1999 and 2005 pages have neither a staff
  section nor an infobox OC/DC field, only a head coach.
- **2005 is visibly weaker**: Detroit 2005 has no infobox OC/DC fields (HC
  only) though its Staff section does carry an OC; New England 2005 and
  Seattle 2005 have no Staff section and no infobox OC/DC fields at all —
  head coach only.
- Put together: coverage is not a smooth function of age. Some 1999 pages
  are as complete as 2022-2024 ones; some 2005 pages (New England, Seattle)
  have nothing but a head coach's name, no coordinators at all from either
  source, on this small sample.

**Assessment**: full 1999-2025 automation with this same parser is
optimistic. Older seasons (particularly the mid-2000s in this sample) will
have team-seasons where Wikipedia's season page simply carries no
coordinator information, so Phase 1 must plan for manual research
(likely a handful to a few dozen team-seasons, going by this small sample
alone — a real count needs the full historical fetch, not this 12-page
spot check) to fill gaps that this pipeline cannot resolve from Wikipedia.
The infobox-template-name churn already seen in 2022-2024 (three variants)
suggests older pages may add still more template-name and field-name
variants that this parser hasn't been taught yet; every new season range
fetched should be spot-checked before trusting its output, the way this
report spot-checked three eras here.

## What Wikipedia tells us, and what it doesn't

Wikipedia's team-season pages report who held the **job title** of
offensive/defensive coordinator (or head coach) for a team-season. They do
not report, and this study cannot get from them, who actually **called
plays** on a given Sunday. Those are the same person most of the time but
not always (a head coach can hold play-calling duties while someone else
holds the coordinator title, or a coordinator can lose play-calling
authority mid-season without losing the title) — that gap is exactly what
Phase 1's hand-built play-caller-override table, sourced and confidence-
graded row by row, is for. Nothing in this phase's CSVs should be read as
"this person called the plays."

## Files produced

- `src/pc_wiki_fetch.py` — polite cached fetcher (HTML + raw wikitext).
- `src/pc_extract_staff.py` — the extractor described above.
- `src/pc_headcoach_check.py` — the schedule-file cross-check.
- `data/reference/team_wiki_names.csv` — franchise id -> Wikipedia team name.
- `data/processed/staff_phase0.csv` — 96 rows, one per team-season.
- `data/processed/staff_phase0_headcoach_check.csv` — 96 rows, cross-check result.
- `data/raw/SOURCE.md` — fetch log summary and license note.
- `tests/test_pc_extract_staff.py` + `tests/conftest.py` — 11 unit tests
  (parsing functions on inline snippets, plus anchor checks against the
  built CSV), all passing.
