---
id: TASK-32
title: T5.1 New-hire IPO at season boundaries
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:28'
updated_date: '2026-07-05 16:53'
labels:
  - backend market future
dependencies:
  - TASK-31
  - TASK-24
references:
  - feature/task-32-new-hire-ipo
modified_files:
  - .gitignore
  - backend/app/main.py
  - backend/app/seed.py
  - backend/pyproject.toml
  - backend/tests/test_seed.py
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
  - backlog/backlog/tasks/task-32 - T5.1-New-hire-IPO-at-season-boundaries.md
priority: low
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
New consultants added to the system enter the market with fresh supply at the start of the next season, rather than being tradable immediately.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A consultant added mid-season becomes tradable at the next season boundary
- [x] #2 The new consultant enters with correct initial supply
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-32 (T5.1 New-hire IPO at season boundaries):

This branch depends on task-31 (portfolio/trading) and task-24 (season), neither
merged into main yet. Ports every module task-31 already ported (objective_engine,
team_scoring, season, game_scheduling, pricing, trading, dividends, reveal,
box_score, portfolio) plus main.py/seed.py, from feature/task-31-portfolio-
exchange-ui -- confirmed a clean superset of the now-merged main this time
(diffed first, per the lesson logged on task-31 about wholesale-copying without
diffing against current main).

Design: a consultant becomes tradable once a season starts on or after their
hire date (User.created_at) -- hired mid-season, they must wait for the next
season boundary. No new persisted state is needed: Season.start_date and
User.created_at (both already in the required data model) are sufficient to
derive this.

1. New function trading.is_tradable(db, consultant_id, now) -> bool: finds the
   active Season (Season.status == active, matching season.py's existing
   query pattern); if none exists, defaults to tradable=True (nothing to gate
   against). Otherwise, tradable = consultant.created_at <= active_season.
   start_date -- hired before or exactly when the current season started.
   A consultant hired after the active season's start_date is not tradable
   until the next start_new_season call updates which season is active.

2. execute_buy enforces this: reject with ValueError (not yet tradable --
   enters the market at the next season boundary) before any wallet/cap
   checks run, if is_tradable returns False. execute_sell does not need an
   equivalent check: a not-yet-tradable consultant has zero Holding rows
   (nobody could have bought them), and execute_sell already rejects
   oversell/zero-holding attempts on its own.

3. AC #2 (correct initial supply): no new supply field exists per
   consultant -- TOTAL_SUPPLY_PER_CONSULTANT (trading.py, task-29) is a
   uniform constant already, not something a new hire needs a special value
   for. This AC is satisfied by proving the existing ownership-cap math
   (25% of the fixed 100-share supply) applies identically to a newly
   tradable consultant once their season boundary arrives, with no
   special-casing that could silently corrupt it -- verified by a test that
   buys up to the cap for a freshly-tradable consultant and confirms it
   succeeds exactly as it would for any other consultant.

4. Tests (backend/tests/test_trading.py, extending the existing file):
   - AC #1: a consultant created after the active season's start_date is
     rejected by execute_buy with a clear tradability error; the same
     consultant becomes tradable once start_new_season is called again
     (simulating the next season boundary) and their created_at now
     precedes the new active season's start_date.
   - AC #1 edge case: a consultant created before or exactly at the active
     season's start_date is tradable immediately (the common case -- most
     consultants exist before any season starts).
   - No-active-season edge case: is_tradable defaults to True when no
     Season row has status active at all.
   - AC #2: buying up to the ownership cap for a freshly-tradable
     consultant succeeds, proving the cap math is unaffected.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 minor): is_tradable's active-season lookup should defensively pick the most-recently-started row if multiple status==active rows ever exist, even though season.py's own invariant should prevent that.

E2E TESTS: Skipped -- backend-only change (trading.py's is_tradable gate on execute_buy), no new HTTP endpoint or UI surface. Matches the rationale for prior backend-only pure/service modules this session.

IMPLEMENTATION NOTES: Added trading.is_tradable(db, consultant_id) -- a consultant is tradable once a season has started on/after their hire date (User.created_at), using Season.status==active as the authoritative current-season flag (matching how the rest of the codebase already treats it, not date math against the caller's clock -- the initial implementation had an unused now parameter, removed after noticing it was dead code). execute_buy rejects a not-yet-tradable consultant before any wallet/cap checks. No new persisted state needed -- Season.start_date and User.created_at (both already in the required data model) are sufficient. Fixed two fixture collisions this change exposed: (1) test_trading.py's _make_user used created_at=NOW, which collided with an unrelated pricing test that creates its own Season purely to satisfy ObjectiveResult's FK -- fixed by backdating the helper's created_at to a fixed past date; (2) seed.py created all Users with created_at=now (today) but the season's start_date is backdated to cover historical TimeEntry data, making every seeded consultant look like a fresh mid-season hire -- fixed by backdating seed.py's staff created_at/Assignment start_date to before the season starts, since the seed script models existing staff, not new hires. Ported objective_engine/team_scoring/season/game_scheduling/pricing/dividends/reveal/box_score/portfolio/main.py/seed.py from task-31's branch (confirmed a clean superset of merged main by diffing first, applying the lesson logged on task-31). Tests: 7 new, 100% branch coverage on app.trading. Full backend suite: 319 passed, ruff clean.

CODE REVIEW: Approved with 0 issues. Ruff clean, 319 tests pass, 100% branch coverage on app.trading. Fixture fixes (backdating pre-existing staff/users) are semantically correct, not workarounds -- these seed/test users genuinely predate any season, they are not the new hires this task's rule targets.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
