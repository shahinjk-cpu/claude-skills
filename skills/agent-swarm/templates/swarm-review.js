export const meta = {
  name: 'swarm-review',
  description: 'Agent swarm review: lens finders, fuzzy dedup, adversarial verify with high-severity escalation, loop until no new findings (cost-aware)',
  whenToUse: 'Audits and reviews of a diff, folder, game build or design doc',
  phases: [
    { title: 'Find', detail: 'one finder per lens per round' },
    { title: 'Verify', detail: 'skeptics per fresh finding; extra votes only for upheld high-severity ones' },
  ],
}

// ---------- args ----------
const A = args || {}
const TARGET = A.target || 'the current git diff'
const CWD = A.cwd || ''

// ---------- cost profile ----------
// lean (default): cheap=haiku, standard=sonnet, strong=session model. balanced: only cheap is downgraded. max: everything inherits.
const COST = ['lean', 'balanced', 'max'].includes(A.cost) ? A.cost : 'lean'
const PROFILES = {
  lean: { cheap: 'haiku', standard: 'sonnet', strong: undefined },
  balanced: { cheap: 'haiku', standard: undefined, strong: undefined },
  max: { cheap: undefined, standard: undefined, strong: undefined },
}
const MODELS = { ...PROFILES[COST], ...(A.models || {}) }
const P = {
  lean: { lenses: 3, rounds: 2, votes: 1, high: 3, cap: 40 },
  balanced: { lenses: 5, rounds: 3, votes: 3, high: 3, cap: 150 },
  max: { lenses: 5, rounds: 4, votes: 3, high: 5, cap: 1000 },
}[COST]
const MAX_AGENTS = A.max_agents ?? P.cap
const RESERVE = A.budget_reserve ?? 20000
const LENSES_LEAN = ['correctness bugs and edge cases', 'error handling, security and data safety', 'missing pieces versus intent']
const LENSES_FULL = ['correctness bugs', 'edge cases and error handling', 'security and data safety', 'performance', 'missing pieces versus intent']
const LENSES = A.lenses && A.lenses.length ? A.lenses : (P.lenses <= 3 ? LENSES_LEAN : LENSES_FULL)
const VOTES = Math.max(1, Math.min(5, A.votes ?? P.votes))
const HIGH_VOTES = Math.max(VOTES, Math.min(5, A.high_votes ?? P.high))
const MAX_ROUNDS = A.max_rounds ?? P.rounds
const BATCH = Math.max(1, A.batch_verify ?? { lean: 6, balanced: 3, max: 1 }[COST])   // findings per first-vote skeptic
const ROLE = A.role || 'standard'
// Pack roles: args.roles as in swarm-build; finder_role finds, verifier_role tries to refute.
const ROLES = A.roles || {}
const BASE_TYPES = {
  builder: 'agent-swarm:swarm-builder', scout: 'agent-swarm:swarm-scout', verifier: 'agent-swarm:swarm-verifier',
  researcher: 'agent-swarm:swarm-researcher', writer: 'agent-swarm:swarm-writer', operator: 'agent-swarm:swarm-operator',
}
const typeOf = (r, fallback) => (r && r.agentType && (BASE_TYPES[r.agentType] || r.agentType)) || fallback
const rulesOf = (r, name) => (r && r.rules ? `Role: ${name}. Rules for this role:\n${r.rules}\n\n` : '')
const FR = ROLES[A.finder_role] || null, VR = ROLES[A.verifier_role] || null
const FIND_TYPE = typeOf(FR, 'agent-swarm:swarm-scout'), VERIFY_TYPE = typeOf(VR, 'agent-swarm:swarm-verifier')
const FIND_MODEL = A.role || (FR && FR.model) || ROLE, VERIFY_MODEL = A.role || (VR && VR.model) || ROLE
const FRULES = rulesOf(FR, A.finder_role), VRULES = rulesOf(VR, A.verifier_role)
const WHERE = CWD ? `Project directory: ${CWD} (cd there first). Read only.\n` : 'Read only.\n'
const TERSE = 'Be terse: return results, not narration.'

const FIND = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  file: { type: 'string' }, line: { type: 'number' }, title: { type: 'string' }, detail: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
}, required: ['file', 'title', 'detail', 'severity'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, why: { type: 'string' } }, required: ['refuted', 'why'] }
const BATCH_VERDICT = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
  index: { type: 'number' }, refuted: { type: 'boolean' }, why: { type: 'string' } }, required: ['index', 'refuted', 'why'] } } }, required: ['verdicts'] }

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
let TYPES_OK = A.types === true || A.types === false ? Promise.resolve(A.types) : null
function typesOk() {
  if (!TYPES_OK) TYPES_OK = spawn('Reply with the single word OK.', { label: 'probe:agent-types', phase: 'Find', agentType: 'agent-swarm:swarm-scout', effort: 'low', ...(MODELS.cheap ? { model: MODELS.cheap } : {}) })
    .then(r => r != null, () => false)
    .then(ok => { if (!ok) log('agent-swarm agent types not registered in this session; using the default agent'); return ok })
  return TYPES_OK
}
async function run(prompt, opts) {
  const { agentType, role, ...rest } = opts
  const model = role && MODELS[role]
  if (model) rest.model = model
  if (agentType && (!agentType.startsWith('agent-swarm:') || await typesOk())) {
    try { const r = await spawn(prompt, { ...rest, agentType }); if (r != null) return r } catch (e) {}
    if (STOPPED) return null
  }
  return spawn(prompt, rest)
}

// ---------- fuzzy dedup: same file, nearby line, similar title words ----------
const STOP = new Set('a an the of in on at to for and or is are be not no with without when if this that it its from by as missing can may'.split(' '))
const words = s => new Set(String(s).toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').split(/\s+/).filter(w => w.length > 2 && !STOP.has(w)))
function jaccard(a, b) {
  if (!a.size || !b.size) return 0
  let n = 0
  for (const w of a) if (b.has(w)) n++
  return n / (a.size + b.size - n)
}
const nfile = f => String(f || '').replace(/\\/g, '/').toLowerCase().replace(/^\.\//, '')
function dup(f, g) {
  if (nfile(f.file) !== nfile(g.file)) return false
  const j = jaccard(f._w, g._w)
  if (f.line == null || g.line == null) return j >= 0.5
  const d = Math.abs(f.line - g.line)
  return (d <= 3 && j >= 0.3) || (d <= 15 && j >= 0.5)
}

const seen = [], confirmed = []
let round = 0
while (round < MAX_ROUNDS && !STOPPED) {
  round++
  const already = seen.slice(-60).map(f => `${f.file}${f.line ? ':' + f.line : ''} ${f.title}`).join('; ')
  const found = (await parallel(LENSES.map((lens, i) => () => run(
    `${WHERE}${FRULES}Review ${TARGET} through this lens: ${lens}. Round ${round}.` +
    (already ? ` Already reported (do not repeat): ${already}` : '') +
    ` Report only concrete, checkable problems with file and line. ${TERSE}`,
    { label: `find:${i + 1}r${round}`, phase: 'Find', schema: FIND, role: FIND_MODEL, agentType: FIND_TYPE })))).filter(Boolean).flatMap(r => r.findings || [])
  const fresh = []
  for (const f of found) {
    f._w = words(f.title)
    if (!seen.some(g => dup(f, g)) && !fresh.some(g => dup(f, g))) fresh.push(f)
  }
  seen.push(...fresh)
  log(`round ${round}: ${found.length} found, ${fresh.length} new`)
  if (!fresh.length) break
  const verifyPrompt = f => `${WHERE}${VRULES}Try to refute this review finding. Read the real code. Default to refuted=true if you cannot confirm it. ${TERSE}\n${JSON.stringify({ file: f.file, line: f.line, title: f.title, detail: f.detail, severity: f.severity })}`
  const vote = (f, v) => run(verifyPrompt(f), { label: `verify:${f.file}#${v + 1}`, phase: 'Verify', schema: VERDICT, role: VERIFY_MODEL, agentType: VERIFY_TYPE })
  // Batched first vote (lean): one skeptic per file checks up to BATCH findings. Each agent carries ~65k base context,
  // so batching cuts verify cost several-fold. Votes 2+ and high-severity escalation stay per finding.
  const firstVotes = new Map()
  if (BATCH > 1) {
    const groups = []
    for (const f of fresh) {
      let g = groups.find(x => nfile(x[0].file) === nfile(f.file) && x.length < BATCH)
      if (!g) groups.push(g = [])
      g.push(f)
    }
    await parallel(groups.map((g, gi) => () => run(
      `${WHERE}${VRULES}Try to refute each of these ${g.length} review findings. Read the real code. Default to refuted=true for any you cannot confirm. Return one verdict per finding, same order, with its index. ${TERSE}\n` +
      g.map((f, k) => `${k}. ${JSON.stringify({ file: f.file, line: f.line, title: f.title, detail: f.detail, severity: f.severity })}`).join('\n'),
      { label: `verify:batch${gi + 1}r${round}`, phase: 'Verify', schema: BATCH_VERDICT, role: VERIFY_MODEL, agentType: VERIFY_TYPE })
      .then(r => { for (const v of (r && r.verdicts) || []) if (g[v.index]) firstVotes.set(g[v.index], { refuted: v.refuted, why: v.why }) })))
  }
  const judged = await pipeline(fresh,
    f => BATCH > 1
      ? Promise.all([Promise.resolve(firstVotes.get(f) || null), ...Array.from({ length: VOTES - 1 }, (_, v) => vote(f, v + 1))])
      : parallel(Array.from({ length: VOTES }, (_, v) => () => vote(f, v))),
    async (vs, f) => {
      let ok = vs.filter(Boolean)
      // Escalate: a high-severity finding that survived the first vote(s) gets extra skeptics before it counts.
      if (f.severity === 'high' && HIGH_VOTES > VOTES && ok.some(x => !x.refuted)) {
        const more = await parallel(Array.from({ length: HIGH_VOTES - VOTES }, (_, k) => () => vote(f, VOTES + k)))
        ok = ok.concat(more.filter(Boolean))
      }
      const { _w, ...clean } = f
      return { ...clean, votes: ok.length, upheld: ok.filter(x => !x.refuted).length, why: ok.map(x => x.why).slice(0, 2) }
    })
  confirmed.push(...judged.filter(Boolean).filter(j => j.votes && j.upheld * 2 > j.votes))
}
// ---------- final merge: one entry per root cause ----------
// Confirmed findings often restate one defect with different titles (e.g. 3 lenses all flag the same unchecked input).
// Pass 1 (plain code): same file, lines within 12, and shared words in title+detail. Pass 2 (one cheap agent, skippable
// with merge_agent:false): groups whatever root causes plain code could not see, across lines or files.
const order = { high: 0, medium: 1, low: 2 }
const parent = confirmed.map((_, i) => i)
const find = i => parent[i] === i ? i : (parent[i] = find(parent[i]))
const join = (a, b) => { a = find(a); b = find(b); if (a !== b) parent[Math.max(a, b)] = Math.min(a, b) }
const cw = confirmed.map(f => words(`${f.title} ${f.detail || ''}`))
for (let i = 0; i < confirmed.length; i++) for (let k = i + 1; k < confirmed.length; k++) {
  const f = confirmed[i], g = confirmed[k]
  if (nfile(f.file) !== nfile(g.file)) continue
  const near = f.line == null || g.line == null || Math.abs(f.line - g.line) <= 12
  if (near && jaccard(cw[i], cw[k]) >= 0.2) join(i, k)
}
let mergedBy = 'code'
if (confirmed.length > 3 && A.merge_agent !== false && !STOPPED) {
  const GROUPS = { type: 'object', properties: { groups: { type: 'array', items: { type: 'array', items: { type: 'number' } } } }, required: ['groups'] }
  const r = await run(
    `These ${confirmed.length} review findings were each confirmed. Several may describe the SAME underlying defect (same root cause, ` +
    `one fix would resolve all of them). Return groups of indices that share a root cause; leave out findings that stand alone. ` +
    `Do not group findings that merely sit in the same file. Do not read files unless a pair is truly ambiguous. ${TERSE}\n` +
    confirmed.map((f, i) => `${i}. ${f.file}${f.line ? ':' + f.line : ''} [${f.severity}] ${f.title} - ${String(f.detail || '').slice(0, 200)}`).join('\n'),
    { label: 'merge:root-causes', phase: 'Verify', schema: GROUPS, role: 'cheap', effort: 'low', agentType: 'agent-swarm:swarm-scout' })
  if (r && Array.isArray(r.groups)) {
    mergedBy = 'code+agent'
    for (const g of r.groups) { const ix = (g || []).filter(i => Number.isInteger(i) && i >= 0 && i < confirmed.length); for (const i of ix.slice(1)) join(ix[0], i) }
  }
}
const clusters = new Map()
confirmed.forEach((f, i) => { const r = find(i); if (!clusters.has(r)) clusters.set(r, []); clusters.get(r).push(f) })
const merged = [...clusters.values()].map(fs => {
  fs.sort((a, b) => order[a.severity] - order[b.severity] || b.upheld - a.upheld)
  const [top, ...rest] = fs
  return rest.length ? { ...top, also: rest.map(f => ({ file: f.file, line: f.line, title: f.title, severity: f.severity })) } : top
})
merged.sort((a, b) => order[a.severity] - order[b.severity])
if (merged.length < confirmed.length) log(`merge: ${confirmed.length} confirmed -> ${merged.length} root causes (${mergedBy})`)
return { cost: COST, models: MODELS, agents_used: SPAWNED, max_agents: MAX_AGENTS, stopped: STOPPED || null, batch_verify: BATCH, rounds: round,
  candidates: seen.length, confirmed_raw: confirmed.length, merged_by: mergedBy, confirmed: merged }
