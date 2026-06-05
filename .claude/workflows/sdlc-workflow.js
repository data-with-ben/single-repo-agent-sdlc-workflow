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
// taskContent: verbatim output of `backlog task <id> --plain` captured at assess-task; passed forward so
//   later agents skip the CLI re-read for the static parts (ACs, description).
// planSummary: the implementation plan written by plan-task; passed to hostile-review and implement.
// implContext: {filesChanged, approachSummary} from implement; passed to verify/test/notes/review so
//   those agents can target specific files rather than scanning the full diff.
const state = { id: null, title: null, branch: null, worktree: null, taskContent: null, planSummary: null, implContext: null }

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

// Batched verify/test/notes — runs verify-ac → unit-tests → e2e-tests → implementation-notes in one agent turn
const VERIFY_BATCH_SCHEMA = {
  type: 'object',
  properties: {
    blocked: { type: 'boolean', description: 'true if any of verify-ac, unit-tests, or e2e-tests blocked (E2E_TESTS_SKIPPED is NOT a blocker)' },
    firstBlockedStep: { type: 'string', description: 'Name of the first blocking skill ("verify-ac", "unit-tests", "e2e-tests"), or empty string if none blocked' },
    detail: { type: 'string', description: 'Detail from the first blocking step. Empty string if none blocked.' },
    signals: {
      type: 'object',
      description: 'Verbatim terminal signal from each skill that was executed',
      properties: {
        'verify-ac': { type: 'string' },
        'unit-tests': { type: 'string' },
        'e2e-tests': { type: 'string' },
        'implementation-notes': { type: 'string' },
      },
      required: ['verify-ac'],
    },
  },
  required: ['blocked', 'firstBlockedStep', 'detail', 'signals'],
}

// Batched self-improvement + merge-guard — runs both in one agent turn after audit passes
const AUDIT_TAIL_SCHEMA = {
  type: 'object',
  properties: {
    selfImpBlocked: { type: 'boolean' },
    selfImpSignal: { type: 'string' },
    selfImpDetail: { type: 'string' },
    mergeGuardBlocked: { type: 'boolean', description: 'false if self-improvement blocked (merge-guard was skipped)' },
    mergeGuardSignal: { type: 'string' },
    mergeGuardDetail: { type: 'string' },
  },
  required: ['selfImpBlocked', 'selfImpSignal', 'selfImpDetail', 'mergeGuardBlocked', 'mergeGuardSignal', 'mergeGuardDetail'],
}

// Extended schemas that carry context forward to avoid downstream re-reads
const ASSESS_SCHEMA = {
  type: 'object',
  properties: {
    signal: { type: 'string' },
    blocked: { type: 'boolean' },
    detail: { type: 'string' },
    taskContent: { type: 'string', description: 'Verbatim output of `backlog task <id> --plain` so downstream agents can skip re-reading it' },
  },
  required: ['signal', 'blocked', 'detail', 'taskContent'],
}

const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    signal: { type: 'string' },
    blocked: { type: 'boolean' },
    detail: { type: 'string' },
    planSummary: { type: 'string', description: 'The complete implementation plan as written to the task notes (verbatim or full reproduction)' },
  },
  required: ['signal', 'blocked', 'detail', 'planSummary'],
}

const IMPLEMENT_SCHEMA = {
  type: 'object',
  properties: {
    signal: { type: 'string' },
    blocked: { type: 'boolean' },
    detail: { type: 'string' },
    filesChanged: { type: 'array', items: { type: 'string' }, description: 'Relative paths (from repo root) of every file created or modified' },
    approachSummary: { type: 'string', description: '3–6 sentence summary of what was implemented, key technical decisions, and any deviations from the plan' },
  },
  required: ['signal', 'blocked', 'detail', 'filesChanged', 'approachSummary'],
}

// ---------------- helpers ----------------

// Builds a pre-loaded context block so downstream agents can skip redundant CLI reads.
// task notes grow over time (plan, review findings, etc. are appended), so taskContent
// covers only the static parts (ACs, description). planSummary and implContext are
// captured explicitly from the steps that produce them and are always current.
function contextCapsule() {
  const parts = []
  if (state.taskContent) {
    parts.push(
      `Task content — use this instead of running \`backlog task ${state.id} --plain\` for the static fields (title, description, acceptance criteria). Re-run the CLI only if you need notes appended after this point (e.g., hostile review findings, implementation notes).\n\`\`\`\n${state.taskContent}\n\`\`\``
    )
  }
  if (state.planSummary) {
    parts.push(`Implementation plan (written by plan-task — use this instead of re-reading the task notes for the plan):\n\`\`\`\n${state.planSummary}\n\`\`\``)
  }
  if (state.implContext) {
    parts.push(
      `Implementation context (captured from implement — use this instead of running git diff/status for an overview):\n` +
      `Files changed: ${state.implContext.filesChanged.join(', ')}\n` +
      `Approach: ${state.implContext.approachSummary}`
    )
  }
  if (!parts.length) return null
  return `CONTEXT CAPSULE — pre-loaded to avoid redundant reads:\n\n${parts.join('\n\n')}`
}

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
    contextCapsule(),
    `AUTONOMY OVERRIDE: run fully autonomously. Never pause to ask the user for confirmation. The manage-backlog-tasks skill's guidance to "share the plan and ask for confirmation" is overridden — ignore it.`,
    `TASK RULE: never edit backlog task files directly — always use the backlog CLI per the manage-backlog-tasks skill.`,
    `COMMIT DISCIPLINE: do NOT create git commits in this step — let changes accumulate in the worktree's working tree. Exception: only if this skill's own instructions explicitly commit (commit / closeout / gate exit paths).`,
    extra,
    `Your final message is consumed by an orchestrator, not a human. Return structured output capturing the skill's terminal signal line VERBATIM in "signal".`,
  ].filter(Boolean).join('\n\n')
}

function batchPrompt(skills, extra) {
  const root = state.worktree || '.'
  const skillList = skills.map((s, i) =>
    `${i + 1}. **${s}** — read and execute ${root}/.claude/skills/${s}/SKILL.md`
  ).join('\n')
  return [
    `You are executing ${skills.length} sequential SDLC workflow skills in a single agent turn to avoid redundant context loading. Run each skill in the order listed below, stopping at the first blocking signal (a *_BLOCKED, *_FAILED, *_NEEDED, or *_REQUIRED terminal). Skip all remaining skills after a block. Exception: E2E_TESTS_SKIPPED is NOT a blocker — continue to the next skill.`,
    state.worktree
      ? `WORKING ROOT: ${state.worktree} (git worktree). cd there FIRST and run ALL commands from inside it. Run backlog CLI from ${state.worktree}/backlog.`
      : `WORKING ROOT: main repo checkout.`,
    state.id ? `Task: ${state.id} — ${state.title}` : null,
    state.branch ? `Feature branch: ${state.branch}` : null,
    contextCapsule(),
    `Skills to run in order:\n${skillList}`,
    `AUTONOMY OVERRIDE: run fully autonomously. Never pause for confirmation.`,
    `TASK RULE: never edit backlog task files directly — always use the backlog CLI.`,
    `COMMIT DISCIPLINE: do NOT create git commits.`,
    extra,
    `Your final message is consumed by an orchestrator. Return structured output capturing each executed skill's terminal signal verbatim.`,
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
const assess = await runSkill('assess-task', 'Assess', `Return the full verbatim output of \`backlog task ${state.id} --plain\` in the taskContent field.`, ASSESS_SCHEMA)
if (assess.blocked) {
  await commitExit(`TASK_REFINEMENT_NEEDED — ${assess.detail}`, 'Assess')
  return blocked(assess.signal || assess.detail)
}
if (assess.taskContent) state.taskContent = assess.taskContent

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
  const pt = await runSkill(
    'plan-task', 'Plan',
    [
      planFeedback ? `REVISION PASS: a previous plan was rejected by hostile review. Revise the plan to fully address these blocking issues:\n${planFeedback}` : null,
      `Return the complete plan text in the planSummary field so the hostile reviewer and implementer can use it without re-reading the task.`,
    ].filter(Boolean).join('\n\n'),
    PLAN_SCHEMA,
  )
  if (pt && pt.planSummary) state.planSummary = pt.planSummary
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
  const impl = await runSkill(
    'implement', 'Implement',
    [
      implementFeedback ? `RETURN-TO-IMPLEMENT PASS: address ONLY the following issues from a downstream step — do not expand scope:\n${implementFeedback}` : null,
      `Return all modified/created file paths in filesChanged and a brief approach summary in approachSummary so downstream agents can target those files without re-scanning the full diff.`,
    ].filter(Boolean).join('\n\n'),
    IMPLEMENT_SCHEMA,
  )
  implementFeedback = ''
  if (impl && impl.filesChanged) state.implContext = { filesChanged: impl.filesChanged, approachSummary: impl.approachSummary || '' }

  // Steps 6–9: verify-ac → unit-tests → e2e-tests → implementation-notes (batched — one agent, one context load)
  const vb = await agent(
    batchPrompt(
      ['verify-ac', 'unit-tests', 'e2e-tests', 'implementation-notes'],
      'Run skills 1–3 in strict order, stopping at the first blocker. Only run implementation-notes (skill 4) if skills 1–3 all pass. E2E_TESTS_SKIPPED is NOT a blocker — continue to implementation-notes when you see it.',
    ),
    { label: 'verify+test+notes', phase: 'Verify & Test', schema: VERIFY_BATCH_SCHEMA },
  ) || { blocked: true, firstBlockedStep: 'verify-ac', detail: 'agent skipped/cancelled', signals: { 'verify-ac': '' } }

  if (vb.blocked) {
    const step = vb.firstBlockedStep
    const detail = vb.detail || ''
    if (step === 'verify-ac') {
      if (acRetries >= 2) {
        await commitExit('AC retry cap reached', 'Verify & Test')
        return blocked(`AC not met after 2 retries — ${detail}`)
      }
      acRetries++
      implementFeedback = `AC verification failed (AC_VERIFICATION_FAILED). Failure details: ${detail}`
      log(`AC verification failed — returning to implement (AC retry ${acRetries}/2)`)
    } else if (step === 'unit-tests') {
      if (unitRetries >= 2) {
        await commitExit('unit test retry cap reached', 'Verify & Test')
        return blocked(`unit tests failing after 2 retries — ${detail}`)
      }
      unitRetries++
      implementFeedback = `Unit tests blocked (UNIT_TESTS_BLOCKED). Failure details: ${detail}`
      log(`Unit tests failed — returning to implement (unit retry ${unitRetries}/2)`)
    } else {
      if (e2eRetries >= 2) {
        await commitExit('e2e retry cap reached', 'Verify & Test')
        return blocked(`e2e tests failing after 2 retries — ${detail}`)
      }
      e2eRetries++
      implementFeedback = `E2E tests blocked (E2E_TESTS_BLOCKED). Failure details: ${detail}`
      log(`E2E tests failed — returning to implement (e2e retry ${e2eRetries}/2)`)
    }
    continue
  }

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
// Steps 11b + 12: self-improvement + merge-guard (batched — one agent, one context load)
// ============================================================
const auditTail = await agent(
  batchPrompt(
    ['self-improvement', 'merge-guard'],
    'Run self-improvement first. If it emits SELF_IMPROVEMENT_REVIEW_REQUIRED (blocked), skip merge-guard and report mergeGuardBlocked=false with an empty signal. Otherwise run merge-guard.',
  ),
  { label: 'self-improvement+merge-guard', phase: 'Audit', schema: AUDIT_TAIL_SCHEMA },
) || { selfImpBlocked: true, selfImpSignal: 'WORKFLOW_BLOCKED: agent skipped', selfImpDetail: 'agent skipped/cancelled', mergeGuardBlocked: false, mergeGuardSignal: '', mergeGuardDetail: '' }

if (auditTail.selfImpBlocked) {
  // SELF_IMPROVEMENT_REVIEW_REQUIRED — human must approve before closeout
  return blocked(`${auditTail.selfImpSignal} — human approval required before closeout. ${auditTail.selfImpDetail}`)
}
if (auditTail.mergeGuardBlocked) return blocked(auditTail.mergeGuardSignal || `merge guard — ${auditTail.mergeGuardDetail}`)

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
