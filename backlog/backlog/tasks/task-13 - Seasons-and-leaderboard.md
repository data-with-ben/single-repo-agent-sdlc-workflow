---
id: TASK-13
title: Seasons and leaderboard
status: To Do
assignee: []
created_date: '2026-07-03 13:30'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend fantasy
  - flagged-for-removal
dependencies:
  - TASK-10
  - TASK-12
priority: medium
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ties the fantasy game to a recurring cadence: a season defines the window over which points accumulate and when rosters reset, and a leaderboard shows standings so users can see how they're doing against each other.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A season has a defined start and end date and only one season is active at a time
- [ ] #2 Points earned from scoring accrue to a user's season total, not just a lifetime total
- [ ] #3 A leaderboard shows all users ranked by total points for the current season
- [ ] #4 A user can view a past season's final leaderboard after it has ended
- [ ] #5 When a new season starts, rosters reset so users draft again
- [ ] #6 Backend and frontend unit tests cover season point accrual, leaderboard ranking, and roster reset on season rollover
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
