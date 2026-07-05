---
id: TASK-31
title: T4.4 Portfolio and exchange (UI)
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:28'
updated_date: '2026-07-05 16:32'
labels:
  - frontend market
dependencies:
  - TASK-30
  - TASK-35
references:
  - feature/task-31-portfolio-exchange-ui
modified_files:
  - .gitignore
  - backend/app/main.py
  - backend/app/seed.py
  - backend/pyproject.toml
  - backend/tests/test_app.py
  - backend/tests/test_seed.py
  - frontend/src/App.tsx
  - backend/app/box_score.py
  - backend/app/dividends.py
  - backend/app/game_scheduling.py
  - backend/app/objective_engine.py
  - backend/app/portfolio.py
  - backend/app/pricing.py
  - backend/app/reveal.py
  - backend/app/season.py
  - backend/app/team_scoring.py
  - backend/app/trading.py
  - backend/tests/test_box_score.py
  - backend/tests/test_dividends.py
  - backend/tests/test_game_scheduling.py
  - backend/tests/test_main_games.py
  - backend/tests/test_main_portfolio.py
  - backend/tests/test_objective_engine.py
  - backend/tests/test_portfolio.py
  - backend/tests/test_pricing.py
  - backend/tests/test_reveal.py
  - backend/tests/test_season.py
  - backend/tests/test_team_scoring.py
  - backend/tests/test_trading.py
  - e2e/tests/portfolio.spec.ts
  - e2e/tests/scoreboard.spec.ts
  - frontend/src/Portfolio.test.tsx
  - frontend/src/Portfolio.tsx
  - frontend/src/Scoreboard.test.tsx
  - frontend/src/Scoreboard.tsx
  - backlog/backlog/tasks/task-31 - T4.4-Portfolio-and-exchange-UI.md
priority: medium
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Holdings screen showing live buy/sell prices, 7-day movement, yesterday's dividends, market movers, and the ability to browse and trade. UI should match wireframe 5 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The screen shows the user's real holdings and live quotes from the pricing module
- [x] #2 Buy and sell actions call the T4.2 trade execution endpoints
- [x] #3 The dividend feed reflects the results of the last reveal
- [x] #4 Market movers and 7-day movement are displayed
- [x] #5 The UI matches the layout described for wireframe 5 (holdings, quotes, dividend feed, movers, browse/exchange)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-31 (T4.4 Portfolio and exchange, UI):

wireframe 5's reference image is the same file already attached for task-27
(backlog/backlog/assets/wireframes/games-view.png) -- its lower half (Your
portfolio / Yesterday's dividends / Market movers) is the target here; the
upper games/box-score half belongs to task-27 and is already built.

This branch depends on task-30 (dividends) and task-35 (auth, already
baseline on main). Rebased cleanly onto the now-merged main (PR #1/task-1),
picking up CORSMiddleware and the health endpoint for free -- no need to
duplicate those here. Still ports objective_engine/team_scoring/season/
game_scheduling/pricing/trading/dividends/reveal/box_score from task-27's
branch (the most complete accumulated set so far), since none of those are
merged yet either.

Public API refactor (a real, necessary change, not scope creep): trading.py's
price-quoting logic (_quote, _rolling_avg_score, _current_demand_pressure) is
currently private to that module. task-31 needs the exact same quoting logic
for two new purposes -- the portfolio's live price display, and a 7-day-ago
comparison for movement percentages -- and it must be the same logic
execute_buy/execute_sell already charge against, not a re-derived
approximation that could silently drift from the real transaction price.
Renamed to a public quote_for_consultant(db, consultant_id, as_of), with
execute_buy/execute_sell updated to call it; no behavior change, verified by
re-running trading.py's existing test suite unchanged.

New backend module: backend/app/portfolio.py.

1. holdings_view(db, user_id) -> list[dict]: every Holding row for user_id
   with shares > 0, joined with the held consultant's display_name, a live
   quote_for_consultant(db, consultant_id, now) (AC #1), and a 7-day
   movement percentage comparing today's fair_value against
   quote_for_consultant(db, consultant_id, now - 7 days)'s fair_value.

2. market_movers(db, limit=3) -> dict: ranks every active consultant by the
   same 7-day fair_value percentage change, returning the top `limit`
   gainers and top `limit` losers (AC #4). This is a resolved
   interpretation of an undefined term (SPEC.md Section 9 names movers
   in the screen list but never defines the ranking) -- flagged for
   hostile review. A short descriptive blurb per mover (recent team_win
   count from Dividend rows, missed-projection count from ObjectiveResult
   rows, both over the same trailing 7 days) is included for context,
   without attempting to reproduce the wireframe's exact narrative
   phrasing (a PTO-return detector would need historical status-change
   tracking that does not exist anywhere in the required data model).

3. dividend_feed is already built (dividends.py, task-30) and reused
   directly for the yesterday's-dividends section (AC #3) -- no new
   backend logic needed, just wiring.

4. Two new endpoints in main.py:
   - GET /me/portfolio: wallet balance, holdings_view's result, this
     user's recent dividend_feed, and market_movers -- one bundled call
     matching the wireframe's single combined screen, rather than forcing
     the frontend to make four separate round trips.
   - POST /trade/buy and POST /trade/sell: thin wrappers around
     trading.execute_buy/execute_sell for the current authenticated user
     (AC #2), translating trading.py's ValueError rejections (insufficient
     balance, ownership cap, oversell) into 400 responses with the
     original message, matching the existing error-translation pattern
     already used for IllegalTransitionError in the time-entry endpoints.

Frontend: new component frontend/src/Portfolio.tsx (matching the wireframe's
lower section: wallet balance, holdings table with live price/7-day movement/
buy-sell buttons, yesterday's dividends list, market movers list), wired into
App.tsx alongside Scoreboard. Buy/sell buttons call the new endpoints and
reload the portfolio view on success; a rejected trade (400) surfaces the
backend's message rather than failing silently.

Tests:
- backend/tests/test_portfolio.py: holdings_view matches actual Holding/
  quote data (AC #1); market_movers ranks correctly and includes both a
  gainer and a loser given a spread of recent performance; 7-day movement
  percentage is computed correctly against a real quote_for_consultant
  call from 7 days prior, not a hardcoded stand-in.
- backend/tests/test_main_portfolio.py: endpoint-level tests for /me/
  portfolio's bundled shape and /trade/buy, /trade/sell's success and
  400-rejection paths (ownership cap, insufficient balance, oversell),
  matching test_main_games.py's DB-backed TestClient style.
- frontend/src/Portfolio.test.tsx: renders holdings with live prices and
  7-day movement, dividend feed, and market movers from mocked fetch data;
  clicking Buy/Sell calls the correct endpoint.
- e2e/tests/portfolio.spec.ts: a real pass against the seeded backend
  verifying the portfolio screen renders and a buy/sell action succeeds
  end to end.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 warning, 1 confirmation): (1) GET /me/portfolio must not create a Wallet row as a side effect of a read -- default to 0.0 in-memory if none exists, unlike the buy/sell endpoints which legitimately get-or-create; (2) confirmed quote_for_consultant's as_of parameter correctly reconstructs historical prices from only data that existed at that point, since it is the exact same function execute_buy/execute_sell already charge against.

E2E TESTS: 3 new tests passed (portfolio.spec.ts) -- real holdings with live quotes render, a buy action calls the trade endpoint and updates the wallet, browsing the exchange lists a consultant not yet held. Also ported and re-verified scoreboard.spec.ts (2 tests) since the Scoreboard feature is also present on this branch.

IMPLEMENTATION NOTES: Added backend/app/portfolio.py (holdings_view, market_movers, exchange_listing, portfolio_summary) and three new endpoints in main.py (GET /me/portfolio, GET /exchange, POST /trade/buy, POST /trade/sell). Added frontend/src/Portfolio.tsx matching the wireframe's lower section, wired into App.tsx alongside Scoreboard. Refactored trading.py's private _quote to a public quote_for_consultant, reused for the portfolio's live prices and 7-day movement comparison -- the exact same function execute_buy/execute_sell already charge against, not a second independently-derived pricing path, verified by re-running trading.py's unchanged test suite. Resolved market movers (undefined by SPEC) as top gainers/losers by 7-day fair_value percentage change, with a blurb (recent team_win count, recent missed-projection count) from data that already exists. Discovered AC5 (browse/exchange) was not covered by holdings-only buy/sell -- added GET /exchange plus a Browse the exchange toggle in the UI, letting a user discover and buy a consultant not currently held. Rebased this branch onto the now-merged main (PR #1/task-1) from within the worktree (not the main checkout, which has an unrelated stray uncommitted change) -- picked up CORSMiddleware and the health endpoint for free; still had to restore /health after wholesale-copying task-27's main.py, which predates that merge. Extended seed.py with two demo trades (giving the player-manager real holdings) so the Portfolio screen has visible data in a freshly seeded environment -- updated test_seed_produces_expected_data accordingly. Ported objective_engine/team_scoring/season/game_scheduling/pricing/dividends/reveal/box_score/Scoreboard.tsx from task-27's branch (none yet merged). Tests: 12 new backend pure-function tests (100% branch coverage on portfolio.py), 8 new endpoint tests, 6 new frontend tests, 3 new e2e tests (plus 2 re-verified scoreboard e2e tests). Full backend suite: 313 passed. Frontend: 25 passed. Ruff and eslint clean.

CODE REVIEW: Approved with 0 issues. Ruff and eslint clean, 313 backend + 25 frontend + 5 e2e tests pass, 100% branch coverage on portfolio.py. Hardcoded shares=1 per buy/sell click matches the wireframe (no quantity selector); N+1 query pattern in market_movers/exchange_listing is consistent with the already-accepted scale tradeoff from task-29/30.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-tests, notes, code-review, this audit).

SELF-IMPROVEMENT: Wholesale-copying a shared file (main.py) from an unmerged dependency branch during the duplicate-across-branches pattern silently regressed an endpoint (/health) that had landed on main independently via a different, already-merged PR -- the copied branch predated that merge and was trusted as a superset without diffing against current main first. Recommend the duplicate-across-branches guidance (wherever it is documented) add: before wholesale-copying a shared file from another unmerged branch, diff it against the current main version of that same file to catch anything main has gained independently, not just assume the source branch is a strict superset. Separately (a reusable technique, not a gap): rebasing a feature branch onto an updated main from within its own worktree -- rather than the primary repo checkout -- avoids conflicts with unrelated stray uncommitted changes that may exist in the main checkout.
<!-- SECTION:NOTES:END -->
