---
id: TASK-28
title: T4.1 Pricing module (pure)
status: To Do
assignee: []
created_date: '2026-07-03 15:27'
labels:
  - backend market
dependencies:
  - TASK-19
priority: medium
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the automated market maker described in SPEC.md Section 8: fairValue, buyPrice, sellPrice, and demandPressure decay. No I/O. Along with the objective engine (T2.1), this is the highest-value unit to get right and heavily unit-test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Price rises with rolling personal score and buy pressure
- [ ] #2 Price falls with sell pressure and poor performance
- [ ] #3 The spread always keeps buyPrice greater than or equal to sellPrice
- [ ] #4 Pricing is deterministic given the same inputs
- [ ] #5 Unit tests cover demand pressure decay over time
<!-- AC:END -->
