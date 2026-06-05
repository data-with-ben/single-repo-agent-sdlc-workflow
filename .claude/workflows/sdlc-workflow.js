export const meta = {
  name: 'sdlc-workflow',
  description: 'End-to-end SDLC mirror of the workflow skill: claim → intake → worktree → assess → plan + hostile review → implement → verify AC → unit tests → e2e → notes → code review → audit → self-improvement → merge guard → closeout',
  whenToUse: 'When the user asks to coordinate a backlog task end-to-end as a multi-agent workflow. Optional args: { taskId: "task-3", gates: { intake: false, plan: false, codeReview: false } } — or a bare string taskId.',
  phases: [
    { title: 'Intake', detail: 'check-for-work → intake → setup-worktree' },
    { title: 'Assess', detail: 'assess-task (+ optional human intake gate)' },
    { title: 'Plan', detail: 'plan-task → hostile-plan-review (max 2 retries, + optional human plan gate)' },
    { title: 'Implement', detail: 'implement (re-entered on AC/test/review failures)' },
    { title: 'Verify & Test', detail: 'verify-ac → unit-tests → e2e-tests → implementation-notes (max 2 retries each)' },
    { title: 'Code Review', detail: 'code-review (max 1 fix iteration, + optional human gate)' },
    { title: 'Audit', detail: 'audit-followed-workflow-steps → self-improvement → merge-guard' },
    { title: 'Closeout', detail: 'single squashed commit, push, mark Done, tear down worktree' },
  ],
}

// ---------------- config ----------------
const cfg = (args && typeof args === 'object') ? args : {}
const requestedTaskId = cfg.taskId || (typeof args === 'string' && args.trim() ? args.trim() : null)
const gates = cfg.gates || {} // { intake: bool, plan: bool, codeReview: bool } — all default OFF, matching "skip by default"

// ---------------- variable bindings (workflow skill: "Variable bindings") ----------------
const state = { id: null, title: null, branch: null, worktree: null }

// ---------------- schemas ----------------
const STEP_SCHEMA = {
  type: 'object',
  properties: {
    signal: { type: 'string', description: 'The exact terminal signal line the skill emitted, verbatim (e.g. "AC_VERIFIED", "CODE_REVIEW_BLOCKED: <reason>", "E2E_TESTS_SKIPPED")' },
    blocked: { type: 'boolean', description: 'true if the skill emitted a blocking signal (*_BLOCKED, *_FAILED, *_NEEDED, *_REQUIRED). E2E_TESTS_SKIPPED is NOT a blocker.' },
    detail: { type: 'string', description: 'Concise actionable detail: failing AC ids, test failures, review issues, reasons. Empty string if none.' },
  },
  required: ['signal', 'blocked', 'detail'],
}

const CLAIM_SCHEMA = {
  type: 'object',
  properties: {
    claimed: { type: 'boolean', description: 'true if a task was claimed' },
    id: { type: 'string', description: 'Claimed task id, e.g. "task-3". Empty string if none.' },
    title: { type: 'string', description: 'Claimed task title. Empty string if none.' },
    signal: { type: 'string', description: 'Verbatim terminal signal: "<id> — <title>", NO_WORK_AVAILABLE, or CHECK_BLOCKED: <reason>' },
    detail: { type: 'string' },
  },
  required: ['claimed', 'id', 'title', 'signal', 'detail'],
}

const INTAKE_SCHEMA = {
  type: 'object',
  properties: {
    branch: { type: 'string', description: 'Feature branch name captured from INTAKE_COMPLETE: <branch>. Empty if blocked.' },
    signal: { type: 'string' },
    blocked: { type: 'boolean' },
    detail: { type: 'string' },
  },
  required: ['branch', 'signal', 'blocked', 'detail'],
}

const WORKTREE_SCHEMA = {
  type: 'object',
  properties: {
    worktree: { type: 'string', description: 'Absolute worktree path captured from WORKTREE_READY: <worktree>. Empty if blocked.' },
    signal: { type: 'string' },
    blocked: { type: 'boolean' },
    detail: { type: 'string' },
  },
  required: ['worktree', 'signal', 'blocked', 'detail'],
}

// ---------------- helpers ----------------
function skillPrompt(skill, extra) {
  const skillFile = state.worktree
    ? `${state.worktree}/.claude/skills/${skill}/SKILL.md`
    : `.claude/skills/${skill}/SKILL.md`
  return [
    `You are executing exactly ONE step of the autonomous SDLC workflow defined in .claude/skills/workflow/SKILL.md. Your step is the \`${skill}\` skill. Do not perform any other workflow steps.`,
    state.worktree
      ? `WORKING ROOT: ${state.worktree} (git worktree for the feature branch — a complete checkout). cd there FIRST and run ALL commands from inside it. Run backlog CLI commands from ${state.worktree}/backlog. Never operate on the main checkout.`
      : `WORKING ROOT: the main repo checkout (your starting directory).`,
    `Read the skill instructions at ${skillFile} and execute them exactly as written. (If a Skill tool listing "${skill}" is available to you, you may invoke it instead — same effect.)`,
    state.id ? `Task: ${state.id} — ${state.title}` : null,
    state.branch ? `Feature branch: ${state.branch}` : null,
    `AUTONOMY OVERRIDE: run fully autonomously. Never pause to ask the user for confirmation. The manage-backlog-tasks skill's guidance to "share the plan and ask for confirmation" is overridden — ignore it.`,
    `TASK RULE: never edit backlog task files directly — always use the backlog CLI per the manage-backlog-tasks skill.`,
    `COMMIT DISCIPLINE: do NOT create git commits in this step — let changes accumulate in the worktree's working tree. Exception: only if this skill's own instructions explicitly commit (commit / closeout / gate exit paths).`,
    extra,
    `Your final message is consumed by an orchestrator, not a human. Return structured output capturing the skill's terminal signal line VERBATIM in "signal".`,
  ].filter(Boolean).join('\n\n')
}

async function runSkill(skill, phaseTitle, extra, schema) {
  const res = await agent(skillPrompt(skill, extra), {
    label: skill,
    phase: phaseTitle,
    schema: schema || STEP_SCHEMA,
  })
  // agent() returns null if the user skips the step mid-run — treat as a block so caps/propagation handle it
  return res || { signal: `WORKFLOW_BLOCKED: ${skill} step was skipped/cancelled`, blocked: true, detail: `${skill} agent did not complete`, branch: '', worktree: '', claimed: false, id: '', title: '' }
}

async function commitExit(reason, phaseTitle) {
  // Exit path: commit pending work before stopping so it is not lost
  await runSkill('commit', phaseTitle, `EXIT PATH: the workflow is stopping early (${reason}). Commit all pending changes in the worktree now so work is not lost. This is the explicit exception to commit discipline.`)
}

function blocked(reason) {
  log(`WORKFLOW_BLOCKED: ${reason}`)
  return { result: `WORKFLOW_BLOCKED: ${reason}`, task: state }
}

// ============================================================
// Step 1: Check for work
// ============================================================
const claim = await runSkill(
  'check-for-work', 'Intake',
  requestedTaskId
    ? `Claim the task with id "${requestedTaskId}".`
    : `Claim the highest-priority available task.`,
  CLAIM_SCHEMA,
)
if (!claim.claimed) return blocked(claim.signal || claim.detail || 'no work available')
state.id = claim.id
state.title = claim.title
log(`Claimed ${state.id} — ${state.title}`)

// ============================================================
// Step 2: Run intake (creates feature branch)
// ============================================================
const intake = await runSkill('intake', 'Intake', `Capture and return the branch name from the INTAKE_COMPLETE: <branch> signal.`, INTAKE_SCHEMA)
if (intake.blocked || !intake.branch) return blocked(intake.signal || 'intake failed')
state.branch = intake.branch
log(`Branch: ${state.branch}`)

// ============================================================
// Step 2b: Set up worktree
// ============================================================
const wt = await runSkill('setup-worktree', 'Intake', `Capture and return the absolute worktree path from the WORKTREE_READY: <worktree> signal.`, WORKTREE_SCHEMA)
if (wt.blocked || !wt.worktree) return blocked(wt.signal || 'worktree setup failed')
state.worktree = wt.worktree
log(`Worktree: ${state.worktree} — all subsequent steps run from here`)

// ============================================================
// Step 3: Assess task definition
// ============================================================
const assess = await runSkill('assess-task', 'Assess')
if (assess.blocked) {
  await commitExit(`TASK_REFINEMENT_NEEDED — ${assess.detail}`, 'Assess')
  return blocked(assess.signal || assess.detail)
}

// ============================================================
// Step 3b (optional): Human intake approval gate — skip by default
// ============================================================
if (gates.intake) {
  const g = await runSkill('intake-gate', 'Assess', `The user explicitly enabled the intake approval gate. Follow the gate skill: it commits pending changes and emits WORKFLOW_BLOCKED for human review.`)
  return blocked(g.signal || 'intake gate — awaiting human review')
}

// ============================================================
// Step 4 + 4a: Plan the task + AI hostile plan review (max 2 retries)
// ============================================================
let planFeedback = ''
for (let attempt = 0; ; attempt++) {
  await runSkill('plan-task', 'Plan', planFeedback ? `REVISION PASS: a previous plan was rejected by hostile review. Revise the plan to fully address these blocking issues:\n${planFeedback}` : null)
  const hostile = await runSkill('hostile-plan-review', 'Plan')
  if (!hostile.blocked) break
  if (attempt >= 2) return blocked(`plan failed after 2 retries — ${hostile.detail}`)
  planFeedback = hostile.detail || hostile.signal
  log(`Hostile review blocked the plan (retry ${attempt + 1}/2) — revising`)
}

// ============================================================
// Step 4b (optional): Human planning approval gate — skip by default
// ============================================================
if (gates.plan) {
  const g = await runSkill('plan-gate', 'Plan', `The user explicitly enabled the planning approval gate. Follow the gate skill exactly: present the plan; if changes are requested, rerun plan-task once and ask again. Emit PLAN_GATE_APPROVED or WORKFLOW_BLOCKED.`)
  if (g.blocked) return blocked(g.signal || 'plan not approved')
}

// ============================================================
// Steps 5–10: Implement → Verify AC → Unit tests → E2E → Notes → Code review
// Retry caps: AC 2, unit 2, e2e 2 (each returns to Step 5); code review 1 fix iteration
// ============================================================
let acRetries = 0
let unitRetries = 0
let e2eRetries = 0
let reviewFixes = 0
let implementFeedback = ''

while (true) {
  // Step 5: Implement
  await runSkill('implement', 'Implement', implementFeedback ? `RETURN-TO-IMPLEMENT PASS: address ONLY the following issues from a downstream step — do not expand scope:\n${implementFeedback}` : null)
  implementFeedback = ''

  // Step 6: Verify AC
  const ac = await runSkill('verify-ac', 'Verify & Test')
  if (ac.blocked) {
    if (acRetries >= 2) {
      await commitExit('AC retry cap reached', 'Verify & Test')
      return blocked(`AC not met after 2 retries — ${ac.detail}`)
    }
    acRetries++
    implementFeedback = `AC verification failed (AC_VERIFICATION_FAILED). Failure details: ${ac.detail}`
    log(`AC verification failed — returning to implement (AC retry ${acRetries}/2)`)
    continue
  }

  // Step 7: Create/update unit tests and run all unit tests
  const unit = await runSkill('unit-tests', 'Verify & Test')
  if (unit.blocked) {
    if (unitRetries >= 2) {
      await commitExit('unit test retry cap reached', 'Verify & Test')
      return blocked('unit tests failing after 2 retries')
    }
    unitRetries++
    implementFeedback = `Unit tests blocked (UNIT_TESTS_BLOCKED). Failure details: ${unit.detail}`
    log(`Unit tests failed — returning to implement (unit retry ${unitRetries}/2)`)
    continue
  }

  // Step 8: Run e2e tests (E2E_TESTS_SKIPPED is not a blocker)
  const e2e = await runSkill('e2e-tests', 'Verify & Test', `Note: E2E_TESTS_SKIPPED is NOT a blocker — report blocked=false for it. Only E2E_TESTS_BLOCKED is blocking.`)
  if (e2e.blocked) {
    if (e2eRetries >= 2) {
      await commitExit('e2e retry cap reached', 'Verify & Test')
      return blocked('e2e tests failing after 2 retries')
    }
    e2eRetries++
    implementFeedback = `E2E tests blocked (E2E_TESTS_BLOCKED). Failure details: ${e2e.detail}`
    log(`E2E tests failed — returning to implement (e2e retry ${e2eRetries}/2)`)
    continue
  }

  // Step 9: Write implementation notes to the task
  await runSkill('implementation-notes', 'Verify & Test')

  // Step 10: AI code review
  const review = await runSkill('code-review', 'Code Review')
  if (review.blocked) {
    if (reviewFixes >= 1) {
      await commitExit('code review unresolved after 1 fix iteration', 'Code Review')
      return blocked('code review unresolved after 1 fix iteration')
    }
    reviewFixes++
    implementFeedback = `Code review found critical/major issues (CODE_REVIEW_BLOCKED). Address ONLY these issues:\n${review.detail}`
    log(`Code review blocked — returning to implement, then re-running steps 6–10 (fix iteration ${reviewFixes}/1)`)
    continue
  }

  break
}

// ============================================================
// Step 10b (optional): Human code review gate — skip by default
// ============================================================
if (gates.codeReview) {
  const g = await runSkill('code-review-gate', 'Code Review', `The user explicitly enabled the human code review gate. Follow the gate skill: it commits pending changes and emits WORKFLOW_BLOCKED for human review.`)
  return blocked(g.signal || 'code review gate — awaiting human review')
}

// ============================================================
// Step 11: Audit followed all workflow steps
// ============================================================
for (let auditRound = 0; ; auditRound++) {
  const audit = await runSkill('audit-followed-workflow-steps', 'Audit')
  if (!audit.blocked) break
  if (auditRound >= 2) {
    await commitExit('audit unresolved', 'Audit')
    return blocked(`audit failed after remediation attempts — ${audit.detail}`)
  }
  log(`Audit found missing steps — remediating: ${audit.detail}`)
  await runSkill('audit-followed-workflow-steps', 'Audit', `REMEDIATION PASS: the audit found these workflow steps incomplete:\n${audit.detail}\n\nGo back and complete each missing step by reading and executing its SKILL.md under ${state.worktree}/.claude/skills/. Then report what you completed. Do NOT re-run the audit itself in this pass.`)
}

// ============================================================
// Step 11b: Self-improvement recommendation
// ============================================================
const selfImp = await runSkill('self-improvement', 'Audit')
if (selfImp.blocked) {
  // SELF_IMPROVEMENT_REVIEW_REQUIRED — a human must approve before closeout
  return blocked(`${selfImp.signal} — human approval required before closeout. ${selfImp.detail}`)
}

// ============================================================
// Step 12: Merge guard (scope check before marking Done)
// ============================================================
const guard = await runSkill('merge-guard', 'Audit')
if (guard.blocked) return blocked(guard.signal || `merge guard — ${guard.detail}`)

// ============================================================
// Step 13: Closeout (single conventional commit, squash, push, mark Done, tear down worktree)
// ============================================================
const close = await runSkill('closeout', 'Closeout', `This is the ONLY step that creates a commit: produce a single conventional commit on ${state.branch}, squash, push, mark ${state.id} Done, and tear down the worktree per the skill.`)
if (close.blocked) return blocked(close.signal || `closeout — ${close.detail}`)

log(`TASK_COMPLETE: ${state.id} — ${state.title}`)
return {
  result: `TASK_COMPLETE: ${state.id} — ${state.title}`,
  task: state.id,
  title: state.title,
  branch: state.branch,
  worktree: state.worktree,
}
