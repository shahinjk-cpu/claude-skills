export const meta = {
  name: 'swarm-build',
  description: 'Agent swarm: plan a goal into a task graph, build each task, adversarially verify, fix, critique for gaps, integrate (cost-aware)',
  whenToUse: 'Multi-part feature or game-system work that should be built in parallel and verified',
  phases: [
    { title: 'Plan', detail: 'decompose the goal into a task graph (skipped when tasks are given), then lint it in plain code' },
    { title: 'Build', detail: 'one builder per task, dependency-ordered, worktrees for overlapping files' },
    { title: 'Verify', detail: 'adversarial verifiers per task, fix loop' },
    { title: 'Critic', detail: 'what is missing versus the goal; adds a follow-up wave' },
    { title: 'Integrate', detail: 'merge worktree branches and run the final check' },
  ],
}

// ---------- args ----------
const A = args || {}
const GOAL = A.goal || ''
const CWD = A.cwd || ''
const VERIFY_CMD = A.verify_cmd || ''
const ISOLATION = A.isolation || 'auto'          // auto | shared | worktree
const MAX_FIX = A.max_fix_rounds ?? 2
const VOTES = Math.max(1, Math.min(5, A.verifiers ?? 1))
const MAX_WAVES = A.max_waves ?? 2
const RULES = A.rules || ''                       // extra project rules / specialist notes for every brief
// ---------- pack roles ----------
// args.roles = { "<role>": { agentType?, model?: 'cheap'|'standard'|'strong', rules?, verifier?: '<role>' } }
// A task's pack_role picks one; its verifier role (or the base verifier) checks it.
const ROLES = A.roles || {}
const BASE_TYPES = {
  builder: 'agent-swarm:swarm-builder', scout: 'agent-swarm:swarm-scout', verifier: 'agent-swarm:swarm-verifier',
  researcher: 'agent-swarm:swarm-researcher', writer: 'agent-swarm:swarm-writer', operator: 'agent-swarm:swarm-operator',
}
const roleOf = name => (name && ROLES[name]) || null
const typeOf = (r, fallback) => (r && r.agentType && (BASE_TYPES[r.agentType] || r.agentType)) || fallback
const rulesOf = (r, name) => (r && r.rules ? `Role: ${name}. Rules for this role:\n${r.rules}\n\n` : '')
const ROLE_LIST = Object.keys(ROLES).length
  ? `Team roles (set pack_role on each task to the best fit): ${Object.entries(ROLES).map(([n, r]) => `${n} (${typeOf(r, 'builder').replace('agent-swarm:swarm-', '')})`).join(', ')}.`
  : ''
if (!GOAL && !(A.tasks && A.tasks.length)) throw new Error('swarm-build needs args.goal or args.tasks')

// ---------- cost profile ----------
// lean (default): cheap=haiku, standard=sonnet, strong=session model. balanced: only cheap is downgraded. max: everything inherits.
const COST = ['lean', 'balanced', 'max'].includes(A.cost) ? A.cost : 'lean'
const PROFILES = {
  lean: { cheap: 'haiku', standard: 'sonnet', strong: undefined },
  balanced: { cheap: 'haiku', standard: undefined, strong: undefined },
  max: { cheap: undefined, standard: undefined, strong: undefined },
}
const MODELS = { ...PROFILES[COST], ...(A.models || {}) }
const MAX_AGENTS = A.max_agents ?? { lean: 60, balanced: 200, max: 1000 }[COST]
const MAX_TASKS = A.max_tasks ?? { lean: 8, balanced: 12, max: 20 }[COST]
const RESERVE = A.budget_reserve ?? 20000
const CRITIC = A.critic ?? (COST !== 'lean')
const VERIFY_LIGHT = A.verify_light ?? (COST !== 'lean')   // lean: light tasks rely on the builder's own check + the final integrate check
const LEARN = A.learnings ? `Lessons from earlier runs in this project (apply them):\n${A.learnings}\n` : ''
const TERSE = 'Be terse: return results, not narration.'

const WHERE = CWD ? `Project directory: ${CWD} (cd there first; all paths are relative to it).\n` : ''
const GUARD = 'Never deploy, publish, post, send, buy, create accounts, enter credentials, download packs/software, push, open PRs, force-push or permanently delete data. If the task needs any of that, stop and report blocked.'
const TIER_EFFORT = { light: 'low', medium: undefined, heavy: 'high' }
const OK = s => s === 'verified' || s === 'self-checked'

// ---------- schemas ----------
const TASK_ITEM = {
  type: 'object',
  properties: {
    id: { type: 'string' }, title: { type: 'string' }, brief: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    deps: { type: 'array', items: { type: 'string' } },
    tier: { type: 'string', enum: ['light', 'medium', 'heavy'] },
    verify: { type: 'string' },
    pack_role: { type: 'string', description: 'team role name from the pack, if roles were given' },
  },
  required: ['id', 'title', 'brief', 'files', 'deps', 'tier', 'verify'],
}
const TASKS_SCHEMA = { type: 'object', properties: { tasks: { type: 'array', items: TASK_ITEM } }, required: ['tasks'] }
const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['done', 'partial', 'blocked'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    verification: { type: 'string', description: 'the check you ran and its outcome, one or two lines' },
    worktree_path: { type: 'string' },
    branch: { type: 'string' },
    notes: { type: 'string' },
    learned: { type: 'array', items: { type: 'string' }, description: 'non-obvious gotchas or deviations from the brief worth remembering for this project; empty if none' },
  },
  required: ['status', 'files_changed', 'verification'],
}
const VERDICT_SCHEMA = {
  type: 'object',
  properties: { pass: { type: 'boolean' }, defects: { type: 'array', items: { type: 'string' } }, checks_run: { type: 'string' } },
  required: ['pass', 'defects', 'checks_run'],
}
const CRITIC_SCHEMA = {
  type: 'object',
  properties: { complete: { type: 'boolean' }, missing: { type: 'array', items: TASK_ITEM } },
  required: ['complete', 'missing'],
}
const FINAL_SCHEMA = {
  type: 'object',
  properties: {
    merged: { type: 'array', items: { type: 'string' } }, conflicts: { type: 'array', items: { type: 'string' } },
    final_check: { type: 'string' }, passed: { type: 'boolean' },
  },
  required: ['merged', 'conflicts', 'final_check', 'passed'],
}

// ---------- spawning: cap, budget guard, role models, agent types ----------
let SPAWNED = 0, STOPPED = ''
function canSpawn() {
  if (SPAWNED >= MAX_AGENTS) STOPPED = STOPPED || `agent cap ${MAX_AGENTS} reached (cost=${COST}); later work was skipped. Raise args.max_agents to go further.`
  else if (budget.total && budget.remaining() < RESERVE) STOPPED = STOPPED || `token budget reserve reached (${Math.round(budget.remaining() / 1000)}k left); later work was skipped.`
  else return true
  if (STOPPED && !canSpawn.logged) { canSpawn.logged = true; log(STOPPED) }
  return false
}
function spawn(prompt, opts) {
  if (!canSpawn()) return Promise.resolve(null)
  SPAWNED++
  return agent(prompt, opts)
}
// Plugin agent types register only in sessions started with agent-swarm installed.
// args.types=true/false skips the probe (the orchestrator can see its own agent list); otherwise one cheap probe decides for the run.
let TYPES_OK = A.types === true || A.types === false ? Promise.resolve(A.types) : null
function typesOk() {
  if (!TYPES_OK) TYPES_OK = spawn('Reply with the single word OK.', { label: 'probe:agent-types', phase: 'Plan', agentType: 'agent-swarm:swarm-scout', effort: 'low', ...(MODELS.cheap ? { model: MODELS.cheap } : {}) })
    .then(r => r != null, () => false)
    .then(ok => { if (!ok) log('agent-swarm agent types not registered in this session; using the default agent'); return ok })
  return TYPES_OK
}
async function run(prompt, opts) {
  const { agentType, role, ...rest } = opts
  const model = role && MODELS[role]
  if (model) rest.model = model
  // Agent types outside this plugin (user or project agents) skip the probe; the try/catch below falls back.
  if (agentType && (!agentType.startsWith('agent-swarm:') || await typesOk())) {
    try { const r = await spawn(prompt, { ...rest, agentType }); if (r != null) return r } catch (e) {}
    if (STOPPED) return null
  }
  return spawn(prompt, rest)
}

// ---------- graph helpers ----------
const norm = s => String(s).replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase()
function overlaps(a, b) {
  for (const x of a.files || []) for (const y of b.files || []) {
    const X = norm(x), Y = norm(y)
    if (X === Y || X.startsWith(Y + '/') || Y.startsWith(X + '/')) return true
  }
  return false
}
function ancestors(id, byId, seen = new Set()) {
  const t = byId[id]
  for (const d of (t && t.deps) || []) if (!seen.has(d)) { seen.add(d); ancestors(d, byId, seen) }
  return seen
}
function needsWorktree(t, all, byId) {
  if (ISOLATION === 'worktree') return true
  if (ISOLATION === 'shared') return false
  const mine = ancestors(t.id, byId)
  return all.some(o => o.id !== t.id && overlaps(t, o) && !mine.has(o.id) && !ancestors(o.id, byId).has(t.id))
}

// Plan lint in plain code (no agents): caps, unique ids, unknown deps, cycles, missing verify, wide tasks, forbidden ops.
const GHOST = /\b(deploy|publish|git push|force[- ]push|open (a )?pr|create (a )?pull request|wrangler|npm publish|upload|send (an )?email)\b/i
function lint(ts, issues, label) {
  ts = ts.slice()
  if (ts.length > MAX_TASKS) {
    issues.push(`${label}: ${ts.length} tasks over the cost=${COST} cap of ${MAX_TASKS}; dropped ${ts.slice(MAX_TASKS).map(t => t.id).join(', ')}`)
    ts = ts.slice(0, MAX_TASKS)
  }
  const ids = new Set()
  ts = ts.map(t => {
    let id = String(t.id || 'task').replace(/\s+/g, '-')
    while (ids.has(id)) id += '-b'
    ids.add(id)
    return { ...t, id, files: t.files || [], deps: t.deps || [], tier: t.tier || 'medium' }
  })
  for (const t of ts) {
    const unknown = t.deps.filter(d => !ids.has(d) || d === t.id)
    if (unknown.length) { issues.push(`${t.id}: dropped unknown deps ${unknown.join(', ')}`); t.deps = t.deps.filter(d => ids.has(d) && d !== t.id) }
    if (!t.verify) { t.verify = VERIFY_CMD || 'read the changed files and run the most direct check'; issues.push(`${t.id}: no verify step; using "${t.verify}"`) }
    if (t.files.length > 5) issues.push(`${t.id}: writes ${t.files.length} files (over 5); consider splitting`)
    const g = GHOST.exec(`${t.title} ${t.brief}`)
    if (g) issues.push(`${t.id}: mentions "${g[0]}"; swarm agents may not do that and will report blocked`)
  }
  const byId = Object.fromEntries(ts.map(t => [t.id, t]))
  const state = {}
  const visit = id => {
    state[id] = 1
    for (const d of byId[id].deps.slice()) {
      if (state[d] === 1) { byId[id].deps = byId[id].deps.filter(x => x !== d); issues.push(`${id}: removed dep ${d} to break a cycle`) }
      else if (!state[d]) visit(d)
    }
    state[id] = 2
  }
  for (const t of ts) if (!state[t.id]) visit(t.id)
  return ts
}

// ---------- plan ----------
const lintIssues = []
let tasks = A.tasks
if (!tasks || !tasks.length) {
  phase('Plan')
  const plan = await run(
    `${WHERE}${LEARN}You are the planner for an agent swarm. Goal:\n${GOAL}\n\n` +
    `Scout the project (read-only) enough to plan, then split the goal into the FEWEST tasks that parallelise well (at most ${MAX_TASKS}; one task is fine for small goals). ` +
    `Each task: a short id, a title, a self-contained brief (paths, constraints, definition of done; builders cannot see anything else), ` +
    `the files/dirs it writes (at most 5), deps (ids it must wait for), tier (light = mechanical, medium = standard, heavy = tricky/unclear), and how to verify it. ` +
    `Give each file a single owner where possible; binary scene/prefab/asset files must have exactly one owner task. ${ROLE_LIST} ${RULES} ${TERSE}`,
    { label: 'planner', phase: 'Plan', schema: TASKS_SCHEMA, agentType: 'agent-swarm:swarm-scout', effort: 'high', role: 'strong' })
  tasks = (plan && plan.tasks) || []
}
tasks = lint(tasks, lintIssues, 'plan')
for (const i of lintIssues) log(`lint: ${i}`)
log(`cost=${COST} (models ${JSON.stringify(MODELS)}), cap ${MAX_AGENTS} agents; ${tasks.length} tasks: ${tasks.map(t => `${t.id}[${t.tier}]`).join(', ')}`)
if (!tasks.length) return { error: 'planner returned no tasks', agents_used: SPAWNED }

// ---------- build -> verify -> fix, dependency-ordered ----------
const results = {}
async function buildTask(t, all, byId) {
  const wt = needsWorktree(t, all, byId)
  const pr = roleOf(t.pack_role), vName = pr && pr.verifier, vr = roleOf(vName)
  const BUILD_TYPE = typeOf(pr, 'agent-swarm:swarm-builder'), VERIFY_TYPE = typeOf(vr, 'agent-swarm:swarm-verifier')
  const buildModel = dflt => (pr && pr.model) || dflt
  const brief =
    `${WHERE}${LEARN}${rulesOf(pr, t.pack_role)}Swarm task ${t.id}: ${t.title}\n\n${t.brief}\n\nFiles you own: ${(t.files || []).join(', ') || '(see brief)'}\n` +
    `Verify with: ${t.verify || VERIFY_CMD || 'the most direct check available'}\n${RULES}\n${GUARD}\n` +
    `Report in learned[] only non-obvious gotchas or deviations from the brief. ${TERSE}` +
    (wt ? '\nYou are in an isolated git worktree: commit your changes there and report worktree_path and branch.' : '')
  let build = await run(brief, {
    label: `build:${t.id}`, phase: 'Build', schema: BUILD_SCHEMA, role: t.tier === 'heavy' ? 'strong' : buildModel('standard'),
    agentType: BUILD_TYPE, effort: TIER_EFFORT[t.tier], ...(wt ? { isolation: 'worktree' } : {}),
  })
  if (!build) return { id: t.id, status: STOPPED ? 'skipped' : 'failed', reason: STOPPED || 'builder died' }
  if (build.status === 'blocked') return { id: t.id, status: 'blocked', build }
  if (t.tier === 'light' && !VERIFY_LIGHT && build.status === 'done') return { id: t.id, status: 'self-checked', build, worktree: wt, rounds: 0 }

  const loc = wt && build.worktree_path ? `The work is in the git worktree at ${build.worktree_path} (branch ${build.branch || '?'}); inspect it there.\n` : ''
  let verdicts = [], round = 0
  while (true) {
    verdicts = (await parallel(Array.from({ length: VOTES }, (_, i) => () => run(
      `${WHERE}${loc}${rulesOf(vr, vName)}${pr && pr.rules ? `The builder had these role rules; check them too:\n${pr.rules}\n` : ''}Adversarially verify swarm task ${t.id}: ${t.title}.\nBrief:\n${t.brief}\n` +
      `Builder's claim: ${JSON.stringify({ status: build.status, files_changed: build.files_changed, verification: build.verification, notes: build.notes }).slice(0, 800)}\n` +
      `Check: ${t.verify || VERIFY_CMD || 'read the changed files'}\n` +
      `Read the real files. Default to pass=false when you cannot confirm. Reviewer ${i + 1} of ${VOTES}. ${TERSE}`,
      { label: `verify:${t.id}${VOTES > 1 ? '#' + (i + 1) : ''}`, phase: 'Verify', schema: VERDICT_SCHEMA, agentType: VERIFY_TYPE, role: (vr && vr.model) || 'standard' })))).filter(Boolean)
    const passes = verdicts.filter(v => v.pass).length
    if (verdicts.length && passes * 2 > verdicts.length) break
    if (!verdicts.length && STOPPED) return { id: t.id, status: 'unverified', build, verdicts, rounds: round, reason: STOPPED }
    if (round >= MAX_FIX) return { id: t.id, status: 'unverified', build, verdicts, rounds: round }
    round++
    const defects = [...new Set(verdicts.flatMap(v => v.defects))]
    log(`${t.id}: fix round ${round} (${defects.length} defects)`)
    build = await run(
      `${WHERE}${loc}${rulesOf(pr, t.pack_role)}Fix swarm task ${t.id}: ${t.title}. Original brief:\n${t.brief}\n\nVerifiers found these defects:\n- ${defects.join('\n- ')}\n` +
      `Fix them in place${wt ? ' inside that worktree, and commit' : ''}. Do not touch files outside the task. ${GUARD} ${TERSE}`,
      { label: `fix:${t.id}#${round}`, phase: 'Verify', schema: BUILD_SCHEMA, agentType: BUILD_TYPE, effort: 'high',
        role: round > 1 || t.tier === 'heavy' ? 'strong' : buildModel('standard') }) || build
  }
  return { id: t.id, status: 'verified', build, worktree: wt, rounds: round }
}

async function runWave(wave, waveNo) {
  const byId = Object.fromEntries(wave.map(t => [t.id, t]))
  const memo = {}
  const go = id => {
    if (memo[id]) return memo[id]
    const t = byId[id]
    const deps = (t.deps || []).filter(d => byId[d])
    memo[id] = Promise.all(deps.map(go)).then(async depRes => {
      const bad = depRes.filter(r => !OK(r.status))
      if (bad.length) return { id, status: 'skipped', reason: `deps not verified: ${bad.map(b => b.id).join(', ')}` }
      return buildTask(t, wave, byId)
    }).then(r => { results[id] = r; log(`wave ${waveNo} ${id}: ${r.status}`); return r })
    return memo[id]
  }
  return Promise.all(wave.map(t => go(t.id)))
}

let wave = tasks, waveNo = 1
await runWave(wave, waveNo)

// ---------- critic -> follow-up waves ----------
while (CRITIC && waveNo < MAX_WAVES && GOAL && !STOPPED) {
  phase('Critic')
  const summary = Object.values(results).map(r => `${r.id}: ${r.status} ${(r.build && r.build.files_changed || []).join(', ')}`).join('\n')
  const crit = await run(
    `${WHERE}Completeness critic for an agent swarm. Goal:\n${GOAL}\n\nTask results:\n${summary}\n\n` +
    `Read the project as it is now. What does the goal still need that no task delivered (or that failed/unverified)? ` +
    `Return complete=true if nothing material is missing; otherwise up to 6 new tasks in the same format (new unique ids, deps only on each other). Do not invent nice-to-haves. ${ROLE_LIST} ${RULES} ${TERSE}`,
    { label: `critic#${waveNo}`, phase: 'Critic', schema: CRITIC_SCHEMA, agentType: 'agent-swarm:swarm-verifier', effort: 'high', role: 'strong' })
  if (!crit || crit.complete || !crit.missing.length) break
  waveNo++
  const waveIssues = []
  wave = lint(crit.missing.slice(0, 6).map(t => ({ ...t, id: results[t.id] ? `${t.id}-w${waveNo}` : t.id })), waveIssues, `wave ${waveNo}`)
  for (const i of waveIssues) log(`lint: ${i}`)
  lintIssues.push(...waveIssues)
  log(`critic added ${wave.length} tasks for wave ${waveNo}: ${wave.map(t => t.id).join(', ')}`)
  await runWave(wave, waveNo)
}

// ---------- integrate ----------
phase('Integrate')
const branches = Object.values(results).filter(r => r.worktree && OK(r.status) && r.build && r.build.branch)
let final = null
if (branches.length || VERIFY_CMD) {
  final = await run(
    `${WHERE}Integrate an agent swarm's work.\n` +
    (branches.length ? `Merge these verified worktree branches into the current branch, one at a time (git merge --no-ff). On a conflict, resolve it only if the resolution is obvious from both briefs; otherwise abort that merge and list it as a conflict:\n${branches.map(b => `- ${b.build.branch} (task ${b.id})`).join('\n')}\n` : 'No branches to merge.\n') +
    `Then run the final check: ${VERIFY_CMD || 'the project build/tests if any'}. Report honestly. Never force-push or rewrite history. ${GUARD} ${TERSE}`,
    { label: 'integrate', phase: 'Integrate', schema: FINAL_SCHEMA, agentType: 'agent-swarm:swarm-builder', role: 'standard' })
}

const all = Object.values(results)
const count = s => all.filter(r => r.status === s).length
return {
  goal: GOAL,
  cost: COST, models: MODELS, agents_used: SPAWNED, max_agents: MAX_AGENTS, stopped: STOPPED || undefined,
  lint: lintIssues,
  tasks: all.map(r => ({ id: r.id, status: r.status, rounds: r.rounds, files: r.build && r.build.files_changed, verification: r.build && r.build.verification, defects: r.verdicts && [...new Set(r.verdicts.flatMap(v => v.defects))], reason: r.reason })),
  totals: { verified: count('verified'), self_checked: count('self-checked'), unverified: count('unverified'), blocked: count('blocked'), skipped: count('skipped'), failed: count('failed'), waves: waveNo },
  learned: all.flatMap(r => ((r.build && r.build.learned) || []).map(x => ({ task: r.id, insight: x }))),
  integrate: final,
}
