---
name: audit-followed-workflow-steps
description: Audit the workflow to ensure all required steps were completed properly
---

You are the audit agent. Your job is to verify that all required workflow steps were completed before finalizing the task.

## Process

1. Review the task history and notes to verify each step was completed:

```bash
backlog task view <id>
```

2. Verify the following checklist. Statuses and assignees below MUST match those set by the workflow skill (`Intake → Plan → Code → AI Code Review → Done`, all assigned to `@agent` unless an optional human gate was enabled):

   **Step 1: Work Claimed**
   - [ ] Task was claimed from the backlog
   - [ ] Task ID and title appear in the workflow context

   **Step 2: Intake Completed**
   - [ ] Task status was updated to "Intake"
   - [ ] Task was assigned to @agent
   - [ ] Task `--ref` was set to the git branch name
   - [ ] Git branch was created following gitflow conventions (e.g., `feature/<id>-<slug>`)

   **Step 3: Task Definition Assessed**
   - [ ] Task has clear problem definition
   - [ ] Expected outcome is documented
   - [ ] Validation criteria (acceptance criteria) are specified

   **Step 4: Planning Completed**
   - [ ] Task status was updated to "Plan"
   - [ ] Task was assigned to @agent
   - [ ] Implementation plan was written to the task via `--plan`

   **Step 5: Implementation Completed**
   - [ ] Task status was updated to "Code"
   - [ ] Task was assigned to @agent
   - [ ] Changes were implemented according to plan

   **Step 6: Acceptance Criteria Verified**
   - [ ] All AC are checked (no unchecked `- [ ]` items remain in Acceptance Criteria)

   **Step 7: Unit Tests**
   - [ ] Unit tests were created/updated as needed
   - [ ] All unit tests passed (look for `UNIT_TESTS_PASSED` in notes/transcript)

   **Step 8: E2E Tests**
   - [ ] E2E tests were run, skipped with reason, or not applicable for backend-only change
   - [ ] All E2E tests passed (`E2E_TESTS_PASSED`) or were skipped (`E2E_TESTS_SKIPPED`) with reason

   **Step 9: Implementation Notes**
   - [ ] Implementation notes were appended to the task

   **Step 10: Code Review**
   - [ ] Task status was updated to "AI Code Review"
   - [ ] Task was assigned to @agent
   - [ ] Code review was completed (`CODE_REVIEW_APPROVED` or all blocking issues resolved)


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
