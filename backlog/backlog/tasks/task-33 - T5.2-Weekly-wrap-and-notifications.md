---
id: TASK-33
title: T5.2 Weekly wrap and notifications
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:29'
updated_date: '2026-07-05 17:24'
labels:
  - backend frontend future
dependencies:
  - TASK-31
references:
  - feature/task-33-weekly-wrap-notifications
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - .gitignore
  - backend/alembic/versions/e4b7610590cb_initial_schema.py
  - backend/app/main.py
  - backend/app/models.py
  - backend/app/seed.py
  - backend/pyproject.toml
  - backend/tests/test_seed.py
  - e2e/playwright.config.ts
  - frontend/src/App.tsx
  - backend/app/box_score.py
  - backend/app/dividends.py
  - backend/app/game_scheduling.py
  - backend/app/notifications.py
  - backend/app/objective_engine.py
  - backend/app/portfolio.py
  - backend/app/pricing.py
  - backend/app/reveal.py
  - backend/app/season.py
  - backend/app/team_scoring.py
  - backend/app/trading.py
  - backend/app/weekly_wrap.py
  - backend/tests/test_box_score.py
  - backend/tests/test_dividends.py
  - backend/tests/test_game_scheduling.py
  - backend/tests/test_main_games.py
  - backend/tests/test_main_portfolio.py
  - backend/tests/test_main_weekly_wrap.py
  - backend/tests/test_notifications.py
  - backend/tests/test_objective_engine.py
  - backend/tests/test_portfolio.py
  - backend/tests/test_pricing.py
  - backend/tests/test_reveal.py
  - backend/tests/test_season.py
  - backend/tests/test_team_scoring.py
  - backend/tests/test_trading.py
  - backend/tests/test_weekly_wrap.py
  - e2e/tests/portfolio.spec.ts
  - e2e/tests/scoreboard.spec.ts
  - e2e/tests/weekly-wrap-and-nudge.spec.ts
  - frontend/src/Portfolio.test.tsx
  - frontend/src/Portfolio.tsx
  - frontend/src/Scoreboard.test.tsx
  - frontend/src/Scoreboard.tsx
  - backlog/backlog/tasks/task-33 - T5.2-Weekly-wrap-and-notifications.md
priority: low
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A weekly summary (team records, biggest market swing, star performer) and a nudge action letting a user ping an underperforming consultant they hold or roster, without exposing billable content.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A weekly wrap is generated on schedule, covering team records, the biggest market swing, and the star performer
- [x] #2 A nudge action sends a friendly reminder to the target consultant
- [x] #3 A nudge never exposes billable hours or description content, per the privacy invariant in SPEC.md Section 12
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-33 (T5.2 Weekly wrap and notifications):

This branch depends on task-31 (portfolio/trading), not merged into main yet.
Ports every module task-32 already ported (objective_engine, team_scoring,
season, game_scheduling, pricing, trading, dividends, reveal, box_score,
portfolio, main.py, seed.py) from feature/task-32-new-hire-ipo, diffed
against current main first to confirm a clean superset (per the lesson
logged on task-31/confirmed on task-32).

No notification delivery channel (email/push) exists anywhere in this
codebase, and SPEC.md does not specify one -- this task is resolved as an
in-app notification: a nudge action writes a row a recipient can read back,
not an external send. A new Notification model is needed (the first schema
addition since the single initial Alembic migration was written); folded
into that same migration file rather than a new incremental one, matching
this repo's established pre-release pattern (every prior model addition --
Season, Dividend, Holding, Transaction, Wallet, Game, TeamMembership,
ObjectiveResult -- was added the same way, confirmed by inspecting
alembic/versions/e4b7610590cb_initial_schema.py).

1. models.py: Notification(id, recipient_id, sender_id, consultant_id,
   message, created_at, read). message is always a static, privacy-safe
   template string (never TimeEntry.description or actual_hours/
   planned_hours content) -- this is what AC #3's invariant is enforced by
   construction, not by a runtime content filter that could be bypassed.

2. New module backend/app/weekly_wrap.py (pure-ish computation over
   already-persisted data, mirroring portfolio.py's shape):
   - team_records(db, week_start, week_end): per-team win/loss/draw counts
     from Game rows in the window (winner inferred from home_score vs
     away_score, matching box_score.py's own win/loss/draw convention).
   - biggest_market_swing(db, week_start, week_end): the consultant with
     the largest absolute fair_value percentage change across the window,
     reusing trading.quote_for_consultant at both endpoints (the same
     function every other price figure in this app already uses -- no
     second pricing path).
   - star_performer(db, week_start, week_end): the consultant with the
     highest total ObjectiveResult points in the window.
   - generate_weekly_wrap(db, week_start): bundles all three. Called
     on-demand (matching portfolio_summary/box_score's existing pattern);
     the generated-on-schedule wording in AC #1 is a job-scheduling concern
     this app has never owned anywhere (reveal_game_date, task-26, has the
     identical run at reveal time wording and is likewise just a callable
     function some external scheduler invokes) -- not something this task
     introduces a cron/scheduler for.

3. New module backend/app/notifications.py:
   - is_nudge_eligible(db, sender_id, consultant_id): sender currently
     holds shares (Holding.shares > 0) in the consultant, or shares a
     TeamMembership with them in the currently active season (the
     description's held or roster wording). A resolved interpretation,
     flagged for hostile review.
   - send_nudge(db, sender_id, consultant_id, now): raises ValueError if
     not eligible; otherwise creates a Notification for the consultant
     with a fixed, generic template message (no TimeEntry content of any
     kind interpolated into it) (AC #2, #3).
   - list_notifications(db, user_id): a recipient's own notifications,
     most recent first.

4. Three new endpoints in main.py: GET /weekly-wrap?week_start=...,
   POST /nudge {consultant_id}, GET /me/notifications. POST /nudge
   translates a ValueError (not eligible) to 400, matching the existing
   pattern used for trade rejections.

5. Frontend: a small addition to Portfolio.tsx (a Nudge button per
   holding, since eligibility is holding-based for the common case) plus
   a minimal notifications list, rather than a whole new screen -- SPEC.md
   does not name a dedicated wireframe for this feature, and Portfolio is
   already the natural home for holding-scoped actions.

Tests:
- backend/tests/test_weekly_wrap.py: team_records correctness across
  win/loss/draw games; biggest_market_swing picks the correct consultant
  and direction (up or down); star_performer picks the correct consultant;
  generate_weekly_wrap bundles all three.
- backend/tests/test_notifications.py: eligibility via holding and via
  roster/teammate separately; a not-eligible sender is rejected; the
  created Notification's message contains no TimeEntry-sourced content
  (AC #3, verified by asserting the message is drawn from a fixed
  allow-list of template strings, not by string-matching for absence,
  which would not catch a future accidental content leak as reliably as
  the model itself never exposing a code path that could reach
  TimeEntry.description/actual_hours/planned_hours at all).
- backend/tests/test_main_weekly_wrap.py (or similar): endpoint-level
  tests for the 400 rejection and successful nudge/notification-listing/
  weekly-wrap paths.
- frontend/src/Portfolio.test.tsx: extended with a Nudge button test.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 minor, 1 confirmation): (1) with no currently active season, only holding-based nudge eligibility applies -- not a bug, worth stating explicitly; (2) confirmed keeping the nudge message as a fixed, non-parameterized template (no caller-supplied text, no derived per-user status) is the simplest and safest way to guarantee AC3's privacy invariant by construction, not by content filtering -- should not be loosened later without re-evaluating the invariant.

E2E TESTS: 2 new tests passed (weekly-wrap-and-nudge.spec.ts) -- sending a nudge to a held consultant succeeds and shows confirmation; the weekly-wrap endpoint returns a bundled shape for a past week. Also re-verified 7 existing scoreboard/portfolio e2e tests since those features are present on this branch too.

IMPLEMENTATION NOTES: Added a Notification model (folded into the existing single initial Alembic migration, matching this repo's established pre-release pattern of adding every new model there rather than a new incremental migration). Added backend/app/weekly_wrap.py (team_records, biggest_market_swing, star_performer, generate_weekly_wrap -- on-demand, matching portfolio_summary/box_score's pattern; this app has never owned a job scheduler anywhere, reveal_game_date/task-26 is described the same run at reveal time way and is likewise just a callable function) and backend/app/notifications.py (is_nudge_eligible via Holding or same-season TeamMembership, send_nudge, list_notifications). AC3's privacy invariant is enforced by construction: the nudge message is a single fixed constant with zero parameters, never touching TimeEntry.description/actual_hours/planned_hours in any code path. Fixed a real bug caught during implementation: the roster-eligibility check's original query joined TeamMembership to a bare User table without actually scoping by Team.season_id, meaning it would have granted eligibility across ANY historical team membership, not just the current season -- corrected to join through Team and filter on the active season's id. Three new endpoints: GET /weekly-wrap, POST /nudge, GET /me/notifications. Added a Nudge button to Portfolio.tsx per holding. Ported objective_engine/team_scoring/season/game_scheduling/pricing/trading/dividends/reveal/box_score/portfolio/main.py/seed.py/Scoreboard.tsx/Portfolio.tsx from task-32's and task-31's branches (confirmed main.py a clean superset of merged main by diffing first). Tests: 9 new backend pure-function/eligibility tests (100% branch coverage on both new modules), 3 new endpoint tests, 1 new frontend test, 2 new e2e tests. Full backend suite: 342 passed. Frontend: 26 passed. Ruff and eslint clean.

CODE REVIEW: Found and fixed 1 issue during self-review -- Notification.consultant_id was always identical to recipient_id (a nudge always targets the consultant who receives it), a genuinely redundant field not justified by any current requirement. Removed it from the model, migration, and all call sites (YAGNI -- do not re-add without a concrete need for recipient != the nudged consultant). Re-verified: ruff clean, 342 backend + 26 frontend + 9 e2e tests pass, migration applies cleanly, 100% branch coverage on both new modules.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-tests, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
