---
id: TASK-22
title: T2.1 Objective engine module (pure)
status: To Do
assignee: []
created_date: '2026-07-03 15:26'
updated_date: '2026-07-04 01:08'
labels:
  - backend scoring
dependencies:
  - TASK-19
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
priority: high
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A pure function (TimeEntry[], date, ptoCalendar) -> ObjectiveResult[] implementing all scoring rules from SPEC.md Section 6, with no I/O. This and the pricing module (T4.1) are the two highest-value, most heavily tested units in the system.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Returns correct per-consultant results for projected-by-11, logged-same-day, EOD, and perfect-day objectives, with points totals capped at 30
- [ ] #2 Respects PTO exclusion and the no-assigned-work-means-neutral rule
- [ ] #3 Reads only transition timestamps, never mutable state
- [ ] #4 Achieves at least 90% branch coverage with table-driven tests
- [ ] #5 Tests cover edge cases: exactly 11:00, a description just under and just over the minimum length, mixed multi-client days, and all-PTO days
<!-- AC:END -->
