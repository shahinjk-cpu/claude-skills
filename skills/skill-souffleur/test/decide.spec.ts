import { test } from 'node:test'
import assert from 'node:assert/strict'
import { decide, initSession } from '../src/core/decide.ts'
import type { Action, CoreEvent, Session } from '../src/core/decide.ts'
import type { Config } from '../src/core/types.ts'
import { loadFixture, toCoreEvents } from './fixtures.ts'

const base: Config = {
  mode: 'enforce',
  needs: { prose: 'Writing text people read.', ui: 'Building a screen.' },
  trustProjects: [], rules: [], notes: [], learn: { skills: true },
  skills: {
    'writing-guide': { need: 'prose', from: 'user' },
    'writing-check': { need: 'prose', from: 'user' },
    'ui-checklist': {
      need: 'ui',
      from: 'user',
      gate: { tools: ['Write', 'Edit'], paths: ['**/*.html'] },
      duty: {
        after: { tools: ['Write'], paths: ['**/*.html'] },
        evidence: { tool: 'Bash', command: '*ui-checklist*detect*' },
      },
    },
  },
}
const cfg = (patch: Partial<Config> = {}): Config => ({ ...base, ...patch })
const withAlways = cfg({ skills: { 'terse:terse-mode': { always: true, from: 'user' }, ...base.skills } })

let t = 0
const at = () => ++t
const prompt = (text = 'do it', matched: string[] = [], fromUser = true): CoreEvent => ({ type: 'prompt', now: at(), text, fromUser, matched })
const tool = (name: string, extra: Partial<Extract<CoreEvent, { type: 'tool' }>> = {}): CoreEvent => ({ type: 'tool', now: at(), tool: name, ...extra })
const loadSkill = (skill: string): CoreEvent => ({ type: 'skill', now: at(), skill })
const compact = (extra: Partial<Extract<CoreEvent, { type: 'compact' }>> = {}): CoreEvent => ({ type: 'compact', now: at(), phase: 'after', trigger: 'manual', ...extra })
const command = (args: string): CoreEvent => ({ type: 'command', now: at(), args })

/** Feeds events in order; returns the final session and the actions of each event. */
function run(config: Config, events: CoreEvent[], start?: Session): { s: Session; out: Action[][] } {
  let s = start ?? initSession(config, 'session-1', 0, 'clear')
  const out: Action[][] = []
  for (const e of events) {
    const r = decide(config, s, e)
    s = r.session
    out.push(r.actions)
  }
  return { s, out }
}
const one = (config: Config, events: CoreEvent[], start?: Session) => run(config, events, start).out.at(-1)!
const ctx = (a: Action[]) => a.filter((x) => x.kind === 'context').map((x) => (x as { text: string }).text).join('\n')
const denies = (a: Action[]) => a.filter((x) => x.kind === 'deny')

/** A session with ui-checklist needed and loaded. */
const uiLoaded = (config = base) => run(config, [prompt('screen', ['ui']), loadSkill('ui-checklist')]).s

test('fresh session asks for always skills on first user prompt', () => {
  const a = one(withAlways, [prompt()])
  assert.match(ctx(a), /terse:terse-mode/)
  assert.doesNotMatch(ctx(a), /writing-guide/)
})

test('nothing missing gives no actions', () => {
  const { s } = run(withAlways, [prompt(), loadSkill('terse:terse-mode')])
  assert.deepEqual(one(withAlways, [prompt()], s), [])
})

test('prompt not from user gives no actions', () => {
  const { s, out } = run(base, [prompt('hand-back', ['prose'], false)])
  assert.deepEqual(out[0], [])
  assert.deepEqual(s.needs, {})
})

test('matched need adds its skills to the request', () => {
  const { s, out } = run(withAlways, [prompt('write the docs and a guide for people who read them later', ['prose'])])
  assert.match(ctx(out[0]!), /terse:terse-mode, writing-guide, writing-check\./)
  assert.equal(s.needs.prose!.reason, 'need:prose from "write the docs and a guide for people wh"')
})

test('need stays active on a later unrelated prompt', () => {
  const { s } = run(base, [prompt('docs', ['prose']), prompt('thanks', [])])
  assert.ok('prose' in s.needs)
  assert.equal(s.ledger['writing-guide']!.state, 'restoring')
})

test('missing skill is asked twice, then not again and status says not seen after 2 requests', () => {
  const { s, out } = run(base, [prompt('docs', ['prose']), prompt('b'), prompt('c'), prompt('d')])
  assert.match(ctx(out[0]!), /writing-guide/)
  assert.match(ctx(out[1]!), /writing-guide/)
  assert.match(ctx(out[2]!), /^$|^((?!writing-guide).)*$/s)
  assert.deepEqual(out[3], [])
  assert.equal(s.ledger['writing-guide']!.state, 'unavailable')
  assert.equal(s.ledger['writing-guide']!.reason, 'not seen after 2 requests')
})

test('subagent skill load does not mark the main ledger loaded', () => {
  const config = cfg({ skills: { bigtest: { always: true, from: 'user' } } })
  const events = toCoreEvents(loadFixture('subagent'))
  const { s, out } = run(config, events)
  assert.equal(s.ledger.bigtest!.state, 'restoring')
  assert.match(ctx(out[1]!), /bigtest/)
  assert.equal(s.subagentsRunning, 1)
  const done = run(config, [{ type: 'agentDone', now: at() }], s)
  assert.equal(done.s.subagentsRunning, 0)
})

test('skill load while a subagent runs and without a main Skill call is ignored', () => {
  const { s } = run(base, [prompt('x', ['prose']), tool('Agent', { brief: 'skills: none' }), loadSkill('writing-guide')])
  assert.equal(s.ledger['writing-guide']!.state, 'restoring')
})

test('main Skill call while a subagent runs counts', () => {
  const { s } = run(base, [prompt('x', ['prose']), tool('Agent', { brief: 'skills: none' }), tool('Skill', { skill: 'writing-guide' }), loadSkill('writing-guide')])
  assert.equal(s.ledger['writing-guide']!.state, 'loaded')
  assert.deepEqual(s.mainSkillCalls, [])
})

test('typed /name counts for the main ledger', () => {
  const { s } = run(base, [prompt('x', ['prose']), tool('Agent', { brief: 'skills: none' }), { type: 'typed', now: at(), name: 'writing-guide' }, loadSkill('writing-guide')])
  assert.equal(s.ledger['writing-guide']!.state, 'loaded')
})

test('compaction mid-turn: next tool call gets toolContext once', () => {
  const { s } = run(withAlways, [prompt('x', ['prose']), loadSkill('terse:terse-mode'), loadSkill('writing-guide'), loadSkill('writing-check')])
  const r1 = run(withAlways, [compact(), tool('Read', { path: 'a.ts' }), tool('Read', { path: 'b.ts' })], s)
  assert.equal(r1.out[0]!.length, 0)
  assert.equal(r1.out[1]![0]!.kind, 'toolContext')
  assert.match((r1.out[1]![0] as { text: string }).text, /terse:terse-mode, writing-guide, writing-check/)
  assert.deepEqual(r1.out[2], [])
})

test('compaction then a prompt: no toolContext afterwards', () => {
  const { s } = run(withAlways, [prompt('x', ['prose']), loadSkill('terse:terse-mode'), compact(), prompt('next')])
  assert.deepEqual(one(withAlways, [tool('Read')], s), [])
})

test('precompute and skipped compactions do not stale', () => {
  const { s } = run(withAlways, [prompt(), loadSkill('terse:terse-mode')])
  const r = run(withAlways, [compact({ trigger: 'precompute' }), compact({ skipped: true }), compact({ phase: 'before' })], s)
  assert.equal(r.s.ledger['terse:terse-mode']!.state, 'loaded')
  assert.equal(r.s.compactedSincePrompt, false)
})

test('subagent compaction does not stale the main ledger', () => {
  const { s } = run(withAlways, [prompt(), loadSkill('terse:terse-mode')])
  const r = run(withAlways, [compact({ agentId: 'agent-1' })], s)
  assert.equal(r.s.ledger['terse:terse-mode']!.state, 'loaded')
})

test('subagent tool call is never gated', () => {
  const { s } = run(base, [prompt('screen', ['ui'])])
  assert.deepEqual(one(base, [tool('Write', { path: 'x.html', agentId: 'agent-1' })], s), [])
})

test('gate denies Write to x.html while ui-checklist is needed and stale, allows after load', () => {
  const s0 = run(base, [prompt('screen', ['ui']), loadSkill('ui-checklist'), compact()]).s
  assert.equal(s0.ledger['ui-checklist']!.state, 'stale')
  const denied = denies(one(base, [tool('Write', { path: 'x.html' })], s0))
  assert.equal(denied.length, 1)
  assert.match((denied[0] as { reason: string }).reason, /load ui-checklist with the Skill tool first, then retry\. .*\/souffleur pause/)
  const ok = run(base, [loadSkill('ui-checklist'), tool('Write', { path: 'x.html' })], s0)
  assert.deepEqual(ok.out[1], [])
  assert.deepEqual(denies(one(base, [tool('Write', { path: 'x.ts' })], s0)), [])
})

test('gate does nothing while the need is not active', () => {
  assert.deepEqual(one(base, [tool('Write', { path: 'x.html' })]), [])
})

test('paused session is not gated', () => {
  const { s } = run(base, [prompt('screen', ['ui']), command('pause')])
  assert.equal(s.paused, true)
  assert.deepEqual(one(base, [tool('Write', { path: 'x.html' })], s), [])
})

test('unavailable skill is not gated', () => {
  const { s } = run(base, [prompt('screen', ['ui']), prompt('2'), prompt('3')])
  assert.equal(s.ledger['ui-checklist']!.state, 'unavailable')
  assert.deepEqual(one(base, [tool('Write', { path: 'x.html' })], s), [])
})

test('untrusted project gate only records', () => {
  const config = cfg({ skills: { ...base.skills, 'ui-checklist': { ...base.skills['ui-checklist']!, from: 'project' } } })
  const s0 = run(config, [prompt('screen', ['ui'])]).s
  const r = run(config, [tool('Write', { path: 'x.html', root: '/project' })], s0)
  assert.deepEqual(r.out[0], [])
  assert.equal(r.s.observed.length, 1)
  assert.match(r.s.observed[0]!.reason, /ui-checklist/)
  const trusted = cfg({ ...config, trustProjects: ['/project'] })
  const t2 = run(trusted, [tool('Write', { path: 'x.html', root: '/project' })], s0)
  assert.equal(t2.out[0]![0]!.kind, 'deny')
  const noRoot = run(trusted, [tool('Write', { path: 'x.html' })], s0)
  assert.deepEqual(noRoot.out[0], [])
})

test('duty opens on Write x.html, denies next gated Write, closes on Bash ui-checklist detect', () => {
  const s0 = uiLoaded()
  const r = run(base, [
    tool('Write', { path: 'a.html' }),
    tool('Write', { path: 'b.html' }),
    tool('Bash', { command: 'run ui-checklist detect b.html' }),
    tool('Write', { path: 'c.html' }),
  ], s0)
  assert.deepEqual(r.out[0], [])
  assert.equal(r.out[1]![0]!.kind, 'deny')
  assert.match((r.out[1]![0] as { reason: string }).reason, /open duty for ui-checklist \(Write a\.html\)/)
  assert.deepEqual(r.out[2], [])
  assert.deepEqual(r.out[3], [])
  assert.equal(r.s.duties.length, 1)
  assert.equal(r.s.duties[0]!.by, 'Write c.html')
})

test('duty denies once, retry passes', () => {
  const r = run(base, [tool('Write', { path: 'a.html' }), tool('Write', { path: 'b.html' }), tool('Write', { path: 'b.html' })], uiLoaded())
  assert.equal(r.out[1]![0]!.kind, 'deny')
  assert.deepEqual(r.out[2], [])
  assert.equal(r.s.duties.length, 1)
})

test('open duty is listed in the next prompt context', () => {
  const r = run(base, [tool('Write', { path: 'a.html' }), prompt('next')], uiLoaded())
  assert.equal(ctx(r.out[1]!), 'Open duty: ui-checklist (Write a.html).')
})

test('pause stops gate, duty and brief denials', () => {
  const s0 = run(base, [prompt('screen', ['ui']), loadSkill('ui-checklist'), compact(), command('pause')]).s
  const r = run(base, [
    tool('Write', { path: 'a.html' }),
    tool('Write', { path: 'b.html' }),
    tool('Agent', { brief: 'no skills line' }),
  ], s0)
  assert.deepEqual(r.out.flatMap(denies), [])
  assert.deepEqual(r.s.observed, [])
})

test('Agent brief without skills line is denied once, retry passes', () => {
  const { s } = run(base, [prompt('screen', ['ui'])])
  const r = run(base, [tool('Agent', { brief: 'do the thing' }), tool('Agent', { brief: 'do the thing' }), tool('Agent', { brief: 'again' })], s)
  assert.equal(r.out[0]![0]!.kind, 'deny')
  assert.match((r.out[0]![0] as { reason: string }).reason, /Configured skills: .*ui-checklist.*Active needs: ui/)
  assert.deepEqual(r.out[1], [])
  assert.equal(r.out[2]![0]!.kind, 'deny')
})

test('Agent brief with "skills: none" passes', () => {
  const { s } = run(base, [prompt('screen', ['ui'])])
  assert.deepEqual(one(base, [tool('Agent', { brief: 'Fix typo.\nskills: none' })], s), [])
})

test('no active need: Agent brief is not checked', () => {
  assert.deepEqual(one(base, [tool('Agent', { brief: 'whatever' })]), [])
})

test('command need/drop/pause', () => {
  const r = run(base, [command('need ui'), command('drop ui'), command('pause')])
  assert.equal(r.out[0]![0]!.kind, 'reply')
  const on = run(base, [command('need ui')]).s
  assert.ok('ui' in on.needs)
  assert.deepEqual(run(base, [command('drop ui')], on).s.needs, {})
  assert.equal(r.s.paused, true)
})

test('command status replies with the status text', () => {
  const a = one(base, [command('')])
  assert.equal(a[0]!.kind, 'reply')
  assert.equal(one(base, [command('status')])[0]!.kind, 'reply')
})

test('unknown need name in command replies with known needs', () => {
  const a = one(base, [command('need nope')])
  assert.match((a[0] as { text: string }).text, /Known needs: prose, ui/)
  assert.match((one(base, [command('drop nope')])[0] as { text: string }).text, /Known needs: prose, ui/)
})

test('replay resume-then-compact ends with bigtest requested on the next prompt', () => {
  const config = cfg({ skills: { bigtest: { always: true, from: 'user' } } })
  const events = toCoreEvents(loadFixture('resume-then-compact-then-clear'))
  const cut = events.findIndex((e) => e.type === 'typed' && e.name === 'clear')
  const r = run(config, events.slice(0, cut))
  assert.equal(r.s.ledger.bigtest!.state, 'restoring')
  assert.match(ctx(r.out.at(-1)!), /invoke these skills .*: bigtest\./)
  const afterLoad = r.out.findIndex((_, i) => events[i]!.type === 'skill')
  assert.ok(afterLoad > 0)
})

test('observe mode: gate, duty and Agent-brief checks deny nothing and record would-deny reasons', () => {
  const config = cfg({ mode: 'observe' })
  const s0 = run(config, [prompt('screen', ['ui']), loadSkill('ui-checklist'), compact()]).s
  const r = run(config, [
    tool('Write', { path: 'a.html' }), // gate: stale
    loadSkill('ui-checklist'),
    tool('Write', { path: 'a.html' }), // opens duty
    tool('Write', { path: 'b.html' }), // duty
    tool('Agent', { brief: 'nothing' }), // brief
  ], s0)
  assert.deepEqual(r.out.flatMap(denies), [])
  assert.equal(r.s.observed.length, 3)
  assert.match(r.s.observed[0]!.reason, /load ui-checklist/)
  assert.match(r.s.observed[1]!.reason, /open duty/)
  assert.match(r.s.observed[2]!.reason, /skills:/)
})

test('observe mode still sends the restore context', () => {
  const a = one(cfg({ mode: 'observe', skills: withAlways.skills }), [prompt()])
  assert.match(ctx(a), /terse:terse-mode/)
})

test('observed and errors keep the last 20', () => {
  const config = cfg({ mode: 'observe' })
  const s0 = run(config, [prompt('screen', ['ui'])]).s
  const events: CoreEvent[] = []
  for (let i = 0; i < 25; i++) events.push(tool('Write', { path: `${i}.html` }), { type: 'error', now: at(), where: 'w', message: `m${i}` })
  const r = run(config, events, s0)
  assert.equal(r.s.observed.length, 20)
  assert.equal(r.s.errors.length, 20)
  assert.equal(r.s.errors.at(-1), 'w: m24')
})

test('resume keeps the ledger, clear starts a fresh session', () => {
  const { s } = run(withAlways, [prompt(), loadSkill('terse:terse-mode')])
  const resumed = decide(withAlways, s, { type: 'start', now: at(), start: 'resume', version: '2.1.332' }).session
  assert.equal(resumed.ledger['terse:terse-mode']!.state, 'loaded')
  assert.equal(resumed.version, '2.1.332')
  const cleared = decide(withAlways, s, { type: 'start', now: at(), start: 'clear' }).session
  assert.equal(cleared.ledger['terse:terse-mode']!.state, 'absent')
  assert.equal(cleared.id, s.id)
})

test('session survives JSON round trip', () => {
  const events: CoreEvent[] = [
    { type: 'start', now: at(), start: 'startup', version: '2.1.332' },
    prompt('screen', ['ui']),
    loadSkill('ui-checklist'),
    tool('Agent', { brief: 'skills: none' }),
    tool('Write', { path: 'a.html' }),
    compact(),
    command('pause'),
    { type: 'error', now: at(), where: 'w', message: 'm' },
  ]
  const { s } = run(cfg({ mode: 'observe' }), events)
  assert.deepEqual(JSON.parse(JSON.stringify(s)), s)
  const again = decide(base, JSON.parse(JSON.stringify(s)) as Session, prompt('more'))
  assert.deepEqual(JSON.parse(JSON.stringify(again.session)), again.session)
})

test('a restore after compaction says the engine note about earlier skills does not apply', () => {
  const config = cfg({ skills: { bigtest: { always: true, from: 'user' } } })
  const r = run(config, [loadSkill('bigtest'), compact(), prompt('next')])
  assert.match(ctx(r.out.at(-1)!), /invoke these skills .*: bigtest\. .*must not be run again does not apply/)
  const first = run(config, [prompt('first')])
  assert.doesNotMatch(ctx(first.out.at(-1)!), /does not apply/)
})

test('a skill not installed here is neither requested nor gated', () => {
  const c = cfg({ skills: { ...base.skills, 'terse:terse-mode': { always: true, from: 'user' } } })
  const { s, out } = run(c, [{ type: 'installed', now: at(), names: ['writing-guide', 'writing-check'] }, prompt('make a page', ['ui']), tool('Write', { path: 'x.html' })])
  assert.equal(s.ledger['ui-checklist']!.state, 'not installed here')
  assert.equal(s.ledger['terse:terse-mode']!.state, 'not installed here')
  assert.equal(s.ledger['ui-checklist']!.requests, 0)
  const text = JSON.stringify(out)
  assert.doesNotMatch(text, /ui-checklist|terse-mode/)
  assert.equal(out[2]!.some((a) => a.kind === 'deny'), false)
})

test('a config event adds new skills as absent, drops removed ones and swaps config errors', () => {
  const c = cfg()
  const start = initSession(c, 'session-1', 0, 'clear')
  const withErr = { ...start, errors: ['config: old', 'hook: kept'] }
  const next = cfg({ skills: { 'writing-guide': base.skills['writing-guide']!, 'pdf-tool': { need: 'prose', from: 'user' } } })
  const { s } = run(next, [{ type: 'config', now: at(), errors: [] }], withErr)
  assert.deepEqual(Object.keys(s.ledger).sort(), ['pdf-tool', 'writing-guide'])
  assert.equal(s.ledger['pdf-tool']!.state, 'absent')
  assert.deepEqual(s.errors, ['hook: kept'])
})

test('a skill not installed here opens no duty and is left out of the Agent brief list', () => {
  const c = cfg({ mode: 'observe' })
  const gone = [{ type: 'installed', now: at(), names: ['writing-guide'] } as CoreEvent]
  const { s, out } = run(c, [...gone, prompt('x', ['ui']), tool('Write', { path: 'x.html' }), tool('Agent', { brief: 'no skills line' })])
  assert.deepEqual(s.duties, [])
  const denied = JSON.stringify(out)
  assert.doesNotMatch(denied, /ui-checklist/)
  const enforced = run(cfg(), [...gone, prompt('x', ['prose']), tool('Agent', { brief: 'no skills line' })])
  const deny = enforced.out[2]!.find((a) => a.kind === 'deny') as { reason: string } | undefined
  assert.ok(deny)
  assert.doesNotMatch(deny.reason, /ui-checklist/)
  assert.match(deny.reason, /writing-guide/)
})

test('a config event drops needs the config no longer has and duties of removed skills', () => {
  const c = cfg()
  const start = {
    ...initSession(c, 'session-1', 0, 'clear'),
    needs: { ui: { since: 1, reason: 'x' }, gone: { since: 1, reason: 'y' } },
    duties: [{ skill: 'ui-checklist', openedAt: 1, by: 'Write', denied: false }, { skill: 'removed', openedAt: 1, by: 'Write', denied: false }],
  }
  const { s } = run(c, [{ type: 'config', now: at(), errors: [] }], start)
  assert.deepEqual(Object.keys(s.needs), ['ui'])
  assert.deepEqual(s.duties.map((d) => d.skill), ['ui-checklist'])
})
