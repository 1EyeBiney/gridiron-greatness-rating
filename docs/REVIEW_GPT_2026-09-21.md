# Outside review of v1.0 (2026-09-21)

Brian asked a different AI model (GPT) to review the live site and reproduce what it could from the published code and tables. Its report is reproduced below verbatim; the point-by-point response is in [REVIEW_RESPONSE_2026-09-21.md](REVIEW_RESPONSE_2026-09-21.md).

---

**There is worthwhile work here, but I found two concrete problems in the quarterback analysis and several conclusions that are stronger than the evidence supports.** Your Purdy question was particularly productive: it exposed a measurement problem, not merely a surprising football result.

I reviewed the site’s methodology and findings, inspected the supporting code and research notes, and reproduced the published quarterback rankings from the committed data. This is a substantive first review, though I have not independently rebuilt every study from raw play-by-play.

**1. Why is Purdy second? The published statistic does not measure what its label says.**

The quarterback leaderboard calls its measure “explosive-pass rate per dropback.” However, the calculation actually is:

> **All team explosive passes and runs in games that quarterback started ÷ all team dropbacks in those games.**

An explosive play includes a pass gaining at least 20 yards **or any rush gaining at least 10 yards**. The code then assigns the entire game’s team totals to the starting quarterback. [Explosive-play definitions](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/src/xe_metrics.py), [quarterback calculation](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/src/xe_analysis_followups.py)

I reproduced Purdy’s published number:

| Published component | Value |
|---|---:|
| Games credited to Purdy | 45 |
| Team explosive plays | 349 |
| Team dropbacks | 1,501 |
| Calculated rate | 23.25% |

So **yes, it includes running-back runs—not just Purdy’s passing attempts or his own runs.** It can also include plays by a backup after the starter leaves. Conversely, Purdy’s relief appearances are not individually credited to him. [Published table](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/data/processed/qb_career_explosive_leaders.csv)

This matters because an offense can raise that ratio by producing more explosive rushing plays without adding any dropbacks. It mixes two different sets of opportunities.

**Purdy might still rank highly on a correctly calculated passing statistic. This table cannot establish that.** Nor can it tell us how much comes from his throws, receivers gaining yards after the catch, blocking, or scheme.

I would replace it with three clearly separated measures:

- **Passing explosiveness:** explosive completed passes divided by the actual quarterback’s dropbacks, with sacks and scrambles explicitly defined.
- **Quarterback rushing explosiveness:** scrambles and designed QB runs, reported separately.
- **Team offensive explosiveness:** all explosive plays divided by all eligible offensive plays.

Then split explosive passes into air-yard and yards-after-catch components. That would make “Why Purdy?” an interesting football investigation rather than an argument over a mislabeled number.

**2. A second bug excludes 894 team-games from the quarterback analysis.**

The research notes attribute missing quarterback matches to incomplete historical QB identifiers. I checked the files: all 894 missing matches involve the Rams, Chargers, or Raiders.

The play-by-play uses current abbreviations; the schedule uses historical ones—for example, `LA` versus `STL`. The quarterback names are present. Normalizing those three franchises’ abbreviations reduced unmatched records **from 894 to zero** in my check. [Join code](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/src/xe_analysis_followups.py), [original explanation](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/exploration/FINDINGS_teams.md)

Fixing that join alone leaves Purdy second under the existing flawed measure, but changes other career totals and the continuity sample. This is a real data-coverage correction that should precede further interpretation.

**3. “Explosive plays travel with the quarterback” is not established yet.**

Your proposed before-and-after analysis is exactly the right direction. In fact, the repository already contains an exploratory version:

- 56 qualifying QB moves between teams.
- Correlation of the moving quarterback’s attributed rate before and after: approximately **0.27**.
- Correlation for the old team under its replacement starter: approximately **−0.05**, across 54 cases.

The notes appropriately call this suggestive. Unfortunately, those calculations use the same mixed run/pass measure described above. [QB-movement research](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/exploration/FINDINGS_teams.md)

The site also cites stronger year-to-year correlation when the same quarterback returns. That is compatible with a QB contribution, but it is also compatible with continuity in coaching, receivers, blocking, and offensive philosophy. Successful quarterbacks are more likely to keep their jobs, too.

**Keeping the quarterback and changing the quarterback are not randomly assigned conditions.**

A stronger study would track four observations for each move:

| | Before move | After move |
|---|---|---|
| Departing team | With departing QB | With replacement |
| Receiving team | With previous QB | With incoming QB |

Use several surrounding seasons where possible, compare with similar teams without a QB change, and account for coaching changes, opponents, personnel, injuries, and league trends. Report whether the result survives removing each prominent move in turn.

Darnold would make an excellent illustrated case within that broader study. He should not be the sole evidence. The existing eight-starts-in-consecutive-seasons requirement also misses transitions involving backup or short starting stints—relevant to understanding his complete trajectory.

For now, my recommended conclusion is: **QB continuity is associated with greater persistence in team explosiveness; the amount attributable to the quarterback remains unresolved.**

**4. Can particular stadiums or fan bases be worth more points? Yes—but those are different questions.**

You can estimate whether a team has an unusually large advantage at a particular home venue. Assigning that advantage specifically to fans is harder.

The existing franchise analysis recognizes some of this. It measures a **home/road swing**, which combines what happens at home with what happens away. Its roughly 6.5-point historical Denver swing, for example, is **not** an estimate that Denver’s stadium adds 6.5 points. [Franchise analysis](https://1eyebiney.github.io/gridiron-greatness-rating/home-field-advantage/franchises.html)

For a stadium study, I would:

- Separate stadiums and periods, rather than pool a franchise across decades and relocations.
- Estimate venue effects alongside team strength, with small samples pulled toward the league average.
- Account for travel, rest, altitude, weather, roof, and opponent familiarity.
- Test whether estimated venue advantages persist in later seasons.
- Show uncertainty and test the overall evidence for venue differences before declaring a ranked winner.

To isolate **fan effects**, add attendance restrictions, occupancy, visiting-fan presence, or other crowd measurements. Attendance itself also reflects team success, so simply correlating attendance with winning would not settle it.

The defensible distinction is: **“This venue has an estimated extra home advantage” can be supported without establishing “this fan base causes that advantage.”**

**5. The 2020 crowd claim needs substantial softening.**

The venues page says that nothing else changed and uses the near-zero 2020 home advantage to argue that much of home field is people. That is too strong. [Current explanation](https://1eyebiney.github.io/gridiron-greatness-rating/home-field-advantage/venues.html)

The most useful counterpoint is in **your own data**:

- **2019:** adjusted home advantage approximately **−0.07 points**
- **2020:** approximately **+0.10 points**

Home advantage was already near zero the year before the attendance restrictions. That does not disprove a crowd effect, but it weakens the simple disappearance-and-return story considerably. [Annual results](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/home-field-advantage/data/processed/by_season.csv)

Other conditions changed in 2020, including preseason cancellation and practice restrictions. [NFL’s season review](https://www.nfl.com/news/2020-in-review-inside-the-most-unique-season-in-nfl-history)

A better study would compare games with different attendance restrictions, account for venue and team differences, and examine pre-pandemic trends. Even then, restrictions were not randomly assigned.

**6. Other things a statistically knowledgeable reader would challenge**

| Issue | Why it matters / next step |
|---|---|
| **Explaining a completed game versus predicting the next one** | Final-game explosive plays and turnovers are already part of how the score happened. Keep these associations separate from genuine forecasts using only information available beforehand. The greatness model has walk-forward validation; the explosive-study regressions report training-sample performance. |
| **“More repeatable” versus “more skillful”** | Rare events have noisier measured rates. The site acknowledges this, but its assertion that rarity cannot explain the gap needs a quantified reliability model or simulation. Separate interceptions, fumbles, and fumble recoveries. |
| **“No detectable effect” versus “no effect”** | “No fan base shows up” and “turnovers predict nothing” imply more certainty than an inconclusive estimate supports. Report the range of effects still compatible with the data. |
| **Playoff elimination labels** | The code uses conference-wide win totals and ignores division qualification as well as tiebreakers. These are approximate contention categories, not actual mathematical elimination. That matters when testing what supposedly eliminated fans do. |
| **Cross-era greatness** | A within-season z-score measures separation from contemporaries. It does not establish who would win across eras or eliminate differences in league parity. “Most dominant relative to its league under this model” is a clearer claim. |
| **Uncertainty in ranks and comparisons** | Show plausible ranking ranges or probabilities of being top five. Also account for shared teams, overlapping seasons, and estimated team ratings when calculating uncertainty. Small differences should not become confident ordering. |

Sources: [explosive regression implementation](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/explosive-edge/src/xe_analysis_shift.py), [home-field implementation](https://github.com/1EyeBiney/gridiron-greatness-rating/blob/master/studies/home-field-advantage/src/hfa.py), [greatness methodology](https://1eyebiney.github.io/gridiron-greatness-rating/methodology.html).

One smaller factual correction: the explosive methodology describes EPA as an increase in win probability. **EPA means expected points added; win probability added is WPA.** An EPA threshold also remains closely related to scoring—it does not remove the underlying association with points. [Site methodology](https://1eyebiney.github.io/gridiron-greatness-rating/explosive-edge/methodology.html), [nflfastR field definitions](https://www.nflfastr.com/articles/field_descriptions)

**My priority for your next exchange with Claude**

First correct the QB numerator, individual-player attribution, and franchise joins; regenerate every affected claim. Then soften the quarterback-ownership and crowd-causation language.

The most valuable new research question would be:

**“Does explosive-play ability improve predictions of future performance beyond what we already know from team strength, opponents, and ordinary offensive efficiency?”**

That would establish whether the site has found useful additional information. The QB-movement and stadium studies can then explain where that information comes from.

There are good foundations here: explicit definitions, downloadable data, sensitivity checks, and genuine forward testing in the greatness project. The main weakness is that some compelling stories have advanced further than the measurements supporting them.