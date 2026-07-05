---
id: TASK-28
title: T4.1 Pricing module (pure)
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:27'
updated_date: '2026-07-05 03:44'
labels:
  - backend market
dependencies:
  - TASK-19
references:
  - feature/task-28-pricing-module
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - .gitignore
  - backend/pyproject.toml
  - backend/app/pricing.py
  - backend/tests/test_pricing.py
  - backlog/backlog/tasks/task-28 - T4.1-Pricing-module-pure.md
priority: medium
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the automated market maker described in SPEC.md Section 8: fairValue, buyPrice, sellPrice, and demandPressure decay. No I/O. Along with the objective engine (T2.1), this is the highest-value unit to get right and heavily unit-test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Price rises with rolling personal score and buy pressure
- [x] #2 Price falls with sell pressure and poor performance
- [x] #3 The spread always keeps buyPrice greater than or equal to sellPrice
- [x] #4 Pricing is deterministic given the same inputs
- [x] #5 Unit tests cover demand pressure decay over time
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-28 (T4.1 Pricing module, pure):

SPEC.md Section 8 gives the core formulas but leaves the exact demand-pressure
decay curve as an explicitly open decision (Section 11, item 2: Exact BASE/K/
spread and demand-pressure curve -- tune against seed). This plan adopts a
concrete, documented resolution for that open decision, following the same
approach used for task-23's draw-handling interpretation: pick the simplest
defensible model, document it clearly, and flag it for hostile review rather
than leaving it unresolved.

New module: backend/app/pricing.py -- pure functions only, no I/O, mirroring
the shape of objective_engine.py and team_scoring.py (both already pure
modules in this codebase).

1. fair_value(rolling_avg_score): fairValue = BASE + K * rolling_avg_score,
   using the SPEC's suggested starting constants (BASE=2.0, K=0.4) as module
   constants. Clamped at a floor of 0.0 -- SPEC does not say prices can go
   negative, and a negative fair value would be nonsensical for a tradeable
   share; this floor is a resolved interpretation, noted for hostile review.

2. Demand pressure model (the open decision): represented as a single
   decaying scalar per consultant, updated incrementally rather than
   recomputed from full trade history each time (recent net volume, decaying
   over time, per the SPEC's own phrasing):
   - decay_demand_pressure(pressure, days_elapsed, decay_rate=0.8): applies
     pressure * decay_rate ** days_elapsed. At decay_rate=0.8, pressure from
     a single trade fades to under 5% of its original magnitude within about
     two weeks, staying within the spirit of the seed script's ~15-consultant,
     multi-week season without needing per-scenario tuning.
   - apply_trade_pressure(pressure, net_shares, pressure_coefficient=0.01):
     adds net_shares * pressure_coefficient to the (already-decayed) pressure
     value. net_shares is positive for net buys, negative for net sells.
   These two functions are meant to be composed by the caller once per
   trading day: decay first (for however many days elapsed since the last
   update), then apply that day's net trade volume.

3. buy_price(fair_value, demand_pressure) / sell_price(fair_value,
   demand_pressure): implement the SPEC formulas directly using SPREAD=0.06
   as a module constant:
     buyPrice  = fairValue * (1 + spread/2) + demandPressure
     sellPrice = fairValue * (1 - spread/2) - demandPressure
   AC #3 requires buyPrice >= sellPrice always. The raw formulas can violate
   this for large-magnitude demand pressure (buyPrice - sellPrice =
   fairValue*spread + 2*demandPressure, which goes negative once
   demandPressure is very negative enough). Resolved by clamping:
   sell_price is floored so it never exceeds buy_price
   (sell_price = min(raw_sell_price, buy_price)) -- a minimal, explicit
   safeguard rather than an unbounded formula, flagged for hostile review as
   another resolved interpretation.

4. price_quote(rolling_avg_score, demand_pressure): the main public entry
   point, returning a small PriceQuote dataclass (fair_value, buy_price,
   sell_price) by composing steps 1 and 3. This is what most tests and
   future callers (task-29's buy/sell execution) will use directly.

5. Determinism (AC #4): all functions are pure (no randomness, no global
   mutable state, no I/O) -- verified by a test that calls price_quote twice
   with identical inputs and asserts identical outputs, rather than relying
   on the it-is-pure-by-construction assumption alone.

6. Tests (backend/tests/test_pricing.py), table-driven in the same style as
   test_objective_engine.py:
   - AC #1: price_quote's buy_price strictly increases as rolling_avg_score
     increases (holding demand pressure fixed), and strictly increases as
     demand_pressure increases (holding score fixed).
   - AC #2: sell_price strictly decreases as rolling_avg_score decreases and
     as demand_pressure decreases (net selling pressure).
   - AC #3: parametrized sweep across a wide range of demand_pressure values
     (including extreme negative/positive) asserting buy_price >= sell_price
     always holds, proving the clamp actually works rather than just
     inspecting the formula.
   - AC #4: determinism test as described in step 5.
   - AC #5: decay_demand_pressure tests across a range of days_elapsed
     values confirming monotonic decay toward zero, and that
     apply_trade_pressure correctly composes with decay (decay-then-apply
     across multiple simulated trading days converges as expected rather
     than accumulating unboundedly).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 warning, 1 minor): (1) docstring must explicitly state that computing the actual 10-day rolling personal score from historical ObjectiveResult rows is out of scope -- fair_value takes the already-computed rolling average as a plain parameter, not a lookup; (2) decay_rate=0.8 and pressure_coefficient=0.01 are reasonable illustrative defaults but are not empirically tuned against real seed trading data, since task-29's buy/sell execution does not exist yet -- document as an acknowledged limitation to revisit later.

E2E TESTS: Skipped -- backend-only pure pricing module (pricing.py), no HTTP endpoint or UI surface introduced, matching the same rationale as objective_engine.py (task-22), team_scoring.py (task-23), season.py (task-24), and game_scheduling.py (task-25).

IMPLEMENTATION NOTES: Added backend/app/pricing.py, a pure module implementing SPEC.md Section 8's automated market maker formulas: fair_value (BASE=2.0, K=0.4, floored at 0.0), buy_price/sell_price (SPREAD=0.06), and a decaying demand-pressure model (decay_demand_pressure + apply_trade_pressure, decay_rate=0.8, pressure_coefficient=0.01 -- illustrative defaults per SPEC's tune-against-seed note, not yet empirically tuned since task-29's buy/sell execution does not exist yet to generate real trade volume). Resolved the two hostile-review findings: (1) docstring explicitly states that computing the real 10-day rolling personal score from ObjectiveResult history is the caller's responsibility, not this module's; (2) sell_price is floored so it never exceeds buy_price, since the raw SPEC formula can otherwise cross over at large-magnitude negative demand pressure -- verified by a parametrized sweep across team counts and an explicit sanity-check test proving the unclamped formula really would violate the invariant without this floor. Added pytest-cov (duplicate-across-branches pattern, same as task-22/23/24/25) to measure coverage: 100% branch coverage on app.pricing. Tests: 62 new, table-driven in the style of test_objective_engine.py, covering all 5 ACs directly (price-rises, price-falls, spread invariant across an 11x4 sweep of demand-pressure/score combinations, determinism, and decay-over-time including a steady-state convergence check for constant daily volume). Full backend suite: 100 passed.

CODE REVIEW: Approved with 0 issues. Ruff clean, 100 tests pass, 100% branch coverage on app.pricing. Noted sell_price recomputes buy_price internally (called once directly and once inside the clamp) -- negligible for a pure O(1) function, and keeping sell_price independently callable (used directly by tests) is preferable to added complexity; no change needed.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
