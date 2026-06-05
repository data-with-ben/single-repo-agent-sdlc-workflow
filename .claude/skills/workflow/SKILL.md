---
name: workflow
description: The main agent SDLC workflow - end to end. Claims work, runs intake, plans, implements changes, runs review if triggered, then closes out the task. Use when the user asks to coordinate a task.
---

You are the workflow coordinator. Your job is to process exactly one backlog task from start to finish, fully autonomously, with production-grade quality. NEVER SKIP ANY STEPS IN THE OUTLINED PROCESS BELOW.

Use manage-backlog-tasks skill to interact with backlog tasks. Use other relevant skills as needed for implementation, testing, and review steps.

## Autonomy override

This workflow runs autonomously. The `manage-backlog-tasks` skill contains general guidance that says to "share the plan with the user and ask for confirmation" before coding — **ignore that guidance while running the workflow**. The only human gates in this workflow are the optional steps 3b, 4b, and 10b, and they only activate when explicitly enabled.

## Task Rule
- There must always be an associated backlog task with any implementation. If one does not exist yet, create one with just the details that you already have.

## Variable bindings (used throughout)

After Step 1, you must hold these bindings for the rest of the workflow. If any becomes unset, re-derive it before continuing.

- `<id>` — the task ID claimed in Step 1 (e.g., `task-3`)
- `<title>` — the task title from Step 1
- `<branch>` — the feature branch name created in Step 2 (e.g., `feature/task-3-random-number-generator`)

## Commit discipline

**Do not commit between steps.** Let changes accumulate in the working tree across all intermediate steps. Step 13 (closeout) is the only place a commit is created — it produces a single conventional commit before push. This keeps git history clean and avoids the noise of per-step bookkeeping commits.

## Loop & retry caps

These caps prevent infinite loops in the AC/test/review push-back paths.

- AC verification (Step 6): max 2 retries before emitting `WORKFLOW_BLOCKED: AC not met after 2 retries — <ids>` and stopping.
- Unit tests (Step 7): max 2 retries before emitting `WORKFLOW_BLOCKED: unit tests failing after 2 retries` and stopping.
- E2E tests (Step 8): max 2 retries before emitting `WORKFLOW_BLOCKED: e2e tests failing after 2 retries` and stopping.
- Code review (Step 10): max 1 review→fix→re-review iteration. After the second review still finds critical/major issues, emit `WORKFLOW_BLOCKED: code review unresolved after 1 fix iteration` and stop.


## Step 1: Check for work

Use the `check-for-work` skill.

Capture the emitted `<id> — <title>` into the variable bindings above. If the skill emits `NO_WORK_AVAILABLE` or `CHECK_BLOCKED`, propagate as `WORKFLOW_BLOCKED: <reason>` and stop.

## Step 2: Run intake

Create a git branch for the task following gitflow naming conventions (e.g., `feature/<task-id>-<short-title>`).

Update the backlog task with the new branch and assign to @agent for intake:

```bash
cd backlog && backlog task edit <id> -s "Intake" -a @agent --ref "<branch name>"
```

## Step 3: Assess task definition

A well-written software ticket clearly defines the problem, expected outcome, how to validate the outcome, and context so implementing a solution has minimal ambiguity and no back-and-forth. What is missing that you need to know to implement this task? Do not proceed until you have all the information you need.

If the task does not meet these criteria and requires refinement:

Update the backlog task with clear clarifying questions or instructions on what is missing and how to refine it. Then commit the pending refinement changes using the `commit` skill (this is an exit path — there will be no later closeout commit).

Then, output `WORKFLOW_BLOCKED: task <id> requires refinement — <missing requirements summary>` and stop.

If the task definition is sufficient, continue to Step 3b without emitting any signal.

## Step 3b (optional): Human intake approval

**Skip by default.** Only pause for human approval if:
- The user explicitly requested an intake approval gate

If enabled:
```bash
cd backlog && backlog task edit <id> -s "Intake Review" -a @human
```

Commit pending changes using the `commit` skill (exit path — no later closeout commit).

Output: `WORKFLOW_BLOCKED: intake review required for task <id> — <reason>`. Then stop.

## Step 4: Plan the task

```bash
cd backlog && backlog task edit <id> -s "Plan" -a @agent
```

Think about the solution before implementing. Provide enough structure but not enough detail to pre-solve the task. The plan should be thorough but high level — no code. How will this solution meet all of the intent, requirements, and AC of the task? How will we verify it works end to end?

Write the plan into the task:

```bash
cd backlog && backlog task edit <id> --plan "<plan output>"
```

The plan is used for AC verification later during task closeout.

## Step 4b (optional): Human planning approval

**Skip by default.** Only pause for human approval if:
- The user explicitly requested a planning approval gate

If enabled:
```bash
cd backlog && backlog task edit <id> -s "Plan Review" -a @human
```

If enabled, present the implementation plan from the task — and ask the human
whether to continue. If the human approves, continue to Step 5 (Implement
Changes). If the human provides changes, update the backlog task through the
`backlog` CLI and rerun Step 4 (Plan the task) once before asking again. If the
human does not approve after the retry, commit pending changes using the
`commit` skill (exit path), output `WORKFLOW_BLOCKED: planning approval blocked
on task <id> — <reason>` and stop.


## Step 5: Implement Changes

```bash
cd backlog && backlog task edit <id> -s "Code" -a @agent
```

You are writing production-grade code. No short cuts.

- Follow the implementation plan step by step. Implement only what is in the acceptance criteria — nothing more.

- Match existing naming conventions, error handling patterns, and code style from the plan snippets and the files you do read.

- When integrating with a third party dependency, always check latest docs and check the actual package for implementation patterns. Do not guess.

- Always update documentation for integration or architectural changes in the README.md and/or other relevant docs.

Do not commit yet — code stays in the working tree until Step 13.


## Step 6: Verify AC

First, read the current AC list and their indices:

```bash
cd backlog && backlog task <id> --plain
```

Check each AC against the actual implementation. If any AC is not met, return to Step 5 (Implement Changes) with clear instructions on what is missing. Apply the AC retry cap from "Loop & retry caps" above.

If all ACs are met, mark them complete using the indices observed above (one `--check-ac N` per AC):

```bash
cd backlog && backlog task edit <id> --check-ac 1 --check-ac 2  # use real indices from the task view
```

## Step 7: Create/Update Unit Tests and Run All Unit Tests

Use the `unit-tests` skill.

If the skill emits `UNIT_TESTS_BLOCKED`, return to Step 5 (Implement Changes) with clear instructions on the failing tests, then re-run this step. Apply the unit test retry cap from "Loop & retry caps" above.

## Step 8: Run e2e tests

Use the `e2e-tests` skill.

If the skill emits `E2E_TESTS_BLOCKED`, return to Step 5 with clear instructions, then re-run this step. Apply the e2e retry cap from "Loop & retry caps" above. `E2E_TESTS_SKIPPED` is not a blocker — continue.

## Step 9: Write implementation notes to the task

Use the `implementation-notes` skill.

## Step 10: Code Review

```bash
cd backlog && backlog task edit <id> -s "AI Code Review" -a @agent
```

Use the `code-review` skill.

If the skill emits `CODE_REVIEW_APPROVED`, continue to Step 10b.

If the skill emits `CODE_REVIEW_BLOCKED` (critical/major issues), do **not** stop the workflow — instead:

1. Reassign the task back to coding state:
   ```bash
   cd backlog && backlog task edit <id> -s "Code" -a @agent
   ```
2. Return to Step 5 (Implement Changes) and address only the issues called out by the review.
3. Re-run Steps 6, 7, 8, 9, then this Step 10 once more.

Apply the code review retry cap from "Loop & retry caps" above. If a second pass through Step 10 still emits `CODE_REVIEW_BLOCKED`, commit pending changes using the `commit` skill (exit path), emit `WORKFLOW_BLOCKED: code review unresolved after 1 fix iteration` and stop.


## Step 10b (optional): Human code review
**Skip by default.** Only pause for human approval if:
- The user explicitly requested a code review approval gate

If enabled:
```bash
cd backlog && backlog task edit <id> -s "Human Code Review" -a @human
```

Commit pending changes using the `commit` skill (exit path — no later closeout commit).

Output: `WORKFLOW_BLOCKED: human code review required for task <id> — <reason>`. Then stop.


## Step 11: Audit Followed All Steps

Use the `audit-followed-workflow-steps` skill.

For any missed steps, go back and complete them. Do not proceed until all steps are verified as completed.


## Step 11b: Self Improvement Recommendation
After auditing, if you identify any meaningful areas for improvement in your workflow execution, output a self-improvement recommendation in the format: `SELF_IMPROVEMENT_RECOMMENDATION: <specific recommendation for improving workflow execution>`. This will help you learn and improve over time.

Meaningful recommendations are specific, actionable, and focused on improving the quality, efficiency, or reliability of your workflow execution and not skipping instructions or steps.

If a meaningful recommendation is identified, write it to the task, commit pending changes using the `commit` skill (exit path), output it after the audit step and stop before the closeout step.

Output: SELF_IMPROVEMENT_REVIEW_REQUIRED: task <id> requires human approval for self-improvement recommendation — <reason>. Then stop.

If no meaningful improvements are identified, do not output anything and proceed to closeout as normal.


## Step 12: Merge Guard (scope check)

Run the merge guard script:

```bash
bash .claude/skills/workflow/scripts/merge-guard.sh <id>
```

The script:
- Refuses to run if the repo is on `main`/`master`/`develop`
- Reads `modified_files` from the task as the authoritative scope
- Treats test files, lockfiles, and e2e `test-results/` as routine artifacts (in scope)

Note: the merge guard inspects the diff between `<base>..HEAD`, so it only sees changes that have already been committed. Because this workflow defers all commits to Step 13, on the happy path the merge guard will report no diff to inspect for the just-implemented changes — that is expected. The guard still catches scope creep from any commits that already existed on the feature branch when the workflow started.

If the script exits non-zero, propagate its `WORKFLOW_BLOCKED:` output (also append it to the task notes) and stop. If it prints `MERGE_GUARD_PASSED`, continue to Step 13.


## Step 13: Closeout (commit, push, mark done)

Only run this step after Step 12 passes.

**Commit all pending changes:**

Use the `commit` skill. This produces one conventional commit containing every change accumulated since Step 2 (code, tests, backlog status updates, plan, notes, AC checks, code review notes).

**Push:**

```bash
bash .claude/skills/workflow/scripts/squash-and-push.sh <id> "feat(<scope>): <task title> (<task id>)"
```

The script squashes commits ahead of base into one if more than one is present (a no-op if the repo received exactly one closeout commit), then pushes with `--force-with-lease` (or sets upstream on first push).

Use a single conventional-commit subject like `feat(<scope>): <task title> (<task id>)`.

If the script exits non-zero, surface its output as `WORKFLOW_BLOCKED: closeout push failed — <details>` and stop.

**Mark the task done:**

```bash
cd backlog && backlog task edit <id> -s Done
```

Use the `commit` skill once more for this final status change, then push:

```bash
git push
```

**Output completion signal:**

Output `TASK_COMPLETE: <id> — <title>`

## Rules

- Process exactly one task per invocation
- Never edit task files directly — always use the `backlog` CLI via manage-backlog-tasks skill
- Single session only: do not run two workflow sessions simultaneously
- If stuck and cannot proceed, output `WORKFLOW_BLOCKED: <reason>` so the loop exits cleanly
- Propagate any `*_BLOCKED` output from sub-skills as `WORKFLOW_BLOCKED: <propagated reason>`
- NEVER SKIP ANY STEPS IN THE OUTLINED PROCESS ABOVE.
