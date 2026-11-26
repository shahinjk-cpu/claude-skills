import type { Session } from './decide.ts'
import { contextNotes, sectionNotes } from './rules.ts'
import type { Config, Mode } from './types.ts'
import { versionNotice } from './version.ts'

const cell = (text: string) => text.replace(/\\/g, '\\\\').replace(/\|/g, '\\|').replace(/\r\n|\r|\n/g, ' ')

/** `HH:MM` in UTC. */
const clock = (ms: number) => new Date(ms).toISOString().slice(11, 16)

/** The `/souffleur` reply: mode, the version notice when Claude Code is newer than the verified one, one row per ledger entry, then non-empty sections, then the Claude Code version. */
export function renderTable(config: Config, s: Session, now: number, root?: string): string {
  void now
  const lines = [`Mode: ${config.mode}${s.paused ? ' (paused)' : ''}`]
  const notice = versionNotice(s.version)
  if (notice) lines.push(notice)
  lines.push('')
  lines.push('| Skill | State | Since | Reason |', '| --- | --- | --- | --- |')
  for (const [name, e] of Object.entries(s.ledger)) {
    lines.push(`| ${cell(name)} | ${e.state} | ${clock(e.since)} | ${cell(e.reason)} |`)
  }
  const duties = s.duties.filter((d) => s.ledger[d.skill]?.state !== 'not installed here').map((d) => `- ${d.skill} (${d.by})`)
  if (duties.length) lines.push('', 'Open duties:', ...duties)
  const needs = Object.entries(s.needs).map(([name, n]) => `- ${name}: ${n.reason}`)
  if (needs.length) lines.push('', 'Active needs:', ...needs)
  const denied = s.observed.map((o) => `- ${clock(o.at)} ${o.reason}`)
  if (denied.length) lines.push('', 'Would have denied:', ...denied)
  if (s.proposals.length) lines.push('', `Open proposals (${s.proposals.length}), /souffleur review asks about them:`, ...s.proposals.map((p) => `- ${p.entry.id}`))
  const leftOut = sectionNotes(config, root).leftOut
  if (leftOut.length) lines.push('', `Notes left out of the system prompt (2,000 character limit): ${leftOut.map((n) => n.id).join(', ')}`)
  const due = contextNotes(config, s, root)
  const waiting = [...due.kept, ...due.leftOut]
  if (waiting.length) lines.push('', `Notes waiting for a later prompt (a context block holds 2,000 characters): ${waiting.map((n) => n.id).join(', ')}`)
  if (config.rules.length || config.notes.length) lines.push('', `Rules: ${config.rules.length}, notes: ${config.notes.length}`)
  if (s.errors.length) lines.push('', 'Errors:', ...s.errors.map((err) => `- ${err}`))
  if (s.version !== undefined) lines.push('', `Claude Code ${s.version}`)
  return lines.join('\n')
}

/** Short summary for the status line; undefined when no skill is configured. */
export function statusLine(s: Session, mode: Mode, notesLeftOut = 0): string | undefined {
  if (s.errors.length) return 'degraded, see /souffleur'
  const counts = { loaded: 0, restoring: 0, stale: 0, unavailable: 0, 'not installed here': 0 }
  for (const e of Object.values(s.ledger)) {
    if (e.state in counts) counts[e.state as keyof typeof counts] += 1
  }
  if (Object.keys(s.ledger).length === 0 && s.proposals.length === 0 && notesLeftOut === 0) return undefined
  const prefix = mode === 'observe' ? 'observe ·' : ''
  const parts = [`${counts.loaded} loaded`]
  if (counts.restoring) parts.push(`${counts.restoring} restoring`)
  if (counts.stale) parts.push(`${counts.stale} stale`)
  if (counts.unavailable) parts.push(`${counts.unavailable} unavailable`)
  if (counts['not installed here']) parts.push(`${counts['not installed here']} not installed here`)
  if (s.proposals.length) parts.push(`${s.proposals.length} to review`)
  if (notesLeftOut) parts.push(`${notesLeftOut} ${notesLeftOut === 1 ? 'note' : 'notes'} over the limit`)
  return prefix ? `${prefix} ${parts.join(', ')}` : parts.join(', ')
}
