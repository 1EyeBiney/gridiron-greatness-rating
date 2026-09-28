# Phase 1b report: draft play-caller table with evidence

Phase 1a built who held the HC/OC/DC **title** for every team-season,
2011-2025. This phase builds a draft of who actually **called plays** for
each unit, with sourced evidence where Wikipedia states it and the
reviewer's own unverified NFL knowledge where it doesn't - clearly marked
as such, per the task's hard rule. Nothing here should be read as final;
it is Brian's review queue.

## Evidence mining

`data/processed/playcall_evidence.csv`: **147 evidence sentences**.

| source_type | count |
|---|---|
| team_season_page | 17 |
| biography | 130 |
| **total** | **147** |

Team-season-page mining re-scanned all 480 already-cached 2011-2025 pages
on disk (zero new network requests). It is deliberately sparse: most
Wikipedia team-season articles narrate wins, losses and injuries, not
who called plays, so 17 hits across 480 pages is the expected shape of
this source, not a bug.

Biography mining fetched 306 distinct coaches' Wikipedia pages (network,
budget-limited): every head coach in `staff_stints.csv` first, then
offensive/defensive coordinators who are not also a head coach, ranked by
number of seasons, until the request budget ran out.

**Biography resolution rate: 297/306 (97.1%)** resolved to a page that
mentions both "football" and "coach" in its opening; 9 did not resolve
(list below, from `data/reference/playcaller_bio_resolution.csv`):
Arthur Smith, "Sean Payton�" (mojibake-corrupted name from a source
row - the real Sean Payton's own biography almost certainly exists but
wasn't looked up under a garbled title), Mike Caldwell, Bill Davis, Blake
Williams, Chris Harris, "Gregg Williams�" (same mojibake pattern),
Hal Hunter, and "Pete Carmichael, Jr." (the comma-variant spelling flagged
as unresolved in Phase 1a - the period-variant "Pete Carmichael Jr." is
a common enough name that it may have resolved to the wrong disambiguation
target, or simply never got a valid coach page found under any of the
three title forms tried).

## Draft table: basis and confidence

`data/processed/playcaller_draft.csv`: **960 rows** (32 franchises x 15
seasons x 2 units, 2011-2025).

| basis | confidence | rows |
|---|---|---|
| default_coordinator | medium | 823 |
| default_no_coordinator_headcoach | low | 67 |
| evidence_wikipedia | high | 1 |
| evidence_wikipedia | medium | 6 |
| model_knowledge_unverified | low | 10 |
| model_knowledge_unverified | medium | 53 |
| **total** | | **960** |

96 of the 960 rows carry `midseason_change = True` (a mid-season change in
the head coach and/or the relevant unit's coordinator that season, per
`staff_stints.csv`'s `n_holders_that_season`).

No `model_knowledge_unverified` row is ever `confidence = high` (enforced
both by the builder's logic and by a dedicated test,
`test_no_model_knowledge_override_is_ever_high_confidence`, which checks
every hand-entered override in
`src/pc_build_playcaller_draft.py::MODEL_KNOWLEDGE_OVERRIDES`). Every one
of those rows' `note` states plainly that it is a belief, not a sourced
fact, and that it needs a source.

`data/reference/playcaller_overrides_for_review.csv`: **214 rows** - every
row where the proposed play-caller differs from the titled coordinator,
where there was a mid-season change, or where no titled coordinator
exists at all - sorted by franchise then season, with the evidence
sentence and URL inlined, plus empty `reviewer_decision`/`reviewer_note`
columns for Brian.

## The ten most important judgment calls

1. **Andy Reid, KC offense, 2013-2025 (medium).** Widely reported he calls
   his own plays as head coach; no specific Wikipedia citation found in
   this run's evidence mining, so it's model-knowledge, not
   evidence-sourced.
2. **Sean McVay, LAR offense, 2017-2025 (medium).** Same pattern -
   well known publicly, not found as a sourced Wikipedia sentence here.
3. **Kyle Shanahan, SF offense, 2017-2025 (medium).** Same pattern.
4. **Sean Payton, NO offense, all seasons except the 2012 suspension
   (medium).** 2012 is deliberately excluded since Payton wasn't
   coaching that season (Bountygate); the interim staff's own OC title
   holder (Pete Carmichael Jr.) is left as the Phase 1a default for 2012
   rather than guessed at further.
5. **Sean Payton, DEN offense, 2023-2025 (medium).** Extends the same
   belief to his second head-coaching job.
6. **Mike McDaniel, MIA offense, 2022-2025 (medium).**
7. **Todd Bowles, TB defense, 2022-2025 (medium).** Extends a title he
   already held as Tampa Bay's own DC-as-HC in 2019-2021 (that earlier
   span is `default_coordinator`, not a judgment call, since Bowles was
   the titled DC then).
8. **Matt Eberflus, CHI defense, 2022-2024 (low, not medium).** Marked
   lower confidence than the others above because Chicago also had
   titled defensive coordinators in this window and this study is not
   confident which seasons, if any, Eberflus personally called plays
   versus deferring.
9. **Dan Quinn, ATL defense, 2015-2020 (low).** Same caveat - a
   defensive-minded head coach believed to be closely involved, but not
   confidently tied to specific seasons.
10. **2022 Miami defensive coordinator (Phase 1a's carried-over flag, not
    resolved here either):** the infobox's "Vic Fangio" versus the staff
    section's "Josh Boyer" disagreement (Fangio was hired for 2023, not
    2022) is still present in `staff_stints.csv` as both names; this
    phase's draft builder uses whichever name(s) `staff_stints.csv` lists
    for that team-season's DC role as the coordinator default and does
    not adjudicate the Phase 1a disagreement - a human should resolve
    that upstream question, not just the play-caller question, for this
    row.

A few more notable calls, at lower stakes than the ten above: Doug
Pederson (PHI offense, 2016-2018, low confidence - explicitly flagged as
uncertain which seasons) and Brian Flores (MIA defense, 2019-2021,
medium). The full, sourced list of every wikipedia-evidence override
(all 7 rows) is in the "Draft table" section above and inline in
`playcaller_overrides_for_review.csv`.

## Known weaknesses

- **Wikipedia biographies rarely state play-calling by season.** Most of
  the 130 biography-sourced hits describe a coach's play-calling
  reputation or a single career-defining moment, not a season-by-season
  record - several evidence rows' `season` column is blank because no
  year could be confidently attached to the sentence, per the task's
  instruction not to guess a season when unsure.
- **Sentence-level unit and person matching is a heuristic, not a parse.**
  `unit_guess` keys off "offen"/"defen" substrings in the same sentence,
  and `persons_mentioned` matches on last name only; a sentence naming two
  people (the outgoing and incoming play-caller, say) produces a
  " | "-joined `proposed_playcaller` rather than picking one, by design -
  the note quotes the sentence so the reviewer can judge, but the CSV
  itself does not resolve the ambiguity.
- **The model-knowledge override list is short and reviewer-selected**,
  not an exhaustive scan of every widely-known play-calling head coach in
  this window (e.g. Mike Vrabel, Bill Belichick, Sean McDermott and others
  were deliberately left at the coordinator default rather than guessed
  at, because this reviewer was not confident enough about them to write
  even a low-confidence note).
- **Mid-season changes and the coordinator default can conflict.** A row
  flagged `midseason_change = True` still gets a single
  `default_playcaller`/`proposed_playcaller` string (typically all named
  holders joined by " | "), not a game-by-game split - that finer grain is
  explicitly out of scope for this phase per the plan (Phase 1's own
  acceptance is the override list itself, not per-game attribution).

## Problems found and how they were handled

- **Two fetch processes ran concurrently for a few minutes.** A first
  attempt to run the biography-fetch script in the background used a
  plain shell `&` rather than the tool's proper background-process
  mechanism; when it appeared not to be tracked, a second run was started
  with the correct mechanism without confirming the first had actually
  stopped. Both were briefly alive at once (confirmed via `Get-CimInstance
  Win32_Process`), which violates this phase's explicit "never run two
  fetching processes at once" rule. Caught within a few minutes by
  polling the request log's line count and noticing it was rising faster
  than one process alone would explain; the duplicate process (Windows
  PID 24228) was killed via `Stop-Process`, leaving only the correctly
  tracked one running to completion. Because both processes shared the
  same on-disk cache, no title was fetched twice from the network in a
  way that duplicated content, but the total request count for this phase
  (474) is somewhat higher than the 450 budget as a direct result of the
  overlap, and request timing during the overlap window did not stay
  strictly at <=1 request/second in aggregate across the two processes
  (each individually did). This is reported here plainly rather than
  smoothed over.
- **Sentence truncation was originally applied before the play-calling
  pattern match**, which could silently drop a match whose trigger phrase
  fell after character 400 of a long sentence. Caught by a test
  (`test_extract_hits_truncates_long_sentences_to_400_chars`) that failed
  against the first version of `extract_hits`; fixed by matching the
  pattern against the full sentence first and only truncating the stored
  copy afterward.

## What a human must check first

1. The 214-row `data/reference/playcaller_overrides_for_review.csv` -
   every no-coordinator, mid-season-change, or overridden row, in one
   place with the evidence sentence and URL inlined.
2. Every `model_knowledge_unverified` row (63 rows) - confirm or reject
   each belief; none of them should be treated as established until
   Brian (or a cited source) confirms it.
3. The single `evidence_wikipedia`/`high` row (2025 NYJ defense, Chris
   Harris) and the six `medium` ones - these are the closest this phase
   gets to a sourced answer, but the extraction is a regex heuristic, not
   a careful read, so each sentence is worth reading in full via its URL
   before trusting the name split.
4. The unresolved biography-name list (9 names, above) - a couple look
   like real coaches whose page just wasn't found under the title forms
   tried (Arthur Smith, Bill Davis, Chris Harris, Hal Hunter, Mike
   Caldwell are all plausible NFL assistants); two are corrupted by the
   known mojibake artifact carried over from Phase 1a's own
   `strip_wiki_markup` note.
5. The carried-over 2022 Miami DC disagreement (Fangio vs. Boyer) still
   sitting unresolved in `staff_stints.csv`, noted again above.

**Everything under `basis = model_knowledge_unverified` in
`playcaller_draft.csv` is this reviewer's own outside knowledge, not a
Wikipedia citation, and must not be treated as fact until sourced.**

## Files produced or changed this phase

- `src/pc_playcall_evidence.py` - new: sentence extraction
  (`sentences_from_wikitext`, `extract_hits`, `unit_guess`,
  `persons_mentioned`), team-season-page mining
  (`mine_team_season_pages`), biography title resolution
  (`resolve_biography_title`) and mining (`mine_biographies`,
  `build_bio_priority_list`), and the evidence CSV writer.
- `src/pc_build_playcaller_draft.py` - new: the draft-table builder
  (`build_draft`), the hand-entered `MODEL_KNOWLEDGE_OVERRIDES` list, and
  the review-subset builder (`build_review_subset`).
- `data/processed/playcall_evidence.csv` - 147 rows.
- `data/processed/playcaller_draft.csv` - 960 rows.
- `data/reference/playcaller_overrides_for_review.csv` - 214 rows.
- `data/reference/playcaller_bio_resolution.csv` - 306 rows.
- `data/raw/SOURCE.md` - Phase 1b addendum with the new fetch count.
- `tests/test_pc_playcallers.py` - 17 new tests (sentence extraction,
  biography-title validation with a monkeypatched fetcher, the draft
  builder on inline frames including the no-high-confidence-on-
  model-knowledge rule, and checks against the real files when present).
  41 tests total across the study, all passing.
