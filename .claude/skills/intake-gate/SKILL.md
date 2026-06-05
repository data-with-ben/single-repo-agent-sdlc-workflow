---
name: intake-gate
description: Optional human intake approval gate — pause the workflow for human review of the task definition before planning begins
---

You are the intake gate agent. This skill is only invoked when the user has explicitly requested a human intake approval gate. Do not call this skill unless that gate has been enabled.

## Process

1. Update the task status to signal it is awaiting human review:

```bash
cd backlog && backlog task edit <id> -s "Intake Review" -a @human
```

2. Use the `commit` skill to commit all pending changes. This is an exit path — there will be no closeout commit.

3. Emit `WORKFLOW_BLOCKED: intake review required for task <id> — task definition must be approved before planning begins` and stop.

The human reviews the task definition offline. If changes are needed, they update the task directly. When ready, they re-invoke the workflow to resume from Step 4 (Plan the task).

## Rules

- Always commit before stopping — pending changes must not be lost
- This skill always emits `WORKFLOW_BLOCKED` — it never continues the workflow
