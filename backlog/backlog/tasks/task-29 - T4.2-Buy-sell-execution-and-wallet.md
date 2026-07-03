---
id: TASK-29
title: T4.2 Buy/sell execution and wallet
status: To Do
assignee: []
created_date: '2026-07-03 15:28'
labels:
  - backend market
dependencies:
  - TASK-28
priority: medium
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Execute trades against the market maker from T4.1: enforce the ownership cap and wallet balance from SPEC.md Section 8, and record every trade as a Transaction.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A buy debits the wallet at the quoted price
- [ ] #2 A sell credits the wallet at the quoted price
- [ ] #3 The ownership cap (default 25%) is enforced, including against self-purchase
- [ ] #4 An oversell or an overspend beyond wallet balance is rejected
- [ ] #5 Every trade is recorded as a Transaction
<!-- AC:END -->
