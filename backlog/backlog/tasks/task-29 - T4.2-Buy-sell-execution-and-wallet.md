---
id: TASK-29
title: T4.2 Buy/sell execution and wallet
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:28'
updated_date: '2026-07-05 03:56'
labels:
  - backend market
dependencies:
  - TASK-28
  - TASK-35
references:
  - feature/task-29-buy-sell-wallet
modified_files:
  - .gitignore
  - backend/pyproject.toml
  - backend/app/pricing.py
  - backend/app/trading.py
  - backend/tests/test_pricing.py
  - backend/tests/test_trading.py
  - backlog/backlog/tasks/task-29 - T4.2-Buy-sell-execution-and-wallet.md
priority: medium
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Execute trades against the market maker from T4.1: enforce the ownership cap and wallet balance from SPEC.md Section 8, and record every trade as a Transaction.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A buy debits the wallet at the quoted price
- [x] #2 A sell credits the wallet at the quoted price
- [x] #3 The ownership cap (default 25%) is enforced, including against self-purchase
- [x] #4 An oversell or an overspend beyond wallet balance is rejected
- [x] #5 Every trade is recorded as a Transaction
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-29 (T4.2 Buy/sell execution and wallet):

This branch depends on task-28 (pricing module), whose branch is not yet merged
into main. Per the established duplicate-across-branches pattern, backend/app/
pricing.py and its test file are ported verbatim onto this branch from
feature/task-28-pricing-module, alongside its pyproject.toml (pytest-cov) and
.gitignore (.coverage) changes. The Holding/Transaction/Wallet SQLAlchemy models
already exist in baseline app/models.py, so no model changes are needed -- this
is a deliberate constraint: SPEC.md Section 4 (marked REQUIRED CONTEXT) lists
the complete data model, and no demand-pressure or market-state entity appears
there, so this task must not invent a new persisted table for it.

Sourcing the quoted price (the real design gap this task must resolve): T4.1's
pricing.py takes rolling_avg_score and demand_pressure as plain float
parameters, computed by whichever caller has DB access. No caller (task-26,
the nightly reveal job) exists yet to maintain a persisted, incrementally-
updated price or demand-pressure value, and SPEC's required data model has no
slot to store one. Resolution: compute both live, at trade time, purely from
data that already exists in the required model --
- rolling_avg_score: query ObjectiveResult for the traded consultant over the
  trailing 10 calendar days ending at the trade's timestamp, average the
  points column, defaulting to 0.0 if no rows exist yet (a new consultant with
  no game history prices at the bare BASE fair value -- a reasonable default,
  not a special case requiring extra logic).
- demand_pressure: replay that consultant's own Transaction history in
  chronological order through pricing.py's decay_demand_pressure +
  apply_trade_pressure functions (decay for the elapsed days between each
  consecutive transaction, then apply that transaction's net shares as buy
  positive / sell negative), arriving at the current pressure as of the new
  trade's timestamp. This reuses task-28's already-tested decay model exactly
  as designed (decay-then-apply, composed by the caller) rather than
  introducing a second, divergent implementation.
This is a resolved interpretation with a real, non-trivial design decision
behind it -- flagged explicitly for hostile review rather than presented as
uncontroversial.

New module: backend/app/trading.py -- DB-writing functions (real I/O),
following the same shape as season.py and game_scheduling.py (both already
established as service-layer modules that use pricing/scheduling's pure logic
underneath).

1. execute_buy(db, user_id, consultant_id, shares, now): quotes the current
   price (per the resolution above), computes total_cost = shares *
   buy_price, and enforces two rejections before mutating anything:
   - AC #4 (overspend): reject with ValueError if the buyer's Wallet balance
     (get-or-create at 0.0 if the row does not exist -- initial wallet funding
     is a separate, out-of-scope concern) is less than total_cost.
   - AC #3 (ownership cap): reject with ValueError if the buyer's existing
     Holding.shares for this consultant plus the new shares would exceed 25%
     of the fixed 100-share supply (a module constant, matching SPEC's
     default), applied uniformly whether or not user_id == consultant_id (no
     self-purchase exemption -- SPEC explicitly says the cap applies incl.
     self).
   If both checks pass: debit the wallet (AC #1), create the Holding row if
   it does not exist or increment its shares, and record a Transaction
   (side=buy, shares, price_per_share=buy_price, total=total_cost,
   executed_at=now) (AC #5).

2. execute_sell(db, user_id, consultant_id, shares, now): quotes the current
   price the same way, then enforces:
   - AC #4 (oversell): reject with ValueError if no Holding row exists for
     (user_id, consultant_id) or its shares are less than the amount being
     sold.
   If it passes: credit the wallet by shares * sell_price (AC #2), decrement
   the Holding's shares, and record a Transaction (side=sell,
   price_per_share=sell_price, total=proceeds, executed_at=now) (AC #5).

3. Both functions validate shares > 0 up front (a zero or negative trade is
   not a valid buy or sell), raising ValueError -- not one of the five ACs
   directly, but a basic input-validity guard the implementation would be
   incomplete without.

4. Tests (backend/tests/test_trading.py), following the DB-fixture style of
   test_season.py / test_game_scheduling.py's DB-integration test classes:
   - AC #1: a buy debits the wallet by exactly shares * buy_price (verified
     against pricing.py's own buy_price formula, not a hardcoded number).
   - AC #2: a sell credits the wallet by exactly shares * sell_price.
   - AC #3: buying up to exactly 25 shares succeeds; buying a 26th share (or
     any amount that would cross 25% of the 100-share supply) is rejected;
     repeated with user_id == consultant_id to prove no self-purchase
     exemption exists.
   - AC #4: a buy that costs more than the wallet's balance is rejected and
     leaves the wallet/holding unchanged; a sell for more shares than are
     held is rejected and leaves the wallet/holding unchanged (both checked
     explicitly, not just that an exception was raised).
   - AC #5: every successful buy and sell produces exactly one Transaction
     row with the correct side/shares/price_per_share/total/executed_at;
     rejected trades produce zero Transaction rows.
   - Price-sourcing correctness: a consultant with strong recent
     ObjectiveResult history prices higher than one with none; a sequence of
     buys measurably raises the quoted price for a subsequent buy (proving
     demand pressure is actually being replayed from Transaction history, not
     silently pinned at zero).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 warning, 2 minor): (1) bound the demand-pressure replay to a trailing window (e.g. 30 days) instead of unbounded transaction history, since decay renders anything older negligible; (2) decide and document whether a Holding row is deleted or left at shares=0 after a full sell -- recommend leaving at 0 for simplicity; (3) define the 10-day rolling-average window boundary precisely, matching existing date-handling conventions in game_scheduling.py/seed.py.

E2E TESTS: Skipped -- backend-only service module (trading.py), no HTTP endpoint or UI surface introduced yet (task-31, the portfolio/exchange UI, will wire this to a route). Matches the same rationale as season.py/game_scheduling.py/pricing.py.

IMPLEMENTATION NOTES: Added backend/app/trading.py (execute_buy/execute_sell), DB-writing service functions matching season.py/game_scheduling.py's shape. Ported pricing.py + its test from task-28's branch (not yet merged, no auto-merge step in this workflow), plus its pyproject.toml (pytest-cov) and .gitignore (.coverage) changes. Resolved the core design gap: pricing.price_quote needs rolling_avg_score and demand_pressure, but no persisted market-state entity exists in SPEC.md Section 4's required data model and no reveal job (task-26) exists yet to maintain one -- resolved by computing both live at trade time purely from existing required entities: rolling_avg_score from a live ObjectiveResult query (trailing 10 days, 0.0 default for no history), demand_pressure by replaying that consultant's own Transaction history (all buyers, since it is a per-consultant market attribute) through pricing.py's own decay_demand_pressure/apply_trade_pressure functions, bounded to a trailing 30-day window per hostile review (decay renders anything older negligible). Holding rows are left at shares=0 after a full sell rather than deleted, per hostile review. Ownership cap (25 of 100 shares) applies uniformly including self-purchase -- verified by a dedicated test with user_id==consultant_id. Tests: 15 new, DB-integration style matching test_season.py/test_game_scheduling.py, covering all 5 ACs plus a wallet-auto-creation edge case and two price-sourcing correctness tests proving rolling-avg-score and demand-pressure are genuinely read from history, not stubbed. Full backend suite: 115 passed, 100% branch coverage on app.trading, ruff clean.

CODE REVIEW: Approved with 0 issues. Ruff clean, 115 tests pass, 100% branch coverage on app.trading. Noted the wallet-balance comparison uses plain floats, consistent with how money/points values are handled everywhere else in this codebase (no Decimal usage anywhere) -- not a new gap, no change needed.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).

SELF-IMPROVEMENT: The T4 market series (task-26, task-28, task-29, task-30) has interleaved dependencies not captured by their declared Dependencies fields -- task-26's reveal job is supposed to recompute/persist prices, but task-29 (buy/sell) needs a live price before task-26 exists, and SPEC.md's required data model has no slot to persist one. This forced two different ad-hoc resolutions in one session (skipping task-26 entirely as premature; computing price live from history for task-29). Recommend the check-for-work or plan-task skill flag tasks whose description references functionality from undeclared, not-yet-built dependencies (detectable by grepping sibling task descriptions for capability keywords the current task's own description also uses) before planning begins, rather than discovering it mid-plan each time.
<!-- SECTION:NOTES:END -->
