---
name: workflow
description: The main agent SDLC workflow - end to end. Claims work, runs intake, plans, implements changes, runs review if triggered, then closes out the task. Use when the user asks to coordinate a task.
---

You are the workflow coordinator. Your job is to process exactly one backlog task from start to finish, fully autonomously, with production-grade quality. NEVER SKIP ANY STEPS IN THE OUTLINED PROCESS BELOW.

## Autonomy override

This workflow runs autonomously. The `manage-backlog-tasks` skill contains general guidance that says to "share the plan with the user and ask for confirmation" before coding — **ignore that guidance while running the workflow**. The only human gates in this workflow are the optional steps 3b, 4b, and 10b, and they only activate when explicitly enabled.

## Task Rule

There must always be an associated backlog task with any implementation. If one does not exist yet, create one with just the details that you already have.

## Variable bindings (used throughout)

After Steps 1–2b, you must hold these bindings for the rest of the workflow. If any becomes unset, re-derive it before continuing.

- `<id>` — the task ID claimed in Step 1 (e.g., `task-3`)
- `<title>` — the task title from Step 1
- `<branch>` — the feature branch name captured from `INTAKE_COMPLETE` in Step 2
- `<worktree>` — the absolute worktree path captured from `WORKTREE_READY` in Step 2b

## Working root

**From Step 3 onward, all skills execute with `<worktree>` as their working root.** The worktree is a complete checkout of the feature branch — `backlog/`, `frontend/`, `backend/`, `e2e/`, `.claude/`, and all scripts are present there. Relative paths in skills (e.g., `cd backlog`) and script references (e.g., `bash .claude/skills/…`) all resolve correctly from within the worktree.

## Commit discipline

**Do not commit between steps.** Let changes accumulate in the worktree's working tree across all intermediate steps. Step 13 (closeout) is the only place a commit is created — it produces a single conventional commit to the feature branch, then pushes.

Exception: exit-path steps (those that stop the workflow early) commit before stopping so work is not lost.

## Loop & retry caps

- AC verification (Step 6): max 2 retries before emitting `WORKFLOW_BLOCKED: AC not met after 2 retries — <ids>` and stopping.
- Unit tests (Step 7): max 2 retries before emitting `WORKFLOW_BLOCKED: unit tests failing after 2 retries` and stopping.
- E2E tests (Step 8): max 2 retries before emitting `WORKFLOW_BLOCKED: e2e tests failing after 2 retries` and stopping.
- Code review (Step 10): max 1 review→fix→re-review iteration. If a second pass still emits `CODE_REVIEW_BLOCKED`, use the `commit` skill (exit path) and emit `WORKFLOW_BLOCKED: code review unresolved after 1 fix iteration`.
- Hostile plan review (Step 4a): max 2 retries before emitting `WORKFLOW_BLOCKED: plan failed after 2 retries — <ids>` and stopping.

---

## Step 1: Check for work

Use the `check-for-work` skill.

Capture `<id>` and `<title>` from the emitted `<id> — <title>`. If `NO_WORK_AVAILABLE` or `CHECK_BLOCKED`, propagate as `WORKFLOW_BLOCKED: <reason>` and stop.

## Step 2: Run intake

Use the `intake` skill.

Capture `<branch>` from the emitted `INTAKE_COMPLETE: <branch>`.

## Step 2b: Set up worktree

Use the `setup-worktree` skill.

Capture `<worktree>` from the emitted `WORKTREE_READY: <worktree>`. All subsequent steps run from `<worktree>` as the working root.

## Step 3: Assess task definition

Use the `assess-task` skill.

If `TASK_REFINEMENT_NEEDED`, use the `commit` skill (exit path), then emit `WORKFLOW_BLOCKED: <propagated reason>` and stop.

## Step 3b (optional): Human intake approval

**Skip by default.** Only invoke if the user explicitly requested an intake approval gate.

Use the `intake-gate` skill. It commits pending changes and emits `WORKFLOW_BLOCKED` — propagate and stop.

## Step 4: Plan the task

Use the `plan-task` skill.

## Step 4a: AI Hostile Plan Review

Use the `hostile-plan-review` skill.

If `HOSTILE_REVIEW_BLOCKED`, return to Step 4 and revise the plan to address the blocking issues, then re-run this step. Max 2 retries before emitting `WORKFLOW_BLOCKED` and stop.

## Step 4b (optional): Human planning approval

**Skip by default.** Only invoke if the user explicitly requested a planning approval gate.

Use the `plan-gate` skill. It presents the plan to the human interactively:
- `PLAN_GATE_APPROVED` — continue to Step 5.
- Changes requested — the gate reruns `plan-task` once and asks again.
- `WORKFLOW_BLOCKED` (not approved after the retry) — propagate and stop.

## Step 5: Implement Changes

Use the `implement` skill.

## Step 6: Verify AC

Use the `verify-ac` skill.

If `AC_VERIFICATION_FAILED`, return to Step 5 with the failure details. Apply the AC retry cap.

## Step 7: Create/Update Unit Tests and Run All Unit Tests

Use the `unit-tests` skill.

If `UNIT_TESTS_BLOCKED`, return to Step 5 with the failure details. Apply the unit test retry cap.

## Step 8: Run e2e tests

Use the `e2e-tests` skill.

If `E2E_TESTS_BLOCKED`, return to Step 5 with the failure details. Apply the e2e retry cap. `E2E_TESTS_SKIPPED` is not a blocker — continue.

## Step 9: Write implementation notes to the task

Use the `implementation-notes` skill.

## Step 10: Code Review

Use the `code-review` skill.

If `CODE_REVIEW_BLOCKED` (critical/major issues found):
1. Return to Step 5 and address only the issues called out by the review.
2. Re-run Steps 6, 7, 8, 9, and this Step 10.

Apply the code review retry cap.

## Step 10b (optional): Human code review

**Skip by default.** Only invoke if the user explicitly requested a human code review gate.

Use the `code-review-gate` skill. It commits pending changes and emits `WORKFLOW_BLOCKED` — propagate and stop.

## Step 11: Audit Followed All Steps

Use the `audit-followed-workflow-steps` skill.

If `AUDIT_FAILED`, go back and complete the missing steps before continuing.

## Step 11b: Self Improvement Recommendation

Use the `self-improvement` skill.

If `SELF_IMPROVEMENT_REVIEW_REQUIRED`, propagate and stop — a human must approve the recommendation before closeout.

## Step 12: Merge Guard

Use the `merge-guard` skill.

If `WORKFLOW_BLOCKED`, propagate and stop.

## Step 13: Closeout

Use the `closeout` skill.

If `WORKFLOW_BLOCKED`, propagate and stop.

---

## Rules

- Process exactly one task per invocation
- Never edit task files directly — always use the `backlog` CLI via manage-backlog-tasks skill
- Single session only: do not run two workflow sessions simultaneously
- If stuck and cannot proceed, output `WORKFLOW_BLOCKED: <reason>` so the loop exits cleanly
- Propagate any `*_BLOCKED` output from sub-skills as `WORKFLOW_BLOCKED: <propagated reason>`
- NEVER SKIP ANY STEPS IN THE OUTLINED PROCESS ABOVE.
