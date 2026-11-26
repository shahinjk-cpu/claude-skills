import { test } from 'node:test'
import assert from 'node:assert/strict'
import { compacted, initLedger, markInstalled, requested, skillLoaded, syncLedger } from '../src/core/ledger.ts'
import type { Config } from '../src/core/types.ts'
import { loadFixture } from './fixtures.ts'

const config: Config = {
  mode: 'observe',
  skills: {
    inj: { startup: 'injected', from: 'user' },
    plain: { always: true, from: 'user' },
  },
  needs: {},
  trustProjects: [], rules: [], notes: [], learn: { skills: true },
}

test('injected skill is loaded at startup and absent after clear', () => {
  const startup = initLedger(config, 100, 'startup')
  assert.equal(startup.inj.state, 'loaded')
  assert.equal(startup.inj.reason, 'injected at startup')
  assert.equal(startup.inj.since, 100)
  assert.equal(startup.plain.state, 'absent')

  const clear = initLedger(config, 100, 'clear')
  assert.equal(clear.inj.state, 'absent')
  assert.equal(clear.inj.reason, '')
  assert.equal(clear.inj.requests, 0)
})

test('loading a configured skill marks it loaded with reason', () => {
  const l = initLedger(config, 100, 'startup')
  const next = skillLoaded(l, 'plain', 200, 'skill.prompt')
  assert.deepEqual(next.plain, { state: 'loaded', since: 200, reason: 'skill.prompt', requests: 0 })
})

test('unknown skill load is ignored', () => {
  const l = initLedger(config, 100, 'startup')
  assert.deepEqual(skillLoaded(l, 'nope', 200, 'skill.prompt'), l)
})

test('compaction turns loaded into stale, absent stays absent', () => {
  const l = skillLoaded(initLedger(config, 100, 'clear'), 'plain', 200, 'skill.prompt')
  const next = compacted(l, 300)
  assert.deepEqual(next.plain, {
    state: 'stale',
    since: 300,
    reason: 'skill.prompt',
    lastCompactAt: 300,
    requests: 0,
  })
  assert.deepEqual(next.inj, l.inj)
})

test('two compactions in a row keep stale and stamp the later time', () => {
  const l = skillLoaded(initLedger(config, 100, 'clear'), 'plain', 200, 'skill.prompt')
  const next = compacted(compacted(l, 300), 400)
  assert.equal(next.plain.state, 'stale')
  assert.equal(next.plain.lastCompactAt, 400)
  assert.equal(next.plain.since, 300)
})

test('compaction during restoring keeps restoring and its request count', () => {
  const l = requested(skillLoaded(initLedger(config, 100, 'clear'), 'plain', 200, 'skill.prompt'), ['plain'], 250)
  assert.equal(l.plain.state, 'restoring')
  assert.equal(l.plain.requests, 1)
  const next = compacted(l, 300)
  assert.equal(next.plain.state, 'restoring')
  assert.equal(next.plain.requests, 1)
  assert.equal(next.plain.lastCompactAt, 300)
})

test('loading after stale resets requests to 0', () => {
  const stale = compacted(skillLoaded(initLedger(config, 100, 'clear'), 'plain', 200, 'skill.prompt'), 300)
  const next = skillLoaded(stale, 'plain', 400, 'skill.prompt')
  assert.equal(next.plain.state, 'loaded')
  assert.equal(next.plain.requests, 0)
  assert.equal(next.plain.since, 400)
})

test('third request turns restoring into unavailable', () => {
  let l = skillLoaded(initLedger(config, 100, 'clear'), 'plain', 200, 'skill.prompt')
  l = requested(l, ['plain'], 210)
  assert.equal(l.plain.state, 'restoring')
  assert.equal(l.plain.requests, 1)
  l = requested(l, ['plain'], 220)
  assert.equal(l.plain.state, 'restoring')
  assert.equal(l.plain.requests, 2)
  l = requested(l, ['plain'], 230)
  assert.equal(l.plain.state, 'unavailable')
  assert.equal(l.plain.reason, 'not seen after 2 requests')
})

test('loading an unavailable skill makes it loaded', () => {
  let l = skillLoaded(initLedger(config, 100, 'clear'), 'plain', 200, 'skill.prompt')
  l = requested(requested(requested(l, ['plain'], 210), ['plain'], 220), ['plain'], 230)
  assert.equal(l.plain.state, 'unavailable')
  const next = skillLoaded(l, 'plain', 240, 'skill.prompt')
  assert.equal(next.plain.state, 'loaded')
  assert.equal(next.plain.requests, 0)
  assert.equal(next.plain.since, 240)
})

test('extra names get entries', () => {
  const l = initLedger(config, 100, 'startup', ['rules-only'])
  assert.deepEqual(l['rules-only'], { state: 'absent', since: 100, reason: '', requests: 0 })
})

test('inputs are not mutated', () => {
  const l = initLedger(config, 100, 'startup', ['extra'])
  const before = structuredClone(l)
  const configBefore = structuredClone(config)
  const loaded = skillLoaded(l, 'plain', 200, 'skill.prompt')
  const stale = compacted(loaded, 300)
  const restoring = requested(stale, ['plain', 'extra'], 400)
  compacted(restoring, 500)
  requested(requested(restoring, ['plain'], 410), ['plain'], 420)
  assert.deepEqual(l, before)
  assert.deepEqual(config, configBefore)
})

test('replays compact-in-process.json: bigtest ends stale', () => {
  const bigConfig: Config = {
    mode: 'observe',
    skills: { bigtest: { always: true, from: 'user' } },
    needs: {},
    trustProjects: [], rules: [], notes: [], learn: { skills: true },
  }
  let l = initLedger(bigConfig, 0, 'startup')
  for (const e of loadFixture('compact-in-process')) {
    if (e.event === 'skill.prompt') {
      const input = e.input as { skill: string }
      l = skillLoaded(l, input.skill, e.at, 'skill.prompt')
    }
    if (e.event === 'session.compact.after') l = compacted(l, e.at)
  }
  assert.equal(l.bigtest.state, 'stale')
  assert.equal(l.bigtest.lastCompactAt, 73459)
})

test('syncLedger adds new skills as absent and drops removed ones', () => {
  let l = initLedger(config, 100, 'clear')
  l = skillLoaded(l, 'plain', 110, 'skill.prompt')
  const next: Config = { ...config, skills: { plain: config.skills.plain!, fresh: { need: 'ui', from: 'user' } } }
  const synced = syncLedger(l, next, 200)
  assert.deepEqual(Object.keys(synced).sort(), ['fresh', 'plain'])
  assert.equal(synced.fresh.state, 'absent')
  assert.equal(synced.fresh.since, 200)
  assert.equal(synced.plain.state, 'loaded')
  assert.equal(synced.plain.since, 110)
  assert.equal('inj' in synced, false)
})

test('markInstalled sets skills missing from the list to not installed here and back', () => {
  let l = initLedger(config, 100, 'clear')
  l = markInstalled(l, ['plain'], 150)
  assert.equal(l.inj.state, 'not installed here')
  assert.equal(l.plain.state, 'absent')
  l = markInstalled(l, ['plain', 'inj'], 160)
  assert.equal(l.inj.state, 'absent')
})

test('markInstalled treats an empty list as unknown and never touches a loaded skill', () => {
  let l = initLedger(config, 100, 'startup')
  assert.equal(markInstalled(l, [], 150), l)
  l = skillLoaded(l, 'plain', 120, 'skill.prompt')
  l = markInstalled(l, ['other'], 150)
  assert.equal(l.plain.state, 'loaded')
})

test('markInstalled matches a bare name with a plugin name either way, but not two different plugins', () => {
  const c: Config = { mode: 'observe', needs: {}, trustProjects: [], rules: [], notes: [], learn: { skills: true }, skills: { plan: { always: true, from: 'user' }, 'flow:check': { always: true, from: 'user' }, 'a:thing': { always: true, from: 'user' } } }
  const l = markInstalled(initLedger(c, 0, 'clear'), ['flow:plan', 'check', 'b:thing'], 5)
  assert.equal(l.plan.state, 'absent')
  assert.equal(l['flow:check'].state, 'absent')
  assert.equal(l['a:thing'].state, 'not installed here')
})

test('markInstalled also moves a skill injected at startup that the list lacks', () => {
  const l = markInstalled(initLedger(config, 0, 'startup'), ['plain'], 5)
  assert.equal(l.inj.state, 'not installed here')
})
