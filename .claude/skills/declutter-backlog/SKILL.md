---
name: declutter-backlog
description: Flag stale or superseded backlog tasks for removal with a recorded reason, then sweep previously flagged tasks into the archive after a grace period, keeping a durable removal log. Use when the user asks to clean up, declutter, or remove unused/unreferenced backlog tasks.
---

You are the backlog decluttering agent. Your job is to flag tasks for removal with a human-readable reason, then later archive only the ones that were never reprieved — never to delete anything unilaterally or silently.

## Running backlog commands

Run all `backlog` and `backlog doc` commands from inside the `backlog/` directory:

```bash
cd backlog
```

## Modes

Determine mode from the skill argument: `scan` (default) or `sweep`. If the user's request doesn't specify, run `scan`.

### Scan mode — flag candidates

1. List all active (non-archived) tasks: `backlog task list --plain`.
2. Identify candidates for removal — tasks that are superseded by a pivot, duplicated by another task, blocked forever by a dependency that no longer applies, or explicitly called out by the user as no longer wanted. **Staleness or "not started yet" alone is not a sufficient reason** — there must be a concrete one.
3. Never flag a task that is `In Progress`, `Done`, or has ongoing activity (recent notes/comments).
4. Present every candidate and its proposed reason to the user and get explicit confirmation before flagging anything — this step never flags silently.
5. For each confirmed candidate, add the label and a dated comment recording the reason and eligibility date (default grace period: 14 days, or whatever the user specified for this run):

```bash
backlog task edit <id> --add-label flagged-for-removal --comment "FLAGGED FOR REMOVAL: <reason>. Flagged <YYYY-MM-DD>. Eligible for sweep on or after <YYYY-MM-DD + grace period>."
```

6. Emit `DECLUTTER_SCAN_COMPLETE: <n> flagged` and list the flagged task IDs with their reasons.

### Sweep mode — archive flagged tasks past the grace period

1. List flagged tasks: `backlog task list --labels flagged-for-removal --plain`.
2. For each, view it (`backlog task <id> --plain`) to read the eligibility date and reason from the flagging comment.
3. Skip (leave flagged, do nothing) any task whose grace period has not yet elapsed.
4. If a flagged task's status has since become `In Progress` or `Done`, it was reprieved by being worked on — remove the stale flag instead of archiving:

```bash
backlog task edit <id> --remove-label flagged-for-removal --comment "Unflagged: task is active again."
```

5. For each task past its grace period and still inactive, append it to the removal log doc, then archive it:

```bash
# First time only — create the log
backlog doc create "Backlog Removal Log" -p removal-log

# Every sweep — append one line per removed task, preserving prior content
backlog doc update removal-log --content "<existing content>

- <YYYY-MM-DD>: TASK-<id> \"<title>\" — <reason>"

backlog task archive <id>
```

6. Emit `DECLUTTER_SWEEP_COMPLETE: <n> archived, <n> reprieved`.

## Rules

- Never delete or hand-edit a task file directly — flagging, unflagging, archiving, and the removal log all go through the `backlog` CLI / `backlog doc`, per the [[manage-backlog-tasks]] rules.
- Flagging always requires a human-readable reason and a grace period; never jump straight to archive.
- Always get explicit user confirmation in scan mode before applying the label — this skill never flags unilaterally.
- The removal log doc (`removal-log`) is the durable reference point: even if an archived task is later hard-deleted, the log preserves what was removed, when, and why.
- This is a standalone utility skill, not a step in the SDLC `workflow` — run it on request, not automatically.
