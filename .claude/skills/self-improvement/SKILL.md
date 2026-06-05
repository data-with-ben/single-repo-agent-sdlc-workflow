---
name: self-improvement
description: Reflect on the current workflow execution and emit a self-improvement recommendation if a meaningful one is identified
---

You are the self-improvement agent. Your job is to identify process improvements based on what happened during this task's execution. Run after the audit step, before closeout.

## What counts as meaningful

A meaningful recommendation is:
- **Specific** — "the hostile-plan-review skill should also check for missing rollback steps" not "be more thorough"
- **Actionable** — something that could be added or changed in a skill or workflow step
- **Recurring** — a pattern that would help future tasks, not a quirk unique to this one
- **Process-level** — about how the workflow runs, not about the code that was written

Do not manufacture recommendations. If the workflow ran smoothly and nothing stands out, say so and move on.

## Process

1. Read the completed task to review what happened during execution:

```bash
cd backlog && backlog task <id> --plain
```

2. Reflect on the execution by reviewing the task notes and status history:
   - Were there unexpected retries or loops?
   - Did any step produce output that a later step had to work around?
   - Was any skill missing context it needed that another skill already had?
   - Did the ordering of steps cause unnecessary rework?
   - Did any skill's instructions turn out to be ambiguous or incomplete?

3. If a meaningful recommendation is identified:
   - Write it to the task:
   ```bash
   cd backlog && backlog task edit <id> --append-notes "SELF-IMPROVEMENT: <specific recommendation>"
   ```
   - Use the `commit` skill to commit all pending changes (exit path — no later closeout commit will run).
   - Emit `SELF_IMPROVEMENT_REVIEW_REQUIRED: task <id> — <recommendation summary>` and stop. A human must approve the recommendation before the workflow continues to closeout.

4. If no meaningful recommendation:
   - Emit nothing and continue to the next step in the workflow — do not stop.

## Rules

- Do not emit a recommendation just to have one — silence is the correct output when the workflow ran well
- Do not recommend changes that are already in the workflow or skills
- The recommendation must target the process, not the implementation quality
