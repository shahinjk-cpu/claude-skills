import type { Config, Match, Mode, NeedName, Note, Origin, Rule, SkillName, SkillRule } from './types.ts'

type FileConfig = {
  mode?: Mode
  trustProjects?: string[]
  skills: Record<SkillName, SkillRule>
  needs: Record<NeedName, string>
  rules: Rule[]
  notes: Note[]
  learn?: { skills: boolean }
  /** Every skill and need key the file spells out, valid or not, for clash checks. */
  skillKeys: string[]
  needKeys: string[]
}

class SchemaError extends Error {}

const NAME = /^[A-Za-z0-9:_-]{1,64}$/
const MAX_SHOWN = 80

const hasLineBreak = (s: string): boolean => [...s].some((c) => c.charCodeAt(0) === 10 || c.charCodeAt(0) === 13 || c.charCodeAt(0) === 0x2028 || c.charCodeAt(0) === 0x2029)

/** Quotes file-supplied text for an error message, cut to 80 characters. */
function show(v: unknown): string {
  const s = typeof v === 'string' ? v : JSON.stringify(v) ?? String(v)
  return JSON.stringify(s.length > MAX_SHOWN ? `${s.slice(0, MAX_SHOWN)}...` : s)
}

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v)

function check(ok: boolean, where: string, problem: string): void {
  if (!ok) throw new SchemaError(`${where}: ${problem}`)
}

function onlyKeys(obj: Record<string, unknown>, allowed: string[], where: string): void {
  for (const key of Object.keys(obj)) check(allowed.includes(key), where, `unknown key ${show(key)}`)
}

/** A project root without trailing slashes (`/` stays), so `where` compares by name. */
export const normRoot = (p: string): string => (p.length > 1 ? p.replace(/\/+$/, '') || '/' : p)

/** C0 and C1 controls, line separators and bidirectional controls: none belong in text that reaches the model or a dialog. */
export function hasControl(s: string): boolean {
  return [...s].some((c) => {
    const n = c.charCodeAt(0)
    return n < 0x20 || (n >= 0x7f && n <= 0x9f) || n === 0x2028 || n === 0x2029 || (n >= 0x202a && n <= 0x202e) || (n >= 0x2066 && n <= 0x2069) || n === 0x200e || n === 0x200f
  })
}

const MAX_LIST = 20
const MAX_TOOL = 100
const MAX_GLOB = 200

/** A list of at most 20 one-line strings, each at most `max` characters. */
function stringList(v: unknown, where: string, max = MAX_GLOB): string[] {
  check(Array.isArray(v) && v.every((s) => typeof s === 'string'), where, 'must be a list of strings')
  const list = v as string[]
  check(list.length <= MAX_LIST, where, `must hold at most ${MAX_LIST} items`)
  for (const item of list) check(item.length <= max && !hasControl(item), where, `items must be one line of at most ${max} characters without control characters`)
  return [...list]
}

function checkGlob(glob: string, where: string): void {
  check(glob.length > 0, where, 'glob must not be empty')
  const bad = /[{}[\]!]/.exec(glob)
  check(bad === null, where, `glob ${show(glob)} uses "${bad?.[0]}"; only *, ** and ? are supported`)
}

function parseMatch(v: unknown, where: string): Match {
  check(isObject(v), where, 'must be an object')
  const obj = v as Record<string, unknown>
  onlyKeys(obj, ['tools', 'paths'], where)
  const match: Match = { tools: stringList(obj.tools, `${where}.tools`, MAX_TOOL) }
  check(match.tools.length > 0, `${where}.tools`, 'must not be empty')
  if (obj.paths !== undefined) {
    match.paths = stringList(obj.paths, `${where}.paths`)
    check(match.paths.length > 0, `${where}.paths`, 'must not be empty')
    for (const glob of match.paths) checkGlob(glob, `${where}.paths`)
  }
  return match
}


const SOURCE = /^(skill(:[A-Za-z0-9:_-]{1,64})?|slip|user)$/
const FIELD = /^[A-Za-z0-9_]{1,40}$/
const ENTRY_ID = /^[A-Za-z0-9:_-]{1,64}$/
const MAX_NOTE = 500

function entryCommon(obj: Record<string, unknown>, where: string): { id: string; source: string; where?: string } {
  check(typeof obj.id === 'string' && ENTRY_ID.test(obj.id) && obj.id !== '__proto__', `${where}.id`, `must be a name of letters, digits, ":", "_" or "-", got ${show(obj.id)}`)
  const out: { id: string; source: string; where?: string } = { id: obj.id as string, source: 'user' }
  if (obj.source !== undefined) {
    check(typeof obj.source === 'string' && SOURCE.test(obj.source), `${where}.source`, `must be "user", "slip" or "skill:<name>", got ${show(obj.source)}`)
    out.source = obj.source as string
  }
  if (obj.where !== undefined) {
    check(typeof obj.where === 'string' && /^(\/|[A-Za-z]:[\\/])/.test(obj.where) && !hasControl(obj.where) && obj.where.length <= 500, `${where}.where`, 'must be an absolute one-line path')
    out.where = normRoot(obj.where as string)
  }
  return out
}

/** One rule entry: exactly one kind. Throws a SchemaError that names the problem. */
export function parseRuleEntry(v: unknown, where: string): Rule {
  check(isObject(v), where, 'must be an object')
  const obj = v as Record<string, unknown>
  onlyKeys(obj, ['id', 'where', 'source', 'before', 'skill', 'field', 'after', 'evidence'], where)
  const rule: Rule = entryCommon(obj, where)
  const kinds = [obj.before !== undefined && obj.skill !== undefined, obj.before !== undefined && obj.field !== undefined, obj.after !== undefined && obj.evidence !== undefined].filter(Boolean).length
  const keys = ['before', 'skill', 'field', 'after', 'evidence'].filter((k) => obj[k] !== undefined).length
  check(kinds === 1 && keys === 2, where, 'needs exactly one of: before + skill, before + field, after + evidence')
  if (obj.before !== undefined) rule.before = parseMatch(obj.before, `${where}.before`)
  check(!(obj.skill !== undefined && rule.before?.tools.includes('Skill')), `${where}.before`, 'a skill rule cannot gate the Skill tool: it would block loading its own skill')
  if (obj.skill !== undefined) {
    check(typeof obj.skill === 'string' && NAME.test(obj.skill) && obj.skill !== '__proto__', `${where}.skill`, `must be a skill name, got ${show(obj.skill)}`)
    rule.skill = obj.skill as string
  }
  if (obj.field !== undefined) {
    check(typeof obj.field === 'string' && FIELD.test(obj.field), `${where}.field`, `must be a field name, got ${show(obj.field)}`)
    rule.field = obj.field as string
  }
  if (obj.after !== undefined) rule.after = parseMatch(obj.after, `${where}.after`)
  if (obj.evidence !== undefined) {
    check(isObject(obj.evidence), `${where}.evidence`, 'must be an object')
    const ev = obj.evidence as Record<string, unknown>
    onlyKeys(ev, ['tool', 'command'], `${where}.evidence`)
    check(typeof ev.tool === 'string' && ev.tool.length > 0 && ev.tool.length <= MAX_TOOL && !hasControl(ev.tool), `${where}.evidence.tool`, `must be a one-line string of at most ${MAX_TOOL} characters`)
    const evidence: { tool: string; command?: string } = { tool: ev.tool as string }
    if (ev.command !== undefined) {
      check(typeof ev.command === 'string' && ev.command.length <= MAX_GLOB && !hasControl(ev.command), `${where}.evidence.command`, `must be a one-line string of at most ${MAX_GLOB} characters`)
      checkGlob(ev.command as string, `${where}.evidence.command`)
      evidence.command = ev.command as string
    }
    rule.evidence = evidence
  }
  return rule
}

/** One note entry. `needs` are the need names the file defines. */
export function parseNoteEntry(v: unknown, where: string, needs: readonly string[]): Note {
  check(isObject(v), where, 'must be an object')
  const obj = v as Record<string, unknown>
  onlyKeys(obj, ['id', 'text', 'need', 'where', 'source'], where)
  const note: Note = { ...entryCommon(obj, where), text: '' }
  check(typeof obj.text === 'string' && obj.text.trim().length >= 1 && obj.text.length <= MAX_NOTE && !hasControl(obj.text), `${where}.text`, `must be one line of 1 to ${MAX_NOTE} characters`)
  note.text = (obj.text as string).trim()
  if (obj.need !== undefined) {
    check(typeof obj.need === 'string' && needs.includes(obj.need), `${where}.need`, `must name a need of the file, got ${show(obj.need)}`)
    note.need = obj.need as string
  }
  return note
}

/** Checks an entry a proposal brings, with the same rules the file is read by. */
export function checkEntry(kind: 'rule' | 'note', value: unknown, needs: readonly string[]): { entry?: Rule | Note; error?: string } {
  try {
    return { entry: kind === 'rule' ? parseRuleEntry(value, 'rule') : parseNoteEntry(value, 'note', needs) }
  } catch (e) {
    if (e instanceof SchemaError) return { error: e.message }
    throw e
  }
}

function parseName(name: string, kind: 'skill' | 'need'): void {
  check(NAME.test(name) && name !== '__proto__', `${kind} ${show(name)}`, 'name must match [A-Za-z0-9:_-] and be 1 to 64 characters')
}

function parseRule(v: unknown, where: string): Omit<SkillRule, 'from'> {
  check(isObject(v), where, 'must be an object')
  const obj = v as Record<string, unknown>
  onlyKeys(obj, ['always', 'startup', 'need', 'gate', 'duty'], where)
  const rule: Omit<SkillRule, 'from'> = {}
  if (obj.always !== undefined) {
    check(typeof obj.always === 'boolean', `${where}.always`, 'must be true or false')
    rule.always = obj.always as boolean
  }
  if (obj.startup !== undefined) {
    check(obj.startup === 'injected', `${where}.startup`, 'must be "injected"')
    rule.startup = 'injected'
  }
  if (obj.need !== undefined) {
    check(typeof obj.need === 'string' && NAME.test(obj.need) && obj.need !== '__proto__', `${where}.need`, `must be a need name, got ${show(obj.need)}`)
    rule.need = obj.need as string
  }
  check(!(rule.always === true && rule.need !== undefined), where, '"always" and "need" cannot be combined')
  check(rule.always === true || rule.need !== undefined || rule.startup !== undefined, where, 'needs one of "always", "need" or "startup"')
  if (obj.gate !== undefined) rule.gate = parseMatch(obj.gate, `${where}.gate`)
  if (obj.duty !== undefined) {
    check(isObject(obj.duty), `${where}.duty`, 'must be an object')
    const duty = obj.duty as Record<string, unknown>
    onlyKeys(duty, ['after', 'evidence'], `${where}.duty`)
    const after = parseMatch(duty.after, `${where}.duty.after`)
    check(isObject(duty.evidence), `${where}.duty.evidence`, 'must be an object')
    const ev = duty.evidence as Record<string, unknown>
    onlyKeys(ev, ['tool', 'command'], `${where}.duty.evidence`)
    check(typeof ev.tool === 'string', `${where}.duty.evidence.tool`, 'must be a string')
    const evidence: { tool: string; command?: string } = { tool: ev.tool as string }
    if (ev.command !== undefined) {
      check(typeof ev.command === 'string', `${where}.duty.evidence.command`, 'must be a string')
      checkGlob(ev.command as string, `${where}.duty.evidence.command`)
      evidence.command = ev.command as string
    }
    rule.duty = { after, evidence }
  }
  return rule
}

/** Parses one file. Whole-file problems throw; entry problems are collected and the entry dropped. */
function parseFile(text: string, source: Origin, errors: string[]): FileConfig {
  const label = `${source} config`
  const fail = (message: string): void => void errors.push(`${label}: ${message}`)
  let data: unknown
  try {
    data = JSON.parse(text.charCodeAt(0) === 0xfeff ? text.slice(1) : text)
  } catch (e) {
    throw new SchemaError(`invalid JSON (${show((e as Error).message)})`)
  }
  check(isObject(data), 'top level', 'must be an object')
  const obj = data as Record<string, unknown>
  const file: FileConfig = { skills: {}, needs: {}, rules: [], notes: [], skillKeys: [], needKeys: [] }

  for (const key of Object.keys(obj)) {
    if (key === 'skills' || key === 'needs') continue
    if (key === 'mode' || key === 'trustProjects' || key === 'rules' || key === 'notes' || key === 'learn') {
      if (source === 'project') fail(`${key} is only allowed in the user config; ignored`)
      continue
    }
    fail(`unknown top-level key ${show(key)}; ignored`)
  }

  if (source === 'user' && obj.mode !== undefined) {
    if (obj.mode === 'observe' || obj.mode === 'enforce') file.mode = obj.mode
    else fail('mode: must be "observe" or "enforce"; ignored')
  }
  if (source === 'user' && obj.trustProjects !== undefined) {
    const list = obj.trustProjects
    if (Array.isArray(list) && list.every((p) => typeof p === 'string' && /^(\/|[A-Za-z]:[\\/])/.test(p))) {
      file.trustProjects = [...(list as string[])]
    } else {
      fail('trustProjects: must be a list of absolute paths; ignored')
    }
  }

  if (source === 'user' && obj.learn !== undefined) {
    const l = obj.learn
    if (isObject(l) && Object.keys(l).every((k) => k === 'skills') && (l.skills === undefined || typeof l.skills === 'boolean')) file.learn = { skills: l.skills !== false }
    else fail('learn: must be { "skills": true or false }; ignored')
  }

  for (const [kind, key] of [['skill', 'skills'], ['need', 'needs']] as const) {
    const section = obj[key]
    if (section === undefined) continue
    if (!isObject(section)) {
      fail(`${key}: must be an object; ignored`)
      continue
    }
    for (const [name, value] of Object.entries(section)) {
      ;(kind === 'skill' ? file.skillKeys : file.needKeys).push(name)
      try {
        parseName(name, kind)
        if (kind === 'skill') {
          file.skills[name] = { from: source, ...parseRule(value, `skill ${show(name)}`) }
        } else {
          check(typeof value === 'string', `need ${show(name)}`, 'must be a string')
          const needText = value as string
          check(needText.length >= 1 && needText.length <= 200 && !hasLineBreak(needText), `need ${show(name)}`, 'text must be one line of 1 to 200 characters')
          file.needs[name] = needText
        }
      } catch (e) {
        if (!(e instanceof SchemaError)) throw e
        fail(`${e.message}; entry dropped`)
      }
    }
  }

  if (source === 'user') {
    const ids = new Set<string>()
    for (const [kind, key] of [['rule', 'rules'], ['note', 'notes']] as const) {
      const list = obj[key]
      if (list === undefined) continue
      if (!Array.isArray(list)) {
        fail(`${key}: must be a list; ignored`)
        continue
      }
      for (const [i, value] of list.entries()) {
        try {
          const label = `${kind} ${i + 1}`
          const entry = kind === 'rule' ? parseRuleEntry(value, label) : parseNoteEntry(value, label, Object.keys(file.needs))
          check(!ids.has(entry.id), label, `id ${show(entry.id)} is already used`)
          ids.add(entry.id)
          if (kind === 'rule') file.rules.push(entry as Rule)
          else file.notes.push(entry as Note)
        } catch (e) {
          if (!(e instanceof SchemaError)) throw e
          fail(`${e.message}; entry dropped`)
        }
      }
    }
  }
  return file
}

/**
 * Reads the user file and the project file (either may be absent). Each file is
 * validated on its own: an invalid entry drops only that entry. The project file
 * is untrusted: it can only add skills and needs under names the user file does
 * not use, and cannot set `mode` or `trustProjects`. Its skills carry
 * `from: 'project'`.
 */
export function parseConfig(
  userText: string | undefined,
  projectText: string | undefined,
): { config: Config; errors: string[] } {
  const errors: string[] = []
  const config: Config = { mode: 'observe', skills: {}, needs: {}, trustProjects: [], rules: [], notes: [], learn: { skills: true } }

  const read = (source: Origin, text: string | undefined): FileConfig | undefined => {
    if (text === undefined) return undefined
    try {
      return parseFile(text, source, errors)
    } catch (e) {
      if (!(e instanceof SchemaError)) throw e
      errors.push(`${source} config skipped: ${e.message}`)
      return undefined
    }
  }
  const user = read('user', userText)
  const project = read('project', projectText)

  const dropUnknownNeed = (file: FileConfig, source: Origin, needs: Set<string>): void => {
    for (const [name, rule] of Object.entries(file.skills)) {
      if (rule.need !== undefined && !needs.has(rule.need)) {
        errors.push(`${source} config: skill ${show(name)} names unknown need ${show(rule.need)}; entry dropped`)
        delete file.skills[name]
      }
    }
  }

  if (user) {
    if (user.mode !== undefined) config.mode = user.mode
    if (user.trustProjects) config.trustProjects = user.trustProjects
    if (user.learn) config.learn = user.learn
    config.rules = user.rules
    config.notes = user.notes
    config.userNeeds = Object.keys(user.needs)
    dropUnknownNeed(user, 'user', new Set(Object.keys(user.needs)))
    Object.assign(config.skills, user.skills)
    Object.assign(config.needs, user.needs)
  }
  if (project) {
    const userSkills = new Set(user?.skillKeys)
    const userNeeds = new Set(user?.needKeys)
    for (const name of Object.keys(project.skills)) {
      if (userSkills.has(name)) {
        errors.push(`project config: skill ${show(name)} is already defined in the user config; entry ignored`)
        delete project.skills[name]
      }
    }
    for (const name of Object.keys(project.needs)) {
      if (userNeeds.has(name)) {
        errors.push(`project config: need ${show(name)} is already defined in the user config; entry ignored`)
        delete project.needs[name]
      }
    }
    dropUnknownNeed(project, 'project', new Set([...Object.keys(config.needs), ...Object.keys(project.needs)]))
    Object.assign(config.skills, project.skills)
    Object.assign(config.needs, project.needs)
  }
  return { config, errors }
}

// --- Glob matching: `*`, `**`, `?` only, no regular expressions. ---

type Token =
  | { t: 'lit'; c: string }
  | { t: 'one' } // any one character
  | { t: 'oneNoSlash' }
  | { t: 'run' } // any characters
  | { t: 'runNoSlash' }
  | { t: 'dirs' } // "**/": nothing, or anything ending in "/"

function compile(glob: string, segments: boolean): Token[] {
  const out: Token[] = []
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i]!
    if (c === '*') {
      let j = i
      while (glob[j + 1] === '*') j++
      const double = j > i
      if (!segments) out.push({ t: 'run' })
      else if (!double) out.push({ t: 'runNoSlash' })
      else if (glob[j + 1] === '/' && (i === 0 || glob[i - 1] === '/')) {
        out.push({ t: 'dirs' })
        j++
      } else out.push({ t: 'run' })
      i = j
    } else if (c === '?') {
      out.push(segments ? { t: 'oneNoSlash' } : { t: 'one' })
    } else {
      out.push({ t: 'lit', c })
    }
  }
  return out
}

/** Walks the tokens once over the text, keeping the set of reachable positions: O(tokens x length). */
function run(tokens: Token[], s: string): boolean {
  const n = s.length
  let cur = new Array<boolean>(n + 1).fill(false)
  cur[0] = true
  for (const tok of tokens) {
    const next = new Array<boolean>(n + 1).fill(false)
    if (tok.t === 'lit' || tok.t === 'one' || tok.t === 'oneNoSlash') {
      for (let j = 0; j < n; j++) {
        if (!cur[j]) continue
        const ch = s[j]!
        if (tok.t === 'lit' ? ch === tok.c : tok.t === 'one' || ch !== '/') next[j + 1] = true
      }
    } else if (tok.t === 'dirs') {
      let seen = false
      for (let j = 0; j <= n; j++) {
        if (j > 0 && s[j - 1] === '/' && seen) next[j] = true
        if (cur[j]) {
          next[j] = true
          seen = true
        }
      }
    } else {
      for (let j = 0; j <= n; j++) {
        next[j] = cur[j] || (j > 0 && next[j - 1]! && (tok.t === 'run' || s[j - 1] !== '/'))
      }
    }
    cur = next
    if (!cur.includes(true)) return false
  }
  return cur[n]!
}

/** Resolves `.`, `..` and repeated slashes so a path cannot step out of the root by spelling. */
function normalizePath(p: string): string {
  const abs = p.startsWith('/')
  const parts: string[] = []
  for (const seg of p.split('/')) {
    if (seg === '' || seg === '.') continue
    if (seg === '..') {
      if (parts.length > 0 && parts[parts.length - 1] !== '..') parts.pop()
      else if (!abs) parts.push('..')
    } else parts.push(seg)
  }
  return (abs ? '/' : '') + parts.join('/')
}

function globMatchesPath(glob: string, path: string, root: string | undefined): boolean {
  let g = glob
  while (g.startsWith('./')) g = g.slice(2)
  let p = normalizePath(path)
  if (!g.startsWith('/') && !g.startsWith('**/') && root !== undefined) {
    const r = normalizePath(root)
    const prefix = r.endsWith('/') ? r : `${r}/`
    if (!p.startsWith(prefix)) return false
    p = p.slice(prefix.length)
  }
  return run(compile(g, true), p)
}

/** True when `tool` is listed and, if `paths` is set, `path` matches one of its globs (`**`, `*`, `?`). */
export function matches(m: Match, tool: string, path: string | undefined, root?: string): boolean {
  if (!m.tools.includes(tool)) return false
  if (m.paths === undefined) return true
  if (path === undefined) return false
  return m.paths.some((glob) => globMatchesPath(glob, path, root))
}

/** Matches a duty's `evidence.command` glob against a command line. Here `*` and `?` also match `/`. */
export function matchesCommand(glob: string, command: string): boolean {
  return run(compile(glob, false), command)
}
