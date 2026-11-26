import { matches, matchesCommand } from './config.ts'
import { compacted, initLedger, markInstalled, requested, skillLoaded, syncLedger } from './ledger.ts'
import type { Ledger } from './ledger.ts'
import { neededSkills } from './needs.ts'
import type { Proposal } from './proposals.ts'
import { checkRules, contextNotes, ruleKind, ruleSkillNames } from './rules.ts'
import { renderTable } from './status.ts'
import type { Config, NeedName, SkillName } from './types.ts'

/** An open duty. `denied` is set once the duty has denied a call, so the retry passes. */
export type Duty = { skill: SkillName; openedAt: number; by: string; denied: boolean }

/** Plain JSON only: the adapter persists it and reads it back. */
export type Session = {
  ledger: Ledger
  needs: Record<NeedName, { since: number; reason: string }>
  duties: Duty[]
  paused: boolean
  id: string
  mainSkillCalls: SkillName[]
  subagentsRunning: number
  compactedSincePrompt: boolean
  agentDenied: boolean
  observed: { at: number; reason: string }[]
  errors: string[]
  version?: string
  /** Skills of rules that fired or were loaded: needed for the rest of the session. */
  ruleSkills: SkillName[]
  /** Open `after` rules; `denied` is set once one has denied a call, so the retry passes. */
  openRules: { id: string; by: string; denied: boolean; told: boolean }[]
  /** Field rules that denied and wait for the retry. */
  fieldDenied: string[]
  proposals: Proposal[]
  /** Skill texts read for proposals in this session. */
  skillReads?: number
  /** Skills the main session asked for (a `Skill` call or a typed name) and whose load has not arrived yet. */
  learnCalls?: string[]
  /** Hashes of declined proposals. */
  declined: string[]
  /** Need notes already sent since the last compaction. */
  notesSent: string[]
  /** Confirmed notes without a need, sent once in the next context. */
  freshNotes: string[]
  /** Requests to revise a proposal, sent once in the next context. */
  revise: string[]
  /** Hashes of the proposals the model made through the tool: at most five per session. */
  proposed: string[]
  /** Counts the stores, so the newer of two copies can be told. */
  rev?: number
}

export type CoreEvent =
  | { type: 'start'; now: number; start: 'startup' | 'resume' | 'clear'; version?: string }
  | { type: 'skill'; now: number; skill: string; text?: string; source?: string; pluginName?: string; path?: string }
  | { type: 'compact'; now: number; phase: 'before' | 'after'; trigger: string; skipped?: boolean; agentId?: string }
  | { type: 'prompt'; now: number; text: string; fromUser: boolean; matched: NeedName[]; root?: string }
  /** `present` names the arguments the call carries, for field rules. */
  | { type: 'tool'; now: number; tool: string; path?: string; command?: string; brief?: string; skill?: string; model?: string; present?: string[]; agentId?: string; root?: string; tree?: string }
  | { type: 'command'; now: number; args: string; root?: string }
  | { type: 'typed'; now: number; name: string }
  | { type: 'agentDone'; now: number }
  /** The config was read again (after `/souffleur init`): the ledger follows it, and `errors` replace the old config errors. */
  | { type: 'config'; now: number; errors: string[] }
  /** The skill names this session lists. An empty list means unknown. */
  | { type: 'installed'; now: number; names: string[] }
  | { type: 'error'; now: number; where: string; message: string }

export type Action =
  | { kind: 'context'; text: string }
  /** A main-session skill load whose text may be read for proposals; the adapter decides whether to. */
  | { kind: 'learn'; skill: SkillName; text: string; source?: string; pluginName?: string; path?: string }
  | { kind: 'deny'; reason: string }
  | { kind: 'reply'; text: string }
  | { kind: 'toolContext'; text: string }

type Result = { session: Session; actions: Action[] }

const KEEP = 20
const MAX_REQUESTS = 2
const COMPACT_TRIGGERS = ['manual', 'auto', 'plugin']
const BRIEF_SKILLS = /^skills:\s*\S/im
const PAUSE_HINT = 'To turn checks off for this session: /souffleur pause.'

export function initSession(config: Config, id: string, now: number, start: 'startup' | 'resume' | 'clear', version?: string): Session {
  const s: Session = {
    ledger: initLedger(config, now, start, ruleSkillNames(config)),
    needs: {},
    duties: [],
    paused: false,
    id,
    mainSkillCalls: [],
    subagentsRunning: 0,
    compactedSincePrompt: false,
    agentDenied: false,
    observed: [],
    errors: [],
    ...emptyRules(),
  }
  if (version !== undefined) s.version = version
  return s
}

function emptyRules() {
  return { ruleSkills: [], openRules: [], fieldDenied: [], proposals: [], declined: [], notesSent: [], freshNotes: [], revise: [], proposed: [] }
}

/** A session stored before a field existed gets that field empty. */
export function normalizeSession(s: Session): Session {
  const have = s as unknown as Record<string, unknown>
  const missing = Object.entries(emptyRules()).filter(([key]) => !Array.isArray(have[key]))
  return missing.length ? ({ ...s, ...Object.fromEntries(missing) } as Session) : s
}

export function statusText(config: Config, session: Session, now: number, root?: string): string {
  return renderTable(config, session, now, root)
}

const lastN = <T>(list: T[], item: T): T[] => [...list, item].slice(-KEEP)

export function decide(config: Config, s: Session, e: CoreEvent): Result {
  switch (e.type) {
    case 'start':
      // A resume keeps the ledger: what was loaded stays in the transcript until a compaction.
      if (e.start === 'resume') return { session: e.version === undefined ? s : { ...s, version: e.version }, actions: [] }
      return { session: initSession(config, s.id, e.now, e.start, e.version), actions: [] }
    case 'skill': {
      const announced = (s.learnCalls ?? []).indexOf(e.skill)
      const main = announced >= 0 || s.subagentsRunning === 0
      const learn = main && config.learn.skills && !s.paused && e.text !== undefined && e.text.trim() !== ''
      const session: Session = { ...onSkill(config, s, e), learnCalls: (s.learnCalls ?? []).filter((_, k) => k !== announced) }
      const from = { ...(e.source === undefined ? {} : { source: e.source }), ...(e.pluginName === undefined ? {} : { pluginName: e.pluginName }), ...(e.path === undefined ? {} : { path: e.path }) }
      return { session, actions: learn ? [{ kind: 'learn', skill: e.skill, text: e.text!, ...from }] : [] }
    }
    case 'compact':
      return { session: onCompact(config, s, e), actions: [] }
    case 'prompt':
      return onPrompt(config, s, e)
    case 'tool':
      return onTool(config, s, e)
    case 'command':
      return onCommand(config, s, e)
    case 'typed':
      return { session: { ...(e.name in s.ledger ? { ...s, mainSkillCalls: [...s.mainSkillCalls, e.name], ruleSkills: withRuleSkill(config, s, e.name) } : s), learnCalls: [...(s.learnCalls ?? []), e.name].slice(-KEEP) }, actions: [] }
    case 'config':
      return { session: { ...s, ledger: syncLedger(s.ledger, config, e.now, ruleSkillNames(config)), ruleSkills: s.ruleSkills.filter((n) => ruleSkillNames(config).includes(n)), openRules: s.openRules.filter((o) => config.rules.some((r) => r.id === o.id)), needs: Object.fromEntries(Object.entries(s.needs).filter(([name]) => name in config.needs)), duties: s.duties.filter((d) => d.skill in config.skills), errors: [...s.errors.filter((m) => !m.startsWith('config: ')), ...e.errors.map((m) => `config: ${m}`)].slice(-KEEP) }, actions: [] }
    case 'installed':
      return { session: { ...s, ledger: markInstalled(s.ledger, e.names, e.now) }, actions: [] }
    case 'agentDone':
      return { session: { ...s, subagentsRunning: Math.max(0, s.subagentsRunning - 1) }, actions: [] }
    case 'error':
      return { session: { ...s, errors: lastN(s.errors, `${e.where}: ${e.message}`) }, actions: [] }
  }
}

/** A skill a rule names, once loaded, stays needed for the session. */
function withRuleSkill(config: Config, s: Session, skill: SkillName): SkillName[] {
  return ruleSkillNames(config).includes(skill) && !s.ruleSkills.includes(skill) ? [...s.ruleSkills, skill] : s.ruleSkills
}

function onSkill(config: Config, s: Session, e: Extract<CoreEvent, { type: 'skill' }>): Session {
  const i = s.mainSkillCalls.indexOf(e.skill)
  if (i < 0 && s.subagentsRunning > 0) return s // a subagent's load
  const calls = i < 0 ? s.mainSkillCalls : s.mainSkillCalls.filter((_, k) => k !== i)
  return { ...s, mainSkillCalls: calls, ledger: skillLoaded(s.ledger, e.skill, e.now, 'skill.prompt'), ruleSkills: withRuleSkill(config, s, e.skill) }
}

function onCompact(config: Config, s: Session, e: Extract<CoreEvent, { type: 'compact' }>): Session {
  if (e.agentId !== undefined || e.phase !== 'after' || e.skipped || !COMPACT_TRIGGERS.includes(e.trigger)) return s
  // Need notes went out in a context block the compaction cut: send them again while their need stays active.
  const needNotes = new Set(config.notes.filter((n) => n.need !== undefined).map((n) => n.id))
  return { ...s, ledger: compacted(s.ledger, e.now), compactedSincePrompt: true, notesSent: s.notesSent.filter((id) => !needNotes.has(id)) }
}

/**
 * Asks for needed skills that are missing. Skills asked for twice without a load are not named again;
 * `requested` moves them to unavailable. Restores run in config order with no size cap (the spec's shortcut;
 * add a priority cap if restores push sessions into the next compaction early).
 */
function restore(config: Config, s: Session, now: number): { ledger: Ledger; text?: string } {
  const missing = neededSkills(config, s.needs, s.ruleSkills).filter((name) => {
    const st = s.ledger[name]?.state
    return st === 'absent' || st === 'stale' || st === 'restoring'
  })
  const ask = missing.filter((name) => s.ledger[name]!.requests < MAX_REQUESTS)
  const giveUp = missing.filter((name) => s.ledger[name]!.requests >= MAX_REQUESTS)
  const ledger = requested(s.ledger, [...ask, ...giveUp], now)
  if (ask.length === 0) return { ledger }
  const again = ask.some((name) => s.ledger[name]!.state !== 'absent')
  const why = again ? ' Compaction cut or dropped their text. The note that skills invoked earlier must not be run again does not apply to them: invoke them again.' : ''
  return { ledger, text: `Souffleur: before anything else, invoke these skills with the Skill tool, one after another: ${ask.join(', ')}.${why}` }
}

function onPrompt(config: Config, s: Session, e: Extract<CoreEvent, { type: 'prompt' }>): Result {
  if (!e.fromUser) return { session: s, actions: [] }
  const needs = { ...s.needs }
  for (const name of e.matched) {
    if (name in needs) continue
    needs[name] = { since: e.now, reason: `need:${name} from "${e.text.slice(0, 40)}"` }
  }
  const next: Session = { ...s, needs, compactedSincePrompt: false }
  const r = restore(config, next, e.now)
  next.ledger = r.ledger
  const lines = r.text === undefined ? [] : [r.text]
  const notes = contextNotes(config, next, e.root).kept
  if (notes.length) {
    lines.push(`Souffleur notes from the user's config:\n${notes.map((n) => `- ${n.text}`).join('\n')}`)
    const ids = notes.map((n) => n.id)
    next.notesSent = [...next.notesSent, ...ids.filter((id) => !next.notesSent.includes(id))]
    next.freshNotes = next.freshNotes.filter((id) => !ids.includes(id) && config.notes.some((n) => n.id === id))
  }
  lines.push(...next.revise)
  next.revise = []
  for (const d of next.duties) if (next.ledger[d.skill]?.state !== 'not installed here') lines.push(`Open duty: ${d.skill} (${d.by}).`)
  for (const o of next.openRules) if (!o.told) lines.push(`Open rule: ${o.id} (${o.by}).`)
  next.openRules = next.openRules.map((o) => ({ ...o, told: true }))
  return { session: next, actions: lines.length ? [{ kind: 'context', text: lines.join('\n') }] : [] }
}

function evidenceMatches(ev: { tool: string; command?: string }, e: Extract<CoreEvent, { type: 'tool' }>): boolean {
  if (ev.tool !== e.tool) return false
  return ev.command === undefined || matchesCommand(ev.command, e.command ?? '')
}

function onTool(config: Config, s: Session, e: Extract<CoreEvent, { type: 'tool' }>): Result {
  if (e.agentId !== undefined) return { session: s, actions: [] }
  const next: Session = { ...s }
  const actions: Action[] = []

  if (e.tool === 'Skill' && e.skill !== undefined && e.skill in s.ledger) next.mainSkillCalls = [...s.mainSkillCalls, e.skill]
  // The learn decision keeps its own list: it also covers skills the config does not list.
  if (e.tool === 'Skill' && e.skill !== undefined) next.learnCalls = [...(s.learnCalls ?? []), e.skill].slice(-KEEP)

  if (s.compactedSincePrompt) {
    next.compactedSincePrompt = false
    const r = restore(config, next, e.now)
    next.ledger = r.ledger
    if (r.text !== undefined) actions.push({ kind: 'toolContext', text: r.text })
  }

  next.duties = s.duties.filter((d) => {
    const ev = config.skills[d.skill]?.duty?.evidence
    return !(ev && evidenceMatches(ev, e))
  })

  // Violations: `trusted` ones may deny in enforce mode; the rest (untrusted project skills) only record.
  const trustedRoot = e.root !== undefined && config.trustProjects.includes(e.root)
  const found: { text: string; trusted: boolean }[] = []

  if (!next.paused) {
    if (e.tool === 'Agent') {
      const active = Object.keys(next.needs)
      if (active.length === 0 || BRIEF_SKILLS.test(e.brief ?? '')) next.agentDenied = false
      else if (next.agentDenied) next.agentDenied = false
      else {
        next.agentDenied = true
        found.push({
          text: `Souffleur: add a line "skills: <names>" (or "skills: none" for mechanical work) to the brief, then retry. Configured skills: ${Object.keys(config.skills).filter((n) => next.ledger[n]?.state !== 'not installed here').join(', ') || 'none'}. Active needs: ${active.join(', ')}. ${PAUSE_HINT}`,
          trusted: true,
        })
      }
    }

    const needed = neededSkills(config, next.needs, next.ruleSkills)
    for (const [name, rule] of Object.entries(config.skills)) {
      if (!rule.gate || next.ledger[name]?.state === 'not installed here' || !matches(rule.gate, e.tool, e.path, e.tree ?? e.root)) continue
      const trusted = rule.from === 'user' || trustedRoot
      const state = next.ledger[name]?.state
      if (needed.includes(name) && state !== undefined && state !== 'loaded' && state !== 'unavailable') {
        found.push({ text: `Souffleur: load ${name} with the Skill tool first, then retry. ${PAUSE_HINT}`, trusted })
      }
      const duty = next.duties.find((d) => d.skill === name)
      if (duty && !duty.denied && rule.duty) {
        const ev = rule.duty.evidence
        const what = ev.command === undefined ? ev.tool : `${ev.tool} matching ${ev.command}`
        found.push({ text: `Souffleur: open duty for ${name} (${duty.by}). Do this first: ${what}. Then retry. ${PAUSE_HINT}`, trusted })
        next.duties = next.duties.map((d) => (d === duty ? { ...d, denied: true } : d))
      }
    }
  }

  // Rules: evidence closes and a first match opens even while paused; only the denials and the needed skills stop.
  const checked = checkRules(config, next, e)
  const rr = next.paused ? { ...checked, reasons: [], denied: [], fired: [] } : checked
  for (const reason of rr.reasons) found.push({ text: `${reason} ${PAUSE_HINT}`, trusted: true })
  if (rr.fired.length) next.ruleSkills = [...next.ruleSkills, ...rr.fired.filter((n) => !next.ruleSkills.includes(n))]

  let denied = false
  const trustedText = found.filter((f) => f.trusted).map((f) => f.text).join('\n')
  const untrustedText = found.filter((f) => !f.trusted).map((f) => f.text).join('\n')
  if (trustedText) {
    if (config.mode === 'enforce') {
      denied = true
      actions.push({ kind: 'deny', reason: trustedText })
    } else next.observed = lastN(next.observed, { at: e.now, reason: trustedText })
  }
  if (untrustedText) next.observed = lastN(next.observed, { at: e.now, reason: untrustedText })

  // Retry state moves only with the outcome of the whole call: a denial marks the rules that spoke, a pass uses up their retry
  // and lets evidence close a rule. In observe nothing is denied, so every break is recorded and no retry state is kept.
  if (denied) {
    next.openRules = next.openRules.map((o) => (rr.denied.includes(o.id) ? { ...o, denied: true } : o))
    next.fieldDenied = [...next.fieldDenied, ...rr.denied.filter((id) => !next.fieldDenied.includes(id) && config.rules.some((r) => r.id === id && ruleKind(r) === 'field'))]
  } else {
    next.openRules = next.openRules.filter((o) => !rr.closed.includes(o.id))
    next.fieldDenied = next.fieldDenied.filter((id) => !rr.released.includes(id))
  }

  if (!denied) {
    if (e.tool === 'Agent') next.subagentsRunning += 1
    const by = e.path === undefined ? e.tool : `${e.tool} ${e.path}`
    next.openRules = [...next.openRules, ...rr.opened.map((id) => ({ id, by, denied: false, told: false }))]
    for (const [name, rule] of Object.entries(config.skills)) {
      if (!rule.duty || next.ledger[name]?.state === 'not installed here' || !matches(rule.duty.after, e.tool, e.path, e.tree ?? e.root)) continue
      if (next.duties.some((d) => d.skill === name)) continue
      next.duties = [...next.duties, { skill: name, openedAt: e.now, by: e.path === undefined ? e.tool : `${e.tool} ${e.path}`, denied: false }]
    }
  }
  return { session: next, actions }
}

function onCommand(config: Config, s: Session, e: Extract<CoreEvent, { type: 'command' }>): Result {
  const [verb = '', arg = ''] = e.args.trim().split(/\s+/)
  const reply = (session: Session, text: string): Result => ({ session, actions: [{ kind: 'reply', text }] })
  const known = () => `Known needs: ${Object.keys(config.needs).join(', ') || 'none'}.`
  switch (verb) {
    case '':
    case 'status':
      return reply(s, statusText(config, s, e.now, e.root))
    case 'pause':
      return reply({ ...s, paused: true }, 'Souffleur: checks are off for this session (no gate, duty or brief denial).')
    case 'need':
      if (!(arg in config.needs)) return reply(s, `Unknown need "${arg}". ${known()}`)
      return reply({ ...s, needs: { ...s.needs, [arg]: { since: e.now, reason: 'command' } } }, `Need ${arg} is on.`)
    case 'drop': {
      if (!(arg in config.needs)) return reply(s, `Unknown need "${arg}". ${known()}`)
      const { [arg]: _gone, ...rest } = s.needs
      return reply({ ...s, needs: rest }, `Need ${arg} is off.`)
    }
    default:
      return reply(s, 'Usage: /souffleur [status | need <name> | drop <name> | pause | init | migrate | rule <text> | review | accept <id> | decline <id>]')
  }
}
