---
id: TASK-11
title: 'Streak bonus, completeness bonus, and missed-day penalty scoring'
status: To Do
assignee: []
created_date: '2026-07-03 13:29'
updated_date: '2026-07-03 15:24'
labels:
  - backend fantasy scoring
  - flagged-for-removal
dependencies:
  - TASK-10
priority: medium
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extends the timeliness scoring engine with three additional mechanics that reward consistency and detail, and punish silence: a streak bonus for consecutive on-time entries, a completeness bonus for detailed descriptions, and a penalty for a day that passes with no entry at all.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A consultant who submits on-time entries for a configurable number of consecutive workdays earns a streak bonus on top of the base tier points
- [ ] #2 A missed on-time day resets the consultant's streak back to zero
- [ ] #3 A time entry whose description meets a minimum length/detail threshold earns a completeness bonus
- [ ] #4 A workday that passes with no time entry logged at all applies a negative point penalty to the consultant's current roster holder
- [ ] #5 Streak, completeness, and missed-day scoring are each independently configurable (thresholds and point values)
- [ ] #6 Backend unit tests cover streak accrual, streak reset, the completeness threshold, and the missed-day penalty
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
