# Phase 6 Summary: Outputs and Website

Status: COMPLETE (site built and tested locally; GitHub Pages not yet enabled - see "Publishing" below)
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
testing with NVDA and JAWS before release. That needs a human with that
software running an actual screen reader against the live site - it
is not something this session can perform, and this deliverable should
not be read as having done it. Recommend an actual screen-reader pass
before or shortly after the site goes live.

## Publishing: not yet done

The workflow file is ready and was tested locally (`python
src/run_phase6.py` from the repo root, the same way CI will run it,
generates the site correctly), but two things this session deliberately
did not do without asking first:

1. **Enable GitHub Pages** in the repository's settings (Settings →
   Pages → Source: GitHub Actions). Until this is done, the workflow has
   nothing to deploy to.
2. **Push to master**, which would trigger the workflow and make the
   site live at a public URL.

Both are exactly the kind of "publish public content" action this
project's safety guidelines ask to be confirmed explicitly, distinct
from writing the code that makes publishing possible.

## What's carried forward

- Roster Quality and Coach Strength Entering Season descriptive
  sub-scores (Phase 5, still need external data).
- The deferred spread comparison (Phase 4).
- Pre-1999 playoff round labels (would let ACC's playoff-win bonus
  escalate by round).
- An actual NVDA/JAWS pass, once the site is live.

## Recommended next step

Confirm publishing (enable Pages, push), then a real screen-reader
check. After that, the project's originally scoped phases (0-6) are all
complete - anything further (Roster Quality, Coach Strength, the spread
comparison, playoff-round reconstruction) is optional depth on an
already-shippable result.
