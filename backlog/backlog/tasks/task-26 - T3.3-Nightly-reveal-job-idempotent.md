---
id: TASK-26
title: T3.3 Nightly reveal job (idempotent)
status: To Do
assignee: []
created_date: '2026-07-03 15:27'
updated_date: '2026-07-05 03:37'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
BACKLOG GAP: This task's Dependencies field only lists TASK-25, but its own description requires crediting Dividends and Wallets and recomputing prices -- functionality owned by TASK-28 (pricing), TASK-29 (buy/sell/wallet), and TASK-30 (dividend payout), none of which exist yet in any branch. Not implementable until those land. Recommend adding them as declared dependencies. Skipped for now in favor of TASK-28, which has no such blocker.
<!-- SECTION:NOTES:END -->
