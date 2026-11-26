export const meta = {
  name: 'swarm-sweep',
  description: 'Agent swarm sweep: apply one instruction to many items (files, assets, scenes, docs), verify (sampled in lean mode), report per item (cost-aware)',
  whenToUse: 'Same job over a long list: migrations, audits per file, asset passes, research over many sources',
  phases: [
    { title: 'Do', detail: 'one agent per chunk of items (auto-chunked to fit the agent cap)' },
    { title: 'Verify', detail: 'one skeptic per verified chunk' },
  ],
}

// ---------- args ----------
const A = args || {}
const ITEMS = A.items || []
const INSTR = A.instruction || ''
const MODE = A.mode || 'read'                 // read | write
const VERIFY = A.verify !== false && MODE === 'write' ? true : A.verify === true
const ISOLATION = A.isolation || 'shared'     // shared | worktree (write mode, when items can collide)
const CWD = A.cwd || ''
const HINT = A.schema_hint || 'a short factual result'
if (!ITEMS.length || !INSTR) throw new Error('swarm-sweep needs args.items and args.instruction')

// ---------- cost profile ----------
const COST = ['lean', 'balanced', 'max'].includes(A.cost) ? A.cost : 'lean'
const PROFILES = {
  lean: { cheap: 'haiku', standard: 'sonnet', strong: undefined },
  balanced: { cheap: 'haiku', standard: undefined, strong: undefined },
  max: { cheap: undefined, standard: undefined, strong: undefined },
}
const MODELS = { ...PROFILES[COST], ...(A.models || {}) }
const MAX_AGENTS = A.max_agents ?? { lean: 60, balanced: 200, max: 1000 }[COST]
const RESERVE = A.budget_reserve ?? 20000
const DO_ROLE = A.role || (MODE === 'read' ? 'cheap' : 'standard')
// Pack roles: args.roles as in swarm-build; pack_role does the items, verify_pack_role checks them.
const ROLES = A.roles || {}
const BASE_TYPES = {
  builder: 'agent-swarm:swarm-builder', scout: 'agent-swarm:swarm-scout', verifier: 'agent-swarm:swarm-verifier',
  researcher: 'agent-swarm:swarm-researcher', writer: 'agent-swarm:swarm-writer', operator: 'agent-swarm:swarm-operator',
}
const typeOf = (r, fallback) => (r && r.agentType && (BASE_TYPES[r.agentType] || r.agentType)) || fallback
const rulesOf = (r, name) => (r && r.rules ? `Role: ${name}. Rules for this role:
${r.rules}

` : '')
const PR = ROLES[A.pack_role] || null
const VR_NAME = A.verify_pack_role || (PR && PR.verifier) || ''
const VR = ROLES[VR_NAME] || null
const DO_TYPE = typeOf(PR, MODE === 'read' ? 'agent-swarm:swarm-scout' : 'agent-swarm:swarm-builder')
const VERIFY_TYPE = typeOf(VR, 'agent-swarm:swarm-verifier')
const DO_MODEL = A.role || (PR && PR.model) || DO_ROLE
const RATE = Math.max(1, A.verify_rate ?? (COST === 'lean' ? 3 : 1))   // verify every Nth chunk
// Auto-chunk so do + sampled verify fit under the cap (one slot kept for the probe).
const perChunk = 1 + (VERIFY ? 1 / RATE : 0)
const maxChunks = Math.max(1, Math.floor((MAX_AGENTS - 1) / perChunk))
const CHUNK = Math.max(1, A.chunk || Math.ceil(ITEMS.length / maxChunks))
const WHERE = CWD ? `Project directory: ${CWD} (cd there first).\n` : ''
const GUARD = 'Never deploy, publish, post, send, buy, create accounts, enter credentials, download packs/software, push, open PRs, force-push or permanently delete data.'
const TERSE = 'Be terse: return results, not narration.'
const RES = {
  type: 'object',
  properties: {
    results: { type: 'array', items: { type: 'object', properties: {
      item: { type: 'string' }, status: { type: 'string', enum: ['ok', 'changed', 'issue', 'failed', 'skipped'] }, result: { type: 'string' },
    }, required: ['item', 'status', 'result'] } },
  },
  required: ['results'],
}
const VERDICT = { type: 'object', properties: { pass: { type: 'boolean' }, problem: { type: 'string' } }, required: ['pass', 'problem'] }

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
  if (!TYPES_OK) TYPES_OK = spawn('Reply with the single word OK.', { label: 'probe:agent-types', phase: 'Do', agentType: 'agent-swarm:swarm-scout', effort: 'low', ...(MODELS.cheap ? { model: MODELS.cheap } : {}) })
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

const chunks = []
for (let i = 0; i < ITEMS.length; i += CHUNK) chunks.push(ITEMS.slice(i, i + CHUNK).map(String))
const sampled = VERIFY ? Math.ceil(chunks.length / RATE) : 0
log(`${ITEMS.length} items in ${chunks.length} agents (chunk ${CHUNK}), mode=${MODE}, cost=${COST}, do=${A.pack_role || 'base'}/${DO_MODEL}` +
  (VERIFY ? `, verify ${RATE === 1 ? 'every chunk' : `1 in ${RATE} chunks (${sampled} of ${chunks.length}); the rest come back verified=null`}` : ', no verify'))

const out = await pipeline(chunks,
  (chunk, _o, i) => run(
    `${WHERE}${INSTR}\n\nItems (${chunk.length}):\n- ${chunk.join('\n- ')}\n\n` +
    (MODE === 'read' ? 'Read only: do not modify any file.\n' : 'Change only what the instruction requires for these items; nothing else.\n') +
    `Return one result per item: ${HINT}. ${TERSE} ${GUARD}`,
    { label: `do:${i + 1}`, phase: 'Do', schema: RES, effort: A.effort, role: DO_MODEL,
      agentType: DO_TYPE,
      ...(MODE === 'write' && ISOLATION === 'worktree' ? { isolation: 'worktree' } : {}) }),
  async (res, chunk, i) => {
    const rs = (res && res.results) || chunk.map(item => ({ item, status: STOPPED ? 'skipped' : 'failed', result: STOPPED ? 'not run: ' + STOPPED : 'agent returned nothing' }))
    if (!VERIFY || !res) return rs
    if (i % RATE !== 0) return rs.map(r => ({ ...r, verified: null }))
    const v = await run(
      `${WHERE}${rulesOf(VR, VR_NAME)}Skeptically check this sweep result. Instruction was:\n${INSTR}\n\nClaimed results:\n${JSON.stringify(rs).slice(0, 3000)}\n` +
      `Inspect the real items. pass=false if any claim is wrong or incomplete; say which item and why. ${TERSE}`,
      { label: `verify:${i + 1}`, phase: 'Verify', schema: VERDICT, role: (VR && VR.model) || 'standard', agentType: VERIFY_TYPE })
    return rs.map(r => ({ ...r, verified: v ? v.pass : null, verify_note: v && !v.pass ? v.problem : undefined }))
  })

const flat = out.filter(Boolean).flat()
const by = s => flat.filter(r => r.status === s).length
return {
  cost: COST, models: MODELS, agents_used: SPAWNED, max_agents: MAX_AGENTS, stopped: STOPPED || null, chunk: CHUNK, verify_rate: VERIFY ? RATE : null,
  totals: { items: ITEMS.length, returned: flat.length, ok: by('ok'), changed: by('changed'), issue: by('issue'), failed: by('failed'), skipped: by('skipped'),
    verified: flat.filter(r => r.verified === true).length, verify_failed: flat.filter(r => r.verified === false).length, unverified: flat.filter(r => r.verified == null).length },
  results: flat,
}
