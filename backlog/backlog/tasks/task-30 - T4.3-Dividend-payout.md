---
id: TASK-30
title: T4.3 Dividend payout
status: To Do
assignee: []
created_date: '2026-07-03 15:28'
labels:
  - backend market
dependencies:
  - TASK-26
  - TASK-29
priority: medium
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Wire the dividend rules from SPEC.md Section 8 into the nightly reveal job (extends T3.3): team_win, perfect_day, and star_of_game dividends, paid per share held at the end of the game date.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Correct per-share dividend amounts are credited to holders for team_win, perfect_day, and star_of_game
- [ ] #2 Dividends are not double-paid when the reveal job is re-run
- [ ] #3 A holder of zero shares receives nothing
- [ ] #4 The dividend feed matches the layout described for wireframe 5
<!-- AC:END -->
