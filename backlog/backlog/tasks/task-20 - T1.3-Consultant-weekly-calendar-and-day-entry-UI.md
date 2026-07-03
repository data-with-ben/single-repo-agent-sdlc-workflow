---
id: TASK-20
title: T1.3 Consultant weekly calendar and day entry (UI)
status: To Do
assignee: []
created_date: '2026-07-03 15:25'
labels:
  - frontend
dependencies:
  - TASK-19
priority: high
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A week strip showing logged/late/missing state per day, plus a day panel for entering time that shows a live 'points if you submit now' hint. UI should match wireframe 2 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The week strip reflects the real TimeEntry state per day (logged, late, or missing)
- [ ] #2 Submitting a day's entry creates or updates the TimeEntry via the T1.2 lifecycle API
- [ ] #3 The live points hint matches the objective rules defined in SPEC.md Section 6
- [ ] #4 The UI matches the layout described for wireframe 2 (week strip plus day panel)
<!-- AC:END -->
