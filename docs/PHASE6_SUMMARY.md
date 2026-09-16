# Phase 6 Summary: Outputs and Website

Status: COMPLETE and published - live at https://1eyebiney.github.io/gridiron-greatness-rating/
Date: 2026-09-16

## What was built

- **Query tables** (`src/queries.py`): all eight queries BUILD_PLAN section 8
  names - greatest champions, weakest champions, greatest losers, best
  teams never to win, largest mismatches, greatest conference imbalance,
  best decade, and records that most overstated strength. Every ranking
  uses the locked True Strength Rating z-score, so any two team-seasons
  from 1970 to 2025 are compared on equal footing.
- **Static site generator** (`src/build_site.py`, templates in
  `src/site_templates/`): a landing page, a methodology page written in
  plain language for site visitors (distinct from the internal
  BUILD_PLAN), 56 season pages, 56 Super Bowl matchup pages, 8 query
  pages, and a data-download page - all generated from the data already
  in `data/processed/` and `data/reference/`, nothing hand-written per
  page. `site/` itself is not committed (see `.gitignore`); it's always
  regenerated fresh, the same reproducibility principle the rest of the
  pipeline follows.
- **CSV and JSON exports**: the full team-season profile, the Super Bowl
  matchup table, and the Conference Strength Index table, each in both
  formats, linked from the site's data-download page.
- **GitHub Actions deployment** (`.github/workflows/deploy-pages.yml`):
  builds the site and publishes it to GitHub Pages on every push to
  master. Not yet triggered live - see below.

## Accessibility (BUILD_PLAN section 10)

Built to the letter of the spec: semantic HTML5 landmarks (`header`,
`nav`, `main`, `footer`), a heading hierarchy on every page, real
`<table>` markup with `scope="col"`/`scope="row"` on every header cell,
a skip-to-content link, and - deliberately - no charts anywhere. BUILD_
PLAN's own accessibility-first principle (section 2, item 6: "usable
non-visually first... charts are optional extras") is satisfied more
directly by not having any: every number is in a plain table and also
downloadable as CSV/JSON. Verified locally with `get_page_text` and a
direct read of the generated HTML's landmark structure and table markup.

**What this session could not do**: BUILD_PLAN section 10 calls for
testing with NVDA and JAWS before release - that needs a human with that
software running an actual screen reader, not something this session can
perform directly. Brian confirmed after the initial launch that the site
"works pretty well" with his own screen reader, which is real evidence
the accessibility approach holds up in practice, though it's not the
same as a dedicated NVDA/JAWS pass across every page type.

## Publishing

Enabled via `gh api` (Pages source: GitHub Actions) and pushed after
Brian's explicit go-ahead - both the settings change and the push were
held for confirmation first, since publishing public content needs that
regardless of how ready the code is. Live at
https://1eyebiney.github.io/gridiron-greatness-rating/, auto-deploying
on every push to master.

One live bug shipped and was fixed within the hour: the query index
page's links used underscore slugs while the page generator wrote
hyphenated filenames, a 404 neither side's own code would have caught in
isolation. Fixed, and a whole-site link checker (`tests/test_build_site.py`)
now builds the entire site in a temp directory and verifies every
internal `href` resolves to a real file - added specifically so this
class of bug can't ship again unnoticed.

## Visual redesign (Brian's request, same day)

Once the site was live and confirmed working, Brian asked for a full
visual pass: a Minnesota Vikings purple/gold color scheme, genuine
mobile responsiveness (most readers will be on a phone), and original
illustrations evoking the 1970s electric-football tabletop game he and
a colleague both grew up playing. Delivered:

- **Color palette**: every foreground/background pairing was checked
  against WCAG contrast math before use (not eyeballed) - see the
  session's `contrast_check.py`. Gold is never used for text on a light
  background or for light text on gold (it fails both ways); purple is
  never used as the accent color against the dark-mode background (it
  fails there too - dark mode uses gold as the accent instead). Both
  light and dark mode pass AA or better on every pair actually used.
- **Mobile**: every dense stat table (up to 14 columns) is wrapped in a
  scrollable container (`.table-scroll`) rather than squeezed or
  reflowed - verified directly by emulating a 375px viewport and
  confirming both the page layout holds and the table itself scrolls
  horizontally on touch.
- **Illustrations**: five images generated via Gemini (Brian's Chrome
  session, driven through browser automation) in a consistent style
  across follow-up prompts in one conversation - a Vikings figurine in
  purple/gold with a horned helmet, styled after Tudor Electric
  Football's real 1947-on design, facing off against opposing figurines
  wearing a bear head, lion head, and cheesehead instead of a helmet.
  Deliberately evocative rather than literal (no real NFL team logos
  reproduced anywhere) given the site may be shared publicly. Resized
  and compressed for web (88-254 KB each, from 3+ MB originals) before
  committing.
- **New page**: `electric-football.html`, a short, factually-grounded
  history of the actual game (Norman Sas, 1947, the vibrating-board
  mechanic, why it was equal parts beloved and unpredictable), tying the
  site's visual theme to that shared memory without inventing specifics
  about anyone's personal experience with it.
- Two accessibility regressions were added as permanent tests, not just
  fixed once: every `<img>` must carry an `alt` attribute (checked
  site-wide), and the link checker now also validates every `src`, not
  just `href` - a broken image path is exactly the kind of thing the
  original link-checker bug pattern predicts and the old test wouldn't
  have caught.

## Narrative pages (Brian's request, same day)

Two long-form pages turn the tables into something a casual fan reads:

- **Why This Exists** (`why.html`, first in the nav) - Brian's own
  motivation, ghostwritten in his first-person voice from what he
  described and meant for him to edit: the 2025 Patriots hunch (the data
  agrees), the '85 Bears (2nd all-time), the Manning Colts, the Patriots
  dynasty, and the 1990s Cowboys' absence from the top (four straight
  seasons rated 18th-27th - sustained, not peaked).
- **What It All Means** (`what-it-means.html`, after Methodology) - a
  Sports-Illustrated-style walk through the top teams, the best that
  never won, the weakest champions, the perfect-season paradox, the
  eras, the franchises, and the Vikings. No quotes; every claim is either
  well-established history or a number from this site's tables.

Because prose can't be regenerated from data, `tests/test_narrative_claims.py`
pins every load-bearing number in both pages to the data (33 checks).
Writing those tests caught four factual errors in the first draft
before anything shipped - see the BUILD_PLAN decision log for the list.
That's the strongest argument this project has produced for testing
prose the same way it tests code.

## What's carried forward

- Roster Quality and Coach Strength Entering Season descriptive
  sub-scores (Phase 5, still need external data).
- The deferred spread comparison (Phase 4).
- Pre-1999 playoff round labels (would let ACC's playoff-win bonus
  escalate by round).
- A dedicated NVDA/JAWS pass across every page type, beyond Brian's own
  spot-check.
- Brian's review of the first-person "Why This Exists" page - it's his
  voice and his story, drafted from a paragraph of description.

## Recommended next step

The project's originally scoped phases (0-6) are complete and live.
Anything further (Roster Quality, Coach Strength, the spread comparison,
playoff-round reconstruction, a dedicated screen-reader audit) is
optional depth on an already-shippable, already-shipped result.
