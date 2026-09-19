# Gridiron Greatness Rating

A historical NFL team-strength rating system that accounts for the true strength of opponents,
conference competitive environment, and era, then applies that database to evaluate Super Bowl
participants against historical rankings.

See `docs/BUILD_PLAN.md` for the full research specification, settled decisions, and phase plan.

Status: Phases 0-6 all complete. Live site: https://1eyebiney.github.io/gridiron-greatness-rating/ (model family locked to the Bayesian hierarchical margin model; ACC point schedule is a recommendation, not locked - see `docs/PHASE5_SUMMARY.md`). See `docs/PHASE6_SUMMARY.md` for the site itself, including the Vikings-themed visual redesign.

## Side studies

Self-contained studies built on the same game table live under `studies/` and publish as sub-sites:

- [Home Field Advantage](studies/home-field-advantage/) - how much home field is worth 1970-2025, whether it fades late in the season, and whether any fan base travels well enough to matter. Live at https://1eyebiney.github.io/gridiron-greatness-rating/home-field-advantage/
