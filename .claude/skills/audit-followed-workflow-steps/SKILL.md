---
name: audit-followed-workflow-steps
description: Audit the workflow to ensure all required steps were completed properly
---

You are the audit agent. Your job is to verify that all required workflow steps were completed before finalizing the task.

## Process

1. Review the task history and notes to verify each step was completed:

```bash
cd backlog && backlog task <id> --plain
```

2. Verify the following checklist. Expected status progression: `Intake → Plan → Code → AI Code Review → Done`, all assigned to `@agent` unless an optional human gate was enabled.

   **Step 1: Work Claimed**
   - [ ] Task was claimed from the backlog
   - [ ] Task ID and title appear in the workflow context

   **Step 2: Intake** (`intake` skill)
   - [ ] Task status was updated to "Intake" and assigned to @agent
   - [ ] Task `--ref` was set to the git branch name
   - [ ] Git branch was created following gitflow conventions (e.g., `feature/<id>-<slug>`)
   - [ ] `INTAKE_COMPLETE` was emitted

   **Step 2b: Worktree Setup** (`setup-worktree` skill)
   - [ ] Worktree was created at `.claude/worktrees/<branch>` (look for `WORKTREE_READY` in transcript)
   - [ ] All subsequent steps ran from the worktree root

   **Step 3: Task Assessment** (`assess-task` skill)
   - [ ] Task has clear problem definition, expected outcome, and testable AC
   - [ ] `TASK_ASSESSMENT_PASSED` was emitted (or workflow was blocked for refinement)

   **Step 4: Planning** (`plan-task` skill)
   - [ ] Task status was updated to "Plan" and assigned to @agent
   - [ ] Implementation plan was written to the task via `--plan`
   - [ ] `PLAN_COMPLETE` was emitted

   **Step 4a: AI Hostile Plan Review** (`hostile-plan-review` skill)
   - [ ] Hostile plan review was run (look for `HOSTILE PLAN REVIEW` in task notes)
   - [ ] `HOSTILE_REVIEW_PASSED` was emitted (or blocking issues were resolved and plan revised)

   **Step 5: Implementation** (`implement` skill)
   - [ ] Task status was updated to "Code" and assigned to @agent
   - [ ] Changes were implemented according to the plan
   - [ ] `IMPLEMENTATION_COMPLETE` was emitted

   **Step 6: AC Verification** (`verify-ac` skill)
   - [ ] All ACs are checked (no unchecked `- [ ]` items remain)
   - [ ] `AC_VERIFIED` was emitted

   **Step 7: Unit Tests** (`unit-tests` skill)
   - [ ] Unit tests were created/updated as needed
   - [ ] `UNIT_TESTS_PASSED` was emitted

   **Step 8: E2E Tests** (`e2e-tests` skill)
   - [ ] `E2E_TESTS_PASSED` or `E2E_TESTS_SKIPPED` (with documented reason) was emitted

   **Step 9: Implementation Notes** (`implementation-notes` skill)
   - [ ] Implementation notes were appended to the task
   - [ ] `IMPLEMENTATION_NOTES_COMPLETE` was emitted

   **Step 10: Code Review** (`code-review` skill)
   - [ ] Task status was updated to "AI Code Review" and assigned to @agent
   - [ ] `CODE_REVIEW_APPROVED` was emitted (or all blocking issues resolved and re-reviewed)


3. For each incomplete step:
   - Document which step was missed
   - Document what needs to be done

4. Emit results:
   - If all steps completed: Emit `AUDIT_PASSED: all workflow steps completed` and continue on to the next step in the workflow - do not stop.
   - If steps are missing: Emit `AUDIT_FAILED: missing steps — <list of missing steps>` and return the list

## Rules

- All steps must be verified as complete
- Check the task history and notes for evidence of each step
- If a step was intentionally skipped, there should be a documented reason
- Do not pass the audit if any critical steps are missing
- If the audit fails, provide clear guidance on what needs to be completed
