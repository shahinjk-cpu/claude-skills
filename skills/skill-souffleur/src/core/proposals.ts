import { checkEntry, normRoot } from './config.ts'
import type { Session } from './decide.ts'
import { describeNote, describeRule } from './rules.ts'
import type { Config, Note, Rule } from './types.ts'

/** A rule or note that waits for the user's answer. `from` is the entry's source: `user`, `slip` or `skill:<name>`. */
export type Proposal = {
  hash: string
  kind: 'rule' | 'note'
  entry: Rule | Note
  scope?: 'everywhere' | 'project'
  from: string
  /** Where a note came from, for example `CLAUDE.md:12`. The dialog shows it. */
  origin?: string
  /** The passage sits in a file of the project: the dialog offers this project first. */
  project?: boolean
}

export const QUEUE_CAP = 20
/** At most this many proposals that came from skill texts wait at once. */
export const SKILL_QUEUE_CAP = 6
export const YES_EVERYWHERE = 'Yes, everywhere'
export const YES_PROJECT = 'Yes, this project only'
export const NO = 'No'
export const OPTIONS = [YES_EVERYWHERE, YES_PROJECT, NO]
const MAX_NOTE = 500

/** FNV-1a over the UTF-16 code units of the text, 64 bits, as 16 hex digits. No Node crypto in the core. */
export function fnv(text: string): string {
  let h = 0xcbf29ce484222325n
  for (let i = 0; i < text.length; i++) {
    h ^= BigInt(text.charCodeAt(i))
    h = (h * 0x100000001b3n) & 0xffffffffffffffffn
  }
  return h.toString(16).padStart(16, '0')
}

/** What an entry says, without its id, source or `where`, so the same content hashes the same wherever it came from. */
export function hashEntry(kind: 'rule' | 'note', entry: Rule | Note): string {
  const { id: _id, source: _source, where: _where, ...content } = entry
  const sorted = Object.fromEntries(Object.entries(content).sort(([a], [b]) => (a < b ? -1 : 1)))
  return fnv(`${kind}:${JSON.stringify(sorted)}`)
}

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)

/** A proposal from tool input or the small model: `kind` plus the fields of a rule or note. The id comes from the content. */
export function makeProposal(raw: unknown, from: string, config: Pick<Config, 'userNeeds'>): { proposal?: Proposal; error?: string } {
  if (!isObject(raw)) return { error: 'the proposal must be an object' }
  const kind = raw.kind
  if (kind !== 'rule' && kind !== 'note') return { error: 'kind must be "rule" or "note"' }
  const { kind: _kind, why: _why, id: _id, source: _source, where: _where, ...fields } = raw
  const drafts: Record<string, unknown> = { ...fields, id: 'draft', source: from }
  if (kind === 'note' && typeof drafts.text === 'string') drafts.text = drafts.text.trim()
  const checked = checkEntry(kind, drafts, config.userNeeds ?? [])
  if (checked.error !== undefined || checked.entry === undefined) return { error: checked.error ?? 'invalid entry' }
  const hash = hashEntry(kind, checked.entry)
  const entry = { ...checked.entry, id: `${kind}-${hash.slice(0, 8)}` }
  return { proposal: { hash, kind, entry, from } }
}

export type EnqueueStatus = 'queued' | 'duplicate' | 'declined' | 'full'

/** Adds a proposal unless the queue is full, the user declined it before, or an equal rule or note exists or waits. */
export function enqueue(config: Config, s: Session, p: Proposal): { session: Session; status: EnqueueStatus } {
  if (s.declined.includes(p.hash)) return { session: s, status: 'declined' }
  const known = [...config.rules.map((r) => hashEntry('rule', r)), ...config.notes.map((n) => hashEntry('note', n)), ...s.proposals.map((q) => q.hash)]
  if (known.includes(p.hash)) return { session: s, status: 'duplicate' }
  if (s.proposals.length >= QUEUE_CAP) return { session: s, status: 'full' }
  const fromSkill = (q: Proposal) => q.from.startsWith('skill:')
  if (fromSkill(p)) {
    if (s.proposals.filter(fromSkill).length >= SKILL_QUEUE_CAP) return { session: s, status: 'full' }
    return { session: { ...s, proposals: [...s.proposals, p] }, status: 'queued' }
  }
  // A slip or the user's own words are asked about before anything a skill text suggested.
  const at = s.proposals.findIndex(fromSkill)
  const proposals = at < 0 ? [...s.proposals, p] : [...s.proposals.slice(0, at), p, ...s.proposals.slice(at)]
  return { session: { ...s, proposals }, status: 'queued' }
}

/** The short form of the entry a dialog and a listing show. */
export const describeProposal = (p: Proposal): string => (p.kind === 'rule' ? describeRule(p.entry as Rule) : describeNote(p.entry as Note))

/** The first waiting proposal as a dialog question. One question per turn: the caller asks once and stops. */
export function nextQuestion(s: Session): { hash: string; question: string; options: string[] } | undefined {
  const p = s.proposals[0]
  if (p === undefined) return undefined
  const from = p.origin === undefined ? '' : ` from ${p.origin}`
  const caution = p.from.startsWith('skill:') ? "Read from a skill's text, not verified: " : ''
  const head = caution === '' ? 'Add' : 'add'
  return { hash: p.hash, question: `${caution}${head} ${p.kind}${from}: ${describeProposal(p)}?`, options: p.project ? [YES_PROJECT, YES_EVERYWHERE, NO] : [...OPTIONS] }
}

/** The proposal an id (the entry id or the hash) names. */
export const findProposal = (s: Session, id: string): Proposal | undefined => s.proposals.find((p) => p.entry.id === id || p.hash === id)

const clip = (text: string) => (text.length > 200 ? `${text.slice(0, 200)}...` : text)

/**
 * Applies the user's answer. A yes returns the entry to write (with `where` for the project answer and the root known)
 * and removes the proposal; a confirmed note without `need` is also sent once in the next context. `No` remembers the hash.
 * Any other text asks the model to revise the proposal. An empty answer (a dismissed dialog) changes nothing.
 */
export function answer(config: Config, s: Session, hash: string, label: string, root?: string): { session: Session; write?: { kind: 'rule' | 'note'; entry: Rule | Note }; revise?: string; note?: string } {
  void config
  const p = s.proposals.find((q) => q.hash === hash)
  if (p === undefined || label.trim() === '') return { session: s }
  const rest = s.proposals.filter((q) => q.hash !== hash)
  if (label === NO) return { session: { ...s, proposals: rest, declined: [...s.declined, hash] } }
  if (label === YES_EVERYWHERE || label === YES_PROJECT) {
    if (label === YES_PROJECT && root === undefined) return { session: s, note: 'The project folder is unknown, so nothing was added.' }
    const entry = label === YES_PROJECT ? { ...p.entry, where: normRoot(root!) } : { ...p.entry }
    const fresh = p.kind === 'note' && (entry as Note).need === undefined ? [...s.freshNotes, entry.id] : s.freshNotes
    return { session: { ...s, proposals: rest, freshNotes: fresh }, write: { kind: p.kind, entry } }
  }
  if (p.from.startsWith('skill:')) {
    const revise = `Souffleur: the user answered proposal ${p.entry.id} with a request to revise it: ${clip(label.trim())}. Call souffleur_propose again with the revised ${p.kind}.`
    return { session: { ...s, proposals: rest, revise: [...s.revise, revise] }, revise }
  }
  const revise = `Souffleur: the user answered a proposal ("${clip(describeProposal(p))}") with a request to revise it: ${clip(label.trim())}. Call souffleur_propose again with the revised ${p.kind}.`
  return { session: { ...s, proposals: rest, revise: [...s.revise, revise] }, revise }
}

const isDoc = (v: unknown): v is Record<string, unknown> => isObject(v)

/** The user file with one entry added; every other key stays. A taken id leaves the file as it was and says so. */
export function addEntry(doc: unknown, kind: 'rule' | 'note', entry: Rule | Note, where?: string): { config: unknown; note?: string } {
  const key = kind === 'rule' ? 'rules' : 'notes'
  const base: Record<string, unknown> = isDoc(doc) ? { ...doc } : {}
  const list: unknown[] = Array.isArray(base[key]) ? [...(base[key] as unknown[])] : []
  if (list.some((x) => isObject(x) && x.id === entry.id)) return { config: doc, note: `${entry.id} is already in the file.` }
  list.push(where === undefined ? entry : { ...entry, where })
  base[key] = list
  return { config: base }
}

/** The prompt the small model shapes a user's words with. */
export function shapePrompt(text: string, needs: Record<string, string>): string {
  const needList = Object.entries(needs).map(([k, v]) => `${k}: ${v}`).join('\n') || 'none'
  return [
    'Turn the user instruction into one JSON object, nothing else.',
    'A checkable rule has one of three shapes: {"kind":"rule","before":{"tools":["Agent"]},"skill":"<skill name>"}, {"kind":"rule","before":{"tools":["Agent"]},"field":"model"}, {"kind":"rule","after":{"tools":["Edit"],"paths":["src/**"]},"evidence":{"tool":"Bash","command":"npm test"}}.',
    'Anything else is a note: {"kind":"note","text":"<one line>"}, with an optional "need" from the list below when it only matters for that kind of work.',
    `Needs:\n${needList}`,
    `Instruction: ${text}`,
  ].join('\n\n')
}

/** Reads the small model's answer for `text`; anything unusable becomes a note with the user's own words. */
export function parseShaped(raw: string, text: string, config: Pick<Config, 'userNeeds'>): Proposal {
  const start = raw.indexOf('{')
  const end = raw.lastIndexOf('}')
  if (start >= 0 && end > start) {
    try {
      const made = makeProposal(JSON.parse(raw.slice(start, end + 1)), 'user', config)
      if (made.proposal) return made.proposal
    } catch {
      // fall through to the plain note
    }
  }
  const made = makeProposal({ kind: 'note', text: text.trim().slice(0, MAX_NOTE) }, 'user', config)
  if (made.proposal) return made.proposal
  const hash = fnv(`note:${text}`)
  return { hash, kind: 'note', from: 'user', entry: { id: `note-${hash.slice(0, 8)}`, text: text.replace(/\s+/g, ' ').trim().slice(0, MAX_NOTE) || 'note', source: 'user' } }
}

/** One listing line per waiting proposal. */
export function proposalLines(s: Session): string[] {
  return s.proposals.map((p) => `- ${p.entry.id}: ${p.kind} ${describeProposal(p)} (${p.from})`)
}
