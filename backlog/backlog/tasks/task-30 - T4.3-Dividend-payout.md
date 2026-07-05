---
id: TASK-30
title: T4.3 Dividend payout
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:28'
updated_date: '2026-07-05 04:08'
labels:
  - backend market
dependencies:
  - TASK-26
  - TASK-29
references:
  - feature/task-30-dividend-payout
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - .gitignore
  - backend/pyproject.toml
  - backend/app/dividends.py
  - backend/app/objective_engine.py
  - backend/app/pricing.py
  - backend/app/team_scoring.py
  - backend/app/trading.py
  - backend/tests/test_dividends.py
  - backend/tests/test_objective_engine.py
  - backend/tests/test_pricing.py
  - backend/tests/test_team_scoring.py
  - backend/tests/test_trading.py
  - backlog/backlog/tasks/task-30 - T4.3-Dividend-payout.md
priority: medium
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Wire the dividend rules from SPEC.md Section 8 into the nightly reveal job (extends T3.3): team_win, perfect_day, and star_of_game dividends, paid per share held at the end of the game date.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Correct per-share dividend amounts are credited to holders for team_win, perfect_day, and star_of_game
- [x] #2 Dividends are not double-paid when the reveal job is re-run
- [x] #3 A holder of zero shares receives nothing
- [x] #4 The dividend feed matches the layout described for wireframe 5
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-30 (T4.3 Dividend payout):

Its own description says wire the dividend rules into the nightly reveal job
(extends T3.3), and its declared Dependencies are task-26 and task-29. task-26
does not exist yet (a separate backlog gap already flagged on task-26 itself:
its own description needs task-28/29/30's functionality, which is circular
with this task depending back on it). Rather than block on a job that does
not exist, this task is implemented as a self-contained module using the
pieces that already do exist -- objective_engine (task-22), team_scoring
(task-23), and trading (task-29, ported from its branch since it is not yet
merged) -- so its dividend-computation and crediting logic is fully testable
standalone now, and task-26 (whenever it lands) becomes a thin caller of this
module's functions rather than something this task must wait on.

New module: backend/app/dividends.py, mirroring team_scoring.py's shape (a
pure computation function) plus a DB-writing crediting wrapper (matching
season.py/game_scheduling.py/trading.py's pattern).

1. compute_dividend_awards(objective_results, team_memberships, game_results):
   pure function determining WHO earns WHAT reason for a game_date, before any
   shareholder or wallet concern enters the picture:
   - team_win: every present member of a GameResult's winner_team_id.
   - perfect_day: every ObjectiveResult with perfect_day=True.
   - star_of_game: the top-points present member of the *losing* team (no
     award for a draw or a postponed game, since neither has a losing team).
     SPEC.md Section 8 calls this the top *normalized* performer; this plan
     resolves normalized as each consultant's own ObjectiveResult.points (the
     same points value objective_engine and team_scoring already use per
     consultant) rather than inventing a second normalization scheme --
     flagged for hostile review as a resolved interpretation. Ties broken by
     lowest consultant_id for determinism, also flagged.
   Returns a list of (consultant_id, reason, per_share) tuples using SPEC's
   fixed amounts (team_win=+2, perfect_day=+1, star_of_game=+0.5) as module
   constants. A consultant can appear multiple times (e.g. team_win and
   perfect_day and star_of_game all in the same game_date) -- each is its own
   award/dividend row, matching SPEC's per-reason Dividend rows.

2. Point-in-time shareholding (the real design gap this task must resolve):
   SPEC.md Section 8 says dividends pay per share held at end of the game date, but app.models.Holding only tracks current shares, not historical
   snapshots -- a holder who buys or sells between the game date and whenever
   the payout actually runs would be paid against the wrong share count if
   current Holding were used directly. Resolved by reconstructing point-in-
   time shares from Transaction history (already a complete, timestamped
   ledger): for a given consultant and cutoff (the end of game_date, i.e.
   strictly before the following calendar day), sum every matching
   Transaction's signed shares (positive buy, negative sell) with
   executed_at before the cutoff, for every user who has ever held any
   shares in that consultant. A holder of zero point-in-time shares
   contributes nothing and produces no Dividend row (AC #3).

3. credit_dividends(db, game_date, awards): DB-writing wrapper.
   - AC #2 (idempotency): for each (user_id, consultant_id, game_date, reason)
     combination, skip entirely (no Dividend row, no wallet credit) if a
     Dividend row for that exact combination already exists -- a guard-check
     rather than a delete-and-recredit pattern, since delete-and-recredit
     would require separately reversing the wallet's prior credit and is
     more error-prone for no benefit here.
   - Otherwise: credit the shareholder's Wallet by shares * per_share (get-
     or-create the wallet, matching trading.py's existing helper), and
     record a Dividend row (user_id, consultant_id, game_date, reason,
     shares, per_share, total).

4. dividend_feed(db, user_id, limit=50): a read-only query function
   returning a user's Dividend rows ordered by game_date descending, in the
   shape SPEC.md Section 9's wireframe 5 (Portfolio/exchange: holdings,
   prices, dividends, movers) would need to render a dividends feed
   (consultant_id, game_date, reason, shares, per_share, total). No wireframe
   mockup exists in this repo beyond that one-line description, so this is a
   resolved interpretation of AC #4's feed shape rather than a literal
   layout match -- flagged for hostile review. Backend-only, no HTTP route or
   UI (task-31 owns the actual Portfolio/exchange screen).

5. Tests (backend/tests/test_dividends.py), following the DB-fixture style
   of test_trading.py's DB-integration test classes, plus pure-function
   table-driven tests matching test_team_scoring.py's style for
   compute_dividend_awards:
   - AC #1: each reason's per-share amount matches SPEC exactly; a
     consultant who both wins and has a perfect day and is star of the game
     (on the losing team is impossible simultaneously with team_win, so this
     specific triple only tests team_win + perfect_day together, with a
     separate test for star_of_game alone on the losing side) produces the
     correct set of Dividend rows and correct total wallet credit.
   - AC #2: calling credit_dividends twice with the same awards and game_date
     credits the wallet only once and creates only one set of Dividend rows.
   - AC #3: a user with zero point-in-time shares in a dividend-earning
     consultant receives no Dividend row and no wallet credit; a user who
     sold all shares before the game date (via trading.execute_sell)
     likewise receives nothing even if they still hold shares in OTHER
     consultants.
   - Point-in-time correctness: a user who buys additional shares *after*
     the game date but before credit_dividends runs is still paid against
     their game-date share count, not their current (larger) count --
     directly proving the point-in-time reconstruction is load-bearing, not
     just a passthrough of current Holding.
   - AC #4: dividend_feed returns rows in game_date-descending order with
     all the fields a portfolio/dividends display would need.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (1 warning, 1 confirmation, 1 minor): (1) point-in-time share reconstruction cannot use a 30-day truncation like task-29's demand pressure, since exact counts are required -- O(all historical transactions per consultant) per run, acceptable at current scale, flagged as a scalability limitation to revisit with task-26; (2) confirmed (strengthens the plan, not just a convention) that top normalized performer reduces mathematically to top raw-points performer within one team, since every teammate shares the same divisor; (3) add an explicit test confirming self-holding (a consultant owning shares in themselves) is paid dividends correctly.

E2E TESTS: Skipped -- backend-only service module (dividends.py), no HTTP endpoint or UI surface introduced yet (task-31, the portfolio/exchange UI, will consume dividend_feed). Matches the same rationale as season.py/game_scheduling.py/pricing.py/trading.py.

IMPLEMENTATION NOTES: Added backend/app/dividends.py (compute_dividend_awards pure function + credit_dividends/dividend_feed DB-writing wrappers), following team_scoring.py's pure-plus-wrapper shape. Resolved the core design gap: this task's own description says wire dividends into the nightly reveal job (task-26), which does not exist yet and is itself blocked on this task's functionality (a circular dependency already flagged on task-26). Resolved by implementing this as a self-contained module using pieces that already exist (objective_engine, team_scoring, trading), so task-26 becomes a thin caller rather than a hard blocker. Resolved point-in-time shareholding (SPEC says dividends pay per share held at end of the game date, but Holding only tracks current shares) by reconstructing shares from Transaction history as of a cutoff, since a holder could buy or sell between the game date and whenever the payout actually runs -- verified by a dedicated test proving shares bought after the game date do not inflate the payout. Resolved star_of_game's normalized performer wording: proved it reduces mathematically to top raw-points performer within one team, since every teammate shares the same normalization divisor -- not just a convention, a forced equivalence. Idempotency (AC2) uses a per-(user,consultant,game_date,reason) guard-check rather than delete-and-recredit, avoiding any need to reverse prior wallet credits. Ported pricing.py/trading.py (task-29), team_scoring.py (task-23), and objective_engine.py (task-22) from their branches (none yet merged), plus pytest-cov/.coverage. Tests: 18 new, 100% branch coverage on app.dividends, including a self-holding test and a wallet-auto-creation test. Full backend suite: 173 passed, ruff clean.

CODE REVIEW: Approved with 0 issues. Ruff clean, 173 tests pass, 100% branch coverage on app.dividends. _shareholders_as_of issues one query per distinct historical trader (N+1) -- consistent with the already-flagged acceptable-at-current-scale limitation, no new issue.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
