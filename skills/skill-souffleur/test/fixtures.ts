import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { CoreEvent } from '../src/core/decide.ts'

export const EVENT_NAMES = [
  'session.start',
  'prompt.submit',
  'tool.call',
  'skill.prompt',
  'command.run',
  'session.compact.before',
  'session.compact.after',
] as const

export type EventName = (typeof EVENT_NAMES)[number]

/** Where a prompt came from, for example `{ kind: 'sdk' }` or `{ kind: 'peer' }`. */
export type Origin = { kind: string }

export type SessionStartInput = {
  cwd: string
  surface: string | null
  isInteractive: boolean
  version: { version: string; base: string }
}

/** `text` is cut at 80 characters. `command` is set when the user typed `/name`. */
export type PromptSubmitInput = {
  text: string
  origin: Origin
  isMeta?: boolean
  command?: { name: string; args: string }
}

/** Tool arguments sit flat beside `tool`. `agentId` is set for a subagent's calls. */
export type ToolCallInput = {
  tool: string
  tool_use_id: string
  agentId?: string
  [argument: string]: unknown
}

/** The skill text is reduced to its length and its first and last characters. */
export type SkillPromptInput = { skill: string; len: number; head: string; tail: string }

export type CommandRunInput = { command: string; args: string }

/** `session.compact.before` and `.after` are the two halves of one hook. */
export type CompactInput = { trigger: string }

export type InputByEvent = {
  'session.start': SessionStartInput
  'prompt.submit': PromptSubmitInput
  'tool.call': ToolCallInput
  'skill.prompt': SkillPromptInput
  'command.run': CommandRunInput
  'session.compact.before': CompactInput
  'session.compact.after': CompactInput
}

export type FixtureEvent = {
  [E in EventName]: { event: E; at: number; session: string; input: InputByEvent[E] }
}[EventName]

export type FixtureFile = { claudeCode: string; events: FixtureEvent[] }

export function loadFixtureFile(name: string): FixtureFile {
  const path = join(import.meta.dirname, 'fixtures', `${name}.json`)
  return JSON.parse(readFileSync(path, 'utf8')) as FixtureFile
}

export function loadFixture(name: string): FixtureEvent[] {
  return loadFixtureFile(name).events
}

const USER_ORIGINS = ['composer', 'bridge', 'sdk']

/** Maps recorded events to core events. Classification is not recorded, so a prompt matches no need. */
export function toCoreEvents(f: FixtureEvent[]): CoreEvent[] {
  const out: CoreEvent[] = []
  let started = false
  for (const e of f) {
    const now = e.at
    switch (e.event) {
      case 'session.start':
        out.push({ type: 'start', now, start: started ? 'resume' : 'startup', version: e.input.version.version })
        started = true
        break
      case 'skill.prompt':
        out.push({ type: 'skill', now, skill: e.input.skill })
        break
      case 'session.compact.before':
        out.push({ type: 'compact', now, phase: 'before', trigger: e.input.trigger })
        break
      case 'session.compact.after':
        out.push({ type: 'compact', now, phase: 'after', trigger: e.input.trigger })
        break
      case 'prompt.submit': {
        const i = e.input
        const fromUser = i.command === undefined && !i.isMeta && USER_ORIGINS.includes(i.origin.kind)
        out.push({ type: 'prompt', now, text: i.text, fromUser, matched: [] })
        break
      }
      case 'tool.call': {
        const i = e.input
        const str = (v: unknown) => (typeof v === 'string' ? v : undefined)
        const ev: Extract<CoreEvent, { type: 'tool' }> = { type: 'tool', now, tool: i.tool }
        const path = str(i.file_path)
        const command = str(i.command)
        const brief = str(i.prompt)
        const skill = str(i.skill)
        const model = str(i.model)
        if (path !== undefined) ev.path = path
        if (command !== undefined) ev.command = command
        if (brief !== undefined) ev.brief = brief
        if (skill !== undefined) ev.skill = skill
        if (model !== undefined) ev.model = model
        if (i.agentId !== undefined) ev.agentId = i.agentId
        out.push(ev)
        break
      }
      case 'command.run':
        out.push(e.input.command === 'souffleur'
          ? { type: 'command', now, args: e.input.args }
          : { type: 'typed', now, name: e.input.command })
        break
    }
  }
  return out
}
