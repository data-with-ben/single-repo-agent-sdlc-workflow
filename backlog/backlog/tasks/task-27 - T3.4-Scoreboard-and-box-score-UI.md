---
id: TASK-27
title: T3.4 Scoreboard and box score (UI)
status: To Do
assignee: []
created_date: '2026-07-03 15:27'
updated_date: '2026-07-04 01:08'
labels:
  - frontend
dependencies:
  - TASK-26
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
priority: medium
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today's slate stays hidden until reveal; after reveal, a box score shows per-member objective checkmarks and a star-of-game callout. UI should match wireframe 4 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Scores are hidden before reveal for non-admins, per the admin visibility rule in SPEC.md Section 11.3
- [ ] #2 The post-reveal box score matches the computed ObjectiveResults
- [ ] #3 A star-of-game callout is shown per completed game
- [ ] #4 The UI matches the layout described for wireframe 4 (hidden slate pre-reveal, box score post-reveal)
<!-- AC:END -->
