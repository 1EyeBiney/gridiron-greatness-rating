# Source: English Wikipedia, Phase 0 + Phase 1a

## Phase 1a addendum (2026-09-27)

Extended the same fetch (raw wikitext, `action=raw`, same polite fetcher and
User-Agent) to all 32 franchises for seasons 2011-2025 (480 team-season
pages total). Seasons 2022-2024 reused the Phase 0 cache (no re-fetch);
2011-2021 and 2025 were newly fetched (384 new requests). Team names for
seasons that pre-date a franchise's current identity were resolved through
the season-aware `data/reference/team_wiki_names.csv` (St. Louis Rams
2011-2015 / Los Angeles Rams 2016-2025; San Diego Chargers 2011-2016 /
Los Angeles Chargers 2017-2025; Oakland Raiders 2011-2019 / Las Vegas
Raiders 2020-2025; Washington Redskins 2011-2019 / Washington Football
Team 2020-2021 / Washington Commanders 2022-2025) - every one of these
page titles resolved (HTTP 200; no 404s in this run).

**Total requests this run: 384**, all HTTP 200, appended to
`data/raw/wikipedia_request_log.txt` (gitignored). Combined with Phase 0's
108 requests, the cumulative log for this study now has 488 lines. No
site other than en.wikipedia.org was contacted; rate stayed at <=1
request/second throughout (enforced by `src/pc_wiki_fetch.py`).

New derived tables produced this phase (all copied from fetched pages,
same no-outside-knowledge rule as Phase 0):
`data/processed/staff_by_season.csv`, `data/processed/staff_stints.csv`,
`data/processed/staff_headcoach_check.csv`,
`data/processed/coordinator_moves.csv`,
`data/processed/coordinator_to_headcoach.csv`,
`data/reference/person_aliases.csv`,
`data/reference/person_doubtful_pairs.csv`. `data/processed/staff_phase0.csv`
and `staff_phase0_headcoach_check.csv` are untouched from Phase 0.


**Fetched:** 2026-09-27
**Fetched by:** Claude Sonnet 5 (Phase 0 subagent), on behalf of Brian Clark (1eyebiney@gmail.com)
**License:** Wikipedia text is CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).
Any text quoted or reused in this study's outputs carries that license and
must be attributed if republished.

## What was fetched

Raw wikitext (`action=raw`) for English Wikipedia "{season} {team} season"
pages, via `https://en.wikipedia.org/w/index.php?title=...&action=raw`.

1. **Phase 0 main set**: 96 team-season pages — all 32 NFL franchises,
   seasons 2022, 2023, 2024. Franchise -> Wikipedia team name mapping in
   `data/reference/team_wiki_names.csv`.
2. **Scaling spot-check** (see docs/PHASE0_REPORT.md): 12 additional pages —
   Detroit Lions, New England Patriots, Baltimore Ravens, Seattle Seahawks,
   each for 1999, 2005, 2012.

**Total requests: 108** (96 + 12), all HTTP 200, logged in
`data/raw/wikipedia_request_log.txt` (gitignored along with the cached
pages themselves).

## Fetch rules followed

- Only en.wikipedia.org was contacted. No other site (no
  Pro-Football-Reference or any other stats site).
- At most 1 request per second (`src/pc_wiki_fetch.py` sleeps to enforce
  this), with User-Agent
  `GridironGreatness-research/1.0 (1eyebiney@gmail.com; non-commercial
  research project)`.
- Every fetched page is cached to disk under `data/raw/wikipedia/` (one
  `.wikitext` file per page, named by a sanitized title + a hash) so
  re-running the extraction script does not re-hit the network. That
  directory (and the request log) is gitignored — see `.gitignore` in this
  study folder — so raw Wikipedia text is never committed to this repo.
- Pages were fetched once and reused for all subsequent debugging/parsing
  iterations in this phase; no page was re-fetched after its first
  successful request.

## What is derived vs. raw

- `data/processed/staff_phase0.csv` and
  `data/processed/staff_phase0_headcoach_check.csv` are derived tables:
  every name in them is copied (after markup-stripping) from a raw fetched
  page, cited by `wiki_title`/`wiki_url` and `raw_note` (the raw field text)
  in the CSV itself. No name was filled in from the author's own knowledge.
