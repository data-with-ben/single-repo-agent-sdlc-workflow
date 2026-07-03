---
id: TASK-10
title: Timezone-aware timeliness scoring engine
status: To Do
assignee: []
created_date: '2026-07-03 13:29'
updated_date: '2026-07-03 15:24'
labels:
  - backend fantasy scoring
  - flagged-for-removal
dependencies:
  - TASK-7
  - TASK-9
priority: medium
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The core scoring mechanic: a time entry earns points based on how promptly it was submitted relative to the consultant's own local workday, not server time. The local workday is divided into four two-to-three hour tiers with strictly decreasing points, and anything after the last tier earns zero. Points earned by a consultant's entry are credited to whichever user currently has that consultant on their roster.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A time entry submitted between the start of the local workday and the end of its first tier (9am-12pm local) earns full points
- [ ] #2 A time entry submitted in the second tier (12pm-2pm local) earns fewer points than the first tier
- [ ] #3 A time entry submitted in the third tier (2pm-4pm local) earns fewer points than the second tier
- [ ] #4 A time entry submitted in the fourth tier (4pm-6pm local) earns fewer points than the third tier
- [ ] #5 A time entry submitted after 6pm local, or on a later calendar day, earns zero points
- [ ] #6 Scoring uses the consultant's own timezone from their profile, not the server's timezone or the manager's timezone
- [ ] #7 Points earned from a consultant's time entry are credited to the roster of whichever user currently has that consultant drafted
- [ ] #8 Backend unit tests cover each tier boundary and the timezone-localization logic
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
