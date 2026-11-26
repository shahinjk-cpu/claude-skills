import { matches, matchesCommand, normRoot } from './config.ts'
import type { Session } from './decide.ts'
import type { Config, Match, Note, Rule, SkillName } from './types.ts'

/** The most characters of notes the system prompt section carries. */
export const NOTE_CAP = 2000

/** `root` is the main repository root (what `where` names); `tree` is the session's own working tree, which globs are relative to. */
export type ToolEvent = { tool: string; path?: string; command?: string; skill?: string; present?: string[]; root?: string; tree?: string }
export type RuleKind = 'skill' | 'field' | 'after'

export const ruleKind = (r: Rule): RuleKind => (r.after !== undefined ? 'after' : r.skill !== undefined ? 'skill' : 'field')

const matchText = (m: Match): string => `${m.tools.join(' or ')}${m.paths ? ` (${m.paths.join(', ')})` : ''}`

/** The exact short form a dialog and a denial show. */
export function describeRule(r: Rule): string {
  switch (ruleKind(r)) {
    case 'skill':
      return `before ${matchText(r.before!)}: skill ${r.skill} loaded`
    case 'field':
      return `before ${matchText(r.before!)}: field ${r.field} set`
    case 'after':
      return `after ${matchText(r.after!)}: ${r.evidence!.tool}${r.evidence!.command === undefined ? '' : ` ${r.evidence!.command}`}`
  }
}

export function describeNote(n: Note): string {
  return `${n.need === undefined ? '' : `(when ${n.need}) `}${n.text}`
}

/** A rule or note applies everywhere, or in the project whose main repository root it names. */
export const appliesHere = (entry: { where?: string }, root: string | undefined): boolean => entry.where === undefined || (root !== undefined && normRoot(entry.where) === normRoot(root))

/** Every skill a rule names, so the ledger has an entry for it. */
export function ruleSkillNames(config: Config): SkillName[] {
  return [...new Set(config.rules.flatMap((r) => (r.skill === undefined ? [] : [r.skill])))]
}

export type RuleResult = {
  /** One text per broken rule. */
  reasons: string[]
  /** After rules this call opens (the caller opens them unless the call is denied). */
  opened: string[]
  /** Open after rules this call's evidence closes. */
  closed: string[]
  /** Rules that denied now: the retry passes. */
  denied: string[]
  /** Field rules whose retry just passed. */
  released: string[]
  /** Skills of skill rules that matched: needed for the rest of the session. */
  fired: SkillName[]
}

const MISSING_STATE = new Set(['loaded', 'unavailable', 'not installed here'])

/** Checks every rule against one main-session tool call. Pure: the caller applies the result. */
export function checkRules(config: Config, s: Session, e: ToolEvent): RuleResult {
  const out: RuleResult = { reasons: [], opened: [], closed: [], denied: [], released: [], fired: [] }
  const base = e.tree ?? e.root
  for (const rule of config.rules) {
    if (!appliesHere(rule, e.root)) continue
    const label = `Souffleur rule ${rule.id} (${describeRule(rule)})`
    switch (ruleKind(rule)) {
      case 'skill': {
        if (!matches(rule.before!, e.tool, e.path, base)) break
        if (e.tool === 'Skill' && e.skill === rule.skill) break // the call that loads the skill is the way out
        const state = s.ledger[rule.skill!]?.state
        if (state === undefined || MISSING_STATE.has(state)) break
        out.fired.push(rule.skill!)
        out.reasons.push(`${label}: load ${rule.skill} with the Skill tool first, then retry.`)
        break
      }
      case 'field': {
        if (!matches(rule.before!, e.tool, e.path, base)) break
        const retry = s.fieldDenied.includes(rule.id)
        if ((e.present ?? []).includes(rule.field!) || retry) {
          if (retry) out.released.push(rule.id)
        } else {
          out.denied.push(rule.id)
          out.reasons.push(`${label}: add "${rule.field}" to the call, then retry.`)
        }
        break
      }
      case 'after': {
        const open = s.openRules.find((o) => o.id === rule.id)
        const ev = rule.evidence!
        if (open && ev.tool === e.tool && (ev.command === undefined || matchesCommand(ev.command, e.command ?? ''))) {
          out.closed.push(rule.id)
        } else if (matches(rule.after!, e.tool, e.path, base)) {
          if (!open) out.opened.push(rule.id)
          else if (!open.denied) {
            out.denied.push(rule.id)
            out.reasons.push(`${label}: do this first: ${ev.tool}${ev.command === undefined ? '' : ` matching ${ev.command}`}. Then retry.`)
          }
        }
        break
      }
    }
  }
  return out
}

/** Notes without `need` for the system prompt section, in file order, up to the cap; the rest are left out. */
export function sectionNotes(config: Config, root: string | undefined): { text: string; leftOut: Note[] } {
  const here = config.notes.filter((n) => n.need === undefined && appliesHere(n, root))
  const kept: Note[] = []
  let used = 0
  let full = false
  const leftOut: Note[] = []
  for (const n of here) {
    if (!full && used + n.text.length <= NOTE_CAP) {
      kept.push(n)
      used += n.text.length
    } else {
      full = true
      leftOut.push(n)
    }
  }
  return { text: kept.length ? `Standing notes from the user:\n${kept.map((n) => `- ${n.text}`).join('\n')}` : '', leftOut }
}

/** The most characters of notes one context block carries. */
export const CONTEXT_CAP = 2000

/**
 * Notes the next prompt's context carries: confirmed ones once, need notes on the first match and after each compaction.
 * Up to the cap; `leftOut` waits for a later prompt and is listed in the status.
 */
export function contextNotes(config: Config, s: Session, root: string | undefined): { kept: Note[]; leftOut: Note[] } {
  const due = config.notes.filter((n) => {
    if (!appliesHere(n, root)) return false
    if (n.need !== undefined) return n.need in s.needs && !s.notesSent.includes(n.id)
    return s.freshNotes.includes(n.id)
  })
  const kept: Note[] = []
  const leftOut: Note[] = []
  let used = 0
  for (const n of due) {
    if (leftOut.length === 0 && used + n.text.length <= CONTEXT_CAP) {
      kept.push(n)
      used += n.text.length
    } else leftOut.push(n)
  }
  return { kept, leftOut }
}
