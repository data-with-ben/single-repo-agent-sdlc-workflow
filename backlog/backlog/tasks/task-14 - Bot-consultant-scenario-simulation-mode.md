---
id: TASK-14
title: Bot consultant scenario simulation mode
status: To Do
assignee: []
created_date: '2026-07-03 13:30'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend fantasy future
  - flagged-for-removal
dependencies:
  - TASK-13
priority: low
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A fun, later-stage addition: fake/bot consultants whose timesheet submission behavior is simulated automatically, so users can watch a season play out (or practice drafting/trading) without needing a full roster of real consultants. Explicitly deferred until the core timesheet and fantasy features are built and stable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A manager or super admin can enable a scenario with a configurable number of bot consultants
- [ ] #2 Bot consultants automatically generate time entries with varied, randomized submission timing across the scoring tiers
- [ ] #3 Bot consultants are draftable and score points through the same scoring engine as real consultants
- [ ] #4 A scenario can be run at accelerated speed so a season completes in minutes rather than real time
- [ ] #5 Bot consultants are visually distinguishable from real consultants in the draft pool and leaderboard
- [ ] #6 Backend unit tests cover bot time-entry generation and its integration with the scoring engine
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
