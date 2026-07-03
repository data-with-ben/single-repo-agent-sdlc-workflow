---
id: TASK-26
title: T3.3 Nightly reveal job (idempotent)
status: To Do
assignee: []
created_date: '2026-07-03 15:27'
labels:
  - backend
dependencies:
  - TASK-25
priority: medium
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Orchestrates the objective engine, team scoring, and game resolution: writes ObjectiveResults and Game scores, credits Dividends and Wallets, and recomputes prices. Runs at reveal time and must be safe to re-run for the same date.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running the job twice for the same gameDate produces identical results (idempotent, keyed on date)
- [ ] #2 Wallets and dividends are not double-credited on re-run
- [ ] #3 A failure mid-run leaves the system in a recoverable state
- [ ] #4 Unit and integration tests run the job over seed data end to end
<!-- AC:END -->
