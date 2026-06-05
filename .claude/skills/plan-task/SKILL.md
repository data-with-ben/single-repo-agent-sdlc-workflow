---
name: plan-task
description: Write a thorough, high-level implementation plan for the current backlog task before any code is written
---

You are the planning agent. Your job is to design the approach for implementing a task before any code is written.

## Process

1. Update the task status:

```bash
cd backlog && backlog task edit <id> -s "Plan" -a @agent
```

2. Read the task in full to understand the problem, AC, and any references:

```bash
cd backlog && backlog task <id> --plain
```

3. Explore the relevant codebase areas. Read the files that will be touched, understand existing patterns and conventions, and identify what already exists that can be reused. Do not write the plan from memory alone.

4. Write the implementation plan. It should be:
   - **Complete** — every AC is addressed with a clear approach
   - **High level** — describes what to build and why each choice, not the exact code
   - **Ordered** — steps that have dependencies come after the things they depend on
   - **Verifiable** — explains how each AC will be confirmed once implemented

   No code. The plan is structured prose or a numbered list, not pseudocode.

5. Write the plan to the task:

```bash
cd backlog && backlog task edit <id> --plan "<plan text>"
```

6. Emit completion:
   - Emit `PLAN_COMPLETE: plan written to task <id>` and continue to the next step in the workflow — do not stop.

## Rules

- Always read the relevant source files before writing the plan
- Every AC must be traceable to at least one step in the plan
- If planning reveals the task scope is larger than the ACs suggest, note this explicitly in the plan — do not silently expand scope
- The plan will be used for AC verification later; make it specific enough to verify against
