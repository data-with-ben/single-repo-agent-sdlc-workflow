---
id: TASK-27
title: T3.4 Scoreboard and box score (UI)
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:27'
updated_date: '2026-07-05 14:32'
labels:
  - frontend
dependencies:
  - TASK-26
  - TASK-35
references:
  - feature/task-27-scoreboard-box-score-ui
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - .gitignore
  - backend/app/main.py
  - backend/app/seed.py
  - backend/pyproject.toml
  - e2e/playwright.config.ts
  - frontend/src/App.tsx
  - backend/app/box_score.py
  - backend/app/dividends.py
  - backend/app/game_scheduling.py
  - backend/app/objective_engine.py
  - backend/app/pricing.py
  - backend/app/reveal.py
  - backend/app/season.py
  - backend/app/team_scoring.py
  - backend/app/trading.py
  - backend/tests/test_box_score.py
  - backend/tests/test_dividends.py
  - backend/tests/test_game_scheduling.py
  - backend/tests/test_main_games.py
  - backend/tests/test_objective_engine.py
  - backend/tests/test_pricing.py
  - backend/tests/test_reveal.py
  - backend/tests/test_season.py
  - backend/tests/test_team_scoring.py
  - backend/tests/test_trading.py
  - e2e/tests/scoreboard.spec.ts
  - frontend/src/Scoreboard.test.tsx
  - frontend/src/Scoreboard.tsx
  - backlog/backlog/tasks/task-27 - T3.4-Scoreboard-and-box-score-UI.md
priority: medium
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today's slate stays hidden until reveal; after reveal, a box score shows per-member objective checkmarks and a star-of-game callout. UI should match wireframe 4 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Scores are hidden before reveal for non-admins, per the admin visibility rule in SPEC.md Section 11.3
- [x] #2 The post-reveal box score matches the computed ObjectiveResults
- [x] #3 A star-of-game callout is shown per completed game
- [x] #4 The UI matches the layout described for wireframe 4 (hidden slate pre-reveal, box score post-reveal)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-27 (T3.4 Scoreboard and box score, UI):

wireframe 4's reference image (backlog/backlog/assets/wireframes/games-view.png)
is now attached, resolving this task's stated blocker (UI should match wireframe
4 once that reference image is attached). Its top section is the target for
this task (a stacked games-list + box-score screen); the lower portfolio/
exchange section belongs to task-31 and is out of scope here.

This branch depends on task-26 (reveal job) and task-35 (auth), neither
merged into main yet. Per the established duplicate-across-branches pattern,
this branch ports every module task-26 itself already ported (objective_engine,
team_scoring, season, game_scheduling, pricing, trading, dividends, reveal)
plus their tests, from feature/task-26-nightly-reveal-job, so the reveal
pipeline exists here to actually produce revealed Game/ObjectiveResult rows to
render. app/auth.py (get_current_user, require_role) already exists on main
(task-35 is baseline, not a separate port).

Backend: new module backend/app/box_score.py (pure functions, mirroring
team_scoring.py's shape) plus two new endpoints in main.py.

1. game_summary(game, team_names, is_admin) -> dict: the hidden/revealed
   games-list row shown at the top of the wireframe (team names always
   visible; home_score/away_score only included if game.revealed or
   is_admin, per SPEC.md Section 11 item 3's admin-live-visibility
   recommendation -- AC #1). A non-revealed game's row omits scores
   entirely (matching the wireframe's double-question-mark placeholder) rather than
   sending nulls indistinguishable from a real 0-0 tie.

2. star_of_game(objective_results_for_losing_team) -> consultant_id | None:
   extracted as its own small, independently testable function rather than
   reusing dividends.compute_dividend_awards's internal logic, since that
   function's star_of_game award is skipped entirely when the earning
   consultant has zero shareholders (dividends.credit_dividends never
   creates a Dividend row in that case) -- the box score must show the
   star of the game regardless of whether anyone happens to own that
   consultant's shares. Same tie-break as dividends.py (top points, ties
   broken by lowest consultant_id) for consistency, duplicated rather than
   imported from the private dividends helper (same precedent as
   dividends.py duplicating team_scoring's _present_results).

3. box_score_for_game(game, objective_results, team_memberships,
   team_names) -> dict: the per-player table (name, 11am/same-day/EOD
   checkmarks, points), per-team subtotal normalized per present member
   (matching team_scoring._team_score's own normalization, recomputed
   here directly from the same ObjectiveResult rows already persisted --
   not re-deriving from GameResult, since GameResult isn't itself
   persisted anywhere the API can read it back from), the team-bonus
   callout (AC #2), and the star-of-game callout (AC #3). Only meaningful
   for a revealed game; the endpoint enforces the visibility rule (below),
   not this pure function.

4. GET /games?work_date=YYYY-MM-DD (defaults to today): returns every
   Game for that date via game_summary, gated by get_current_user (AC #1's
   hidden-for-non-admins rule applies per game, not to the whole endpoint
   -- a mixed day with one revealed and one hidden game must show both
   rows correctly).

5. GET /games/{game_id}/box-score: 404 if the game does not exist; 403 if
   the game is not yet revealed and the caller is not an admin (AC #1);
   otherwise returns box_score_for_game's result (AC #2, #3).

Frontend: new component frontend/src/Scoreboard.tsx (matching wireframe 4's
top section: a row of game cards -- team names, a Final vs In-progress-
hidden status, scores or a double-question-mark placeholder -- with the
box score for a selected/most-recent revealed game rendered below, including
the team-bonus and
star-of-game callouts). Wired into App.tsx alongside the existing
components. Uses apiFetch, following WeeklyCalendar.tsx/MorningProjection.tsx's
existing patterns (dev-mode X-User-Id identity, no separate auth flow).

Tests:
- backend/tests/test_box_score.py: pure-function tests for game_summary
  (AC #1: scores present only when revealed or is_admin) and
  star_of_game/box_score_for_game (AC #2: points/checkmarks match the
  ObjectiveResult inputs exactly; AC #3: correct consultant chosen, ties
  broken deterministically, no star for a draw/postponed game).
- backend/tests/test_main_games.py (or similar): endpoint-level tests for
  the 403/404/visibility behavior against a real DB-backed FastAPI
  TestClient, matching test_main_timeentry.py's existing style.
- frontend/src/Scoreboard.test.tsx: renders hidden games as hidden, renders
  a revealed game's box score with checkmarks and the star-of-game
  callout, matching WeeklyCalendar.test.tsx's mocked-fetch pattern.
- e2e/tests/scoreboard.spec.ts: a real end-to-end pass verifying a
  pre-reveal hidden game and a post-reveal box score against the running
  backend, following the existing e2e pattern (backend + frontend
  webServer array already established in playwright.config.ts).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 minor, 1 confirmation): (1) box_score_for_game's objective_results parameter must be documented as app.models.ObjectiveResult (persisted DB rows), not objective_engine.ObjectiveResult (the pure dataclass) -- same name, different module, real confusion risk; (2) confirmed the box-score endpoint's 403 for a hidden game is a defensive backend guarantee, not the primary UX signal -- the frontend should never call it for a hidden game since the games-list response already indicates reveal status.

E2E TESTS: 2 new tests passed (scoreboard.spec.ts) -- a consultant sees the revealed game's real box score with checkmarks, and an admin can access a hidden game's box score (403 for non-admin, 200 for admin). Copied the canonical playwright.config.ts (backend+frontend webServer). Discovered and fixed a real CORS gap: this branch had no CORSMiddleware (the same recurring gap from task-1, not yet merged/duplicated here) -- without it every cross-origin fetch from the Vite dev server silently failed with no visible error, which is why the first e2e run showed an empty games list. Also broadened GET /games's default window from a single exact date to a trailing 5 days, matching wireframe 4's actual layout (todays hidden slate shown alongside the most recently revealed Final game, not just an exact-date match, which would show nothing on an off day).

IMPLEMENTATION NOTES: Added backend/app/box_score.py (game_summary, star_of_game, box_score_for_game -- pure, mirrors team_scoring.py's shape) and two new endpoints (GET /games, GET /games/{id}/box-score) in main.py. Added frontend/src/Scoreboard.tsx matching wireframe 4 (backlog/backlog/assets/wireframes/games-view.png, now attached, resolving this task's stated blocker), wired into App.tsx. Resolved the hostile-review-flagged confusion risk by keeping box_score.py strictly on app.models.ObjectiveResult (persisted rows), not the pure objective_engine dataclass. star_of_game is computed independently from dividends.py's award logic, since that skips creating an award entirely when the earning consultant has no shareholders -- the box score must show the star regardless of share ownership. Extended app/seed.py to schedule and reveal one real day of games (via game_scheduling/reveal, both already built), since without this the Scoreboard would have nothing to render against a freshly seeded database -- necessary, not scope creep, and verified idempotent (test_seed_is_idempotent still passes). Broadened GET /games's default window to a trailing 5 days to match wireframe 4's actual layout (todays hidden slate alongside the most recent Final game). Found and fixed a real CORS gap during e2e testing: this branch had no CORSMiddleware, so every cross-origin fetch from the Vite dev server silently failed -- ported task-1's fix. Ported objective_engine/team_scoring/season/game_scheduling/pricing/trading/dividends/reveal from task-26's branch (none yet merged), plus pytest-cov/.coverage. Tests: 11 new backend pure-function tests (100% branch coverage on box_score.py), 7 new endpoint tests, 5 new frontend tests, 2 new e2e tests. Full backend suite: 293 passed. Frontend: 15 passed. Ruff and eslint clean.

CODE REVIEW: Approved with 0 issues. Ruff and eslint clean, 293 backend + 15 frontend + 2 e2e tests pass, 100% branch coverage on box_score.py. Verified the box-score endpoints correctly gate on is_admin consistently with the existing admin-check pattern elsewhere in main.py.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-tests, notes, code-review, this audit).

SELF-IMPROVEMENT: A missing CORSMiddleware produces a silent failure (empty UI, no console error visible to a script) that took real debugging time to trace back to its root cause here -- the symptom (empty games list) looked identical to a data/seeding bug. This is now the fifth time this exact CORS gap has been independently rediscovered across branches (task-1's original fix, plus duplicates on task-20/21/23-adjacent work, and now here), always because the fix lives on an unmerged branch. Recommend the e2e-tests skill add a fast CORS sanity check (a single OPTIONS preflight request against the backend before running the full suite) so a missing CORSMiddleware fails immediately with a clear, specific error instead of surfacing as a mysterious empty-page assertion failure deep into a test run.
<!-- SECTION:NOTES:END -->
