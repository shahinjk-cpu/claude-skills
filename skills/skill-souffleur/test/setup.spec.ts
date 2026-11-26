import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseConfig } from '../src/core/config.ts'
import { applyChoice, candidates, cleanNeedText, CHOICE_LABEL, explicitOnly, injectedWarning, options, parsePicks, parseSkips, picksPrompt, setupSteps, SETUP_INTRO, INJECTED_HELP } from '../src/core/setup.ts'

const config = (user: unknown, project?: unknown) => parseConfig(JSON.stringify(user), project === undefined ? undefined : JSON.stringify(project)).config
const doc = (c: unknown) => c as { mode?: string; skills: Record<string, Record<string, unknown>>; needs: Record<string, string> }

test('options for a plain skill end with Stop', () => {
  const o = options('writing-guide', undefined, 'need')
  assert.equal(o.length, 4)
  assert.equal(o.at(-1), 'Stop')
  assert.ok(!o.includes(CHOICE_LABEL.injected))
})

test('options for a plugin skill offer Injected', () => {
  const o = options('terse:terse-mode', undefined, 'start')
  assert.ok(o.includes(CHOICE_LABEL.injected))
  assert.ok(!o.includes('Stop'))
  assert.ok(o.length <= 4)
})

test('current choice is listed first, else the recommended one', () => {
  assert.equal(options('writing-guide', 'need', 'start')[0], 'When the task needs it')
  assert.equal(options('writing-guide', undefined, 'start')[0], 'From the start')
  assert.equal(options('writing-guide', undefined, 'none')[0], "Don't watch")
  assert.equal(options('terse:terse-mode', 'injected', 'start')[0], CHOICE_LABEL.injected)
})

test('applyChoice start writes always', () => {
  const r = applyChoice({ mode: 'enforce', trustProjects: ['/w'] }, 'writing-guide', 'start')
  assert.deepEqual(doc(r.config).skills['writing-guide'], { always: true })
  assert.equal(doc(r.config).mode, 'enforce')
  assert.deepEqual((r.config as { trustProjects: string[] }).trustProjects, ['/w'])
})

test('applyChoice on a missing file starts in observe mode', () => {
  assert.equal(doc(applyChoice(undefined, 'writing-guide', 'start').config).mode, 'observe')
})

test('applyChoice injected writes always and startup injected', () => {
  const r = applyChoice({}, 'terse:terse-mode', 'injected')
  assert.deepEqual(doc(r.config).skills['terse:terse-mode'], { always: true, startup: 'injected' })
})

test('applyChoice need reuses a shared key', () => {
  const start = { skills: { 'writing-check': { need: 'prose' } }, needs: { prose: 'Writing text people read.' } }
  const r = applyChoice(start, 'writing-guide', 'need', { key: 'prose', text: 'Writing text people read.' })
  assert.deepEqual(doc(r.config).skills['writing-guide'], { need: 'prose' })
  assert.deepEqual(doc(r.config).needs, { prose: 'Writing text people read.' })
})

test('other text on a shared need forks a new key', () => {
  const start = { skills: { 'writing-check': { need: 'prose' }, 'writing-guide': { need: 'prose' } }, needs: { prose: 'Writing text people read.' } }
  const r = applyChoice(start, 'writing-guide', 'need', { key: 'prose', text: 'Writing a README.' })
  const d = doc(r.config)
  assert.equal(d.skills['writing-check']!.need, 'prose')
  const key = d.skills['writing-guide']!.need as string
  assert.notEqual(key, 'prose')
  assert.match(key, /^[A-Za-z0-9:_-]{1,64}$/)
  assert.equal(d.needs[key], 'Writing a README.')
  assert.equal(d.needs.prose, 'Writing text people read.')
})

test('none removes entry and orphaned need', () => {
  const start = { skills: { 'writing-guide': { need: 'prose' }, 'ui-checklist': { need: 'ui' } }, needs: { prose: 'p', ui: 'u' } }
  const d = doc(applyChoice(start, 'writing-guide', 'none').config)
  assert.deepEqual(Object.keys(d.skills), ['ui-checklist'])
  assert.deepEqual(d.needs, { ui: 'u' })
})

test('none keeps an entry with a gate and says why', () => {
  const entry = { need: 'ui', gate: { tools: ['Write'] } }
  const start = { skills: { 'ui-checklist': entry }, needs: { ui: 'u' } }
  const r = applyChoice(start, 'ui-checklist', 'none')
  assert.deepEqual(r.config, start)
  assert.match(r.note ?? '', /gate or duty/)
})

test('change of kind keeps gate and duty', () => {
  const duty = { after: { tools: ['Write'] }, evidence: { tool: 'Bash' } }
  const start = { skills: { 'ui-checklist': { need: 'ui', gate: { tools: ['Write'] }, duty } }, needs: { ui: 'u' } }
  const d = doc(applyChoice(start, 'ui-checklist', 'start').config)
  assert.deepEqual(d.skills['ui-checklist'], { always: true, gate: { tools: ['Write'] }, duty })
  assert.deepEqual(d.needs, {})
})

test('applyChoice does not change its input', () => {
  const start = { skills: { 'writing-guide': { need: 'prose' } }, needs: { prose: 'p' } }
  const frozen = structuredClone(start)
  applyChoice(start, 'writing-guide', 'none')
  assert.deepEqual(start, frozen)
})

test('candidates order: user, hook, model; project-only is listed, not asked', () => {
  const c = config({ skills: { 'writing-guide': { always: true } } }, { skills: { 'ui-checklist': { always: true } } })
  const got = candidates(c, ['writing-guide', 'ui-checklist', 'writing-check', 'bigtest', 'other-one'], ['writing-check'], ['bigtest', 'not-installed'])
  assert.deepEqual(got, [
    { skill: 'writing-guide', source: 'user' },
    { skill: 'writing-check', source: 'hook' },
    { skill: 'bigtest', source: 'model' },
    { skill: 'ui-checklist', source: 'project' },
  ])
})

test('project-only skill is listed, not asked', () => {
  const c = config({ skills: {} }, { skills: { 'ui-checklist': { always: true } } })
  const got = candidates(c, ['ui-checklist'], [], [])
  assert.deepEqual(got, [{ skill: 'ui-checklist', source: 'project' }])
})

test('parsePicks keeps installed names, reuses existing need keys, caps at 10', () => {
  const installed = ['writing-guide', 'writing-check', 'ui-checklist']
  const raw = 'Sure:\n```json\n' + JSON.stringify({
    skills: [
      { name: 'writing-guide', need: 'prose', needText: 'ignored, prose exists' },
      { name: 'ui-checklist', need: 'ui', needText: 'Building a screen.' },
      { name: 'ghost', need: 'x', needText: 'y' },
      { name: 'writing-check', need: 'bad key!' },
      'junk',
    ],
  }) + '\n```'
  const got = parsePicks(raw, installed, { prose: 'Writing text people read.' })
  assert.deepEqual(got, [
    { skill: 'writing-guide', need: { key: 'prose', text: 'Writing text people read.' } },
    { skill: 'ui-checklist', need: { key: 'ui', text: 'Building a screen.' } },
  ])
  assert.deepEqual(parsePicks('no json', installed, {}), [])
  const many = Array.from({ length: 14 }, (_, i) => `skill-number-${i}`)
  assert.equal(parsePicks(JSON.stringify(many.map((name) => ({ name, need: 'k', needText: 't' }))), many, {}).length, 10)
})

test('SETUP_INTRO names the four answers and points to migrate', () => {
  for (const w of ['From the start', CHOICE_LABEL.injected, 'When the task needs it', "Don't watch", '/souffleur migrate']) assert.ok(SETUP_INTRO.includes(w), w)
  assert.doesNotMatch(SETUP_INTRO, /[–—]/)
})

test('a non-plugin skill whose current setting is injected is offered Injected in place of Stop', () => {
  const o = options('writing-guide', 'injected', 'start')
  assert.equal(o[0], CHOICE_LABEL.injected)
  assert.ok(!o.includes('Stop'))
  assert.equal(o.length, 4)
})

test('applyChoice leaves anything that is not a config object alone and says so', () => {
  for (const bad of [[], 'text', 5, { skills: 'nope' }, { needs: [] }, { skills: [] }]) {
    const r = applyChoice(bad, 'writing-guide', 'start')
    assert.deepEqual(r.config, bad)
    assert.match(r.note ?? '', /not|wrong|object/i)
  }
})

test('applyChoice with the same choice returns an equal config', () => {
  const start = { mode: 'observe', skills: { 'writing-guide': { always: true } }, needs: {} }
  assert.deepEqual(applyChoice(start, 'writing-guide', 'start').config, start)
})

test('applyChoice refuses a need text that config.ts would reject', () => {
  for (const text of ['', 'a\nb', 'x'.repeat(201)]) {
    const r = applyChoice({ skills: {}, needs: {} }, 'writing-guide', 'need', { key: 'prose', text })
    assert.deepEqual(r.config, { skills: {}, needs: {} })
    assert.ok(r.note)
  }
})

test('cleanNeedText collapses whitespace and keeps 1 to 200 characters', () => {
  assert.equal(cleanNeedText('  a\n  b\t c '), 'a b c')
  assert.equal(cleanNeedText('   '), undefined)
  assert.equal(cleanNeedText('x'.repeat(201)), undefined)
  assert.equal(cleanNeedText('x'.repeat(200))?.length, 200)
})

test('needs that a project-file skill uses survive pruning, and removed needs are reported', () => {
  const start = { skills: { 'writing-guide': { need: 'ui' }, 'writing-check': { need: 'prose' } }, needs: { ui: 'u', prose: 'p' } }
  const r = applyChoice(start, 'writing-guide', 'none', undefined, { 'ui-checklist': { need: 'ui' } })
  assert.deepEqual(doc(r.config).needs, { ui: 'u', prose: 'p' })
  const gone = applyChoice(start, 'writing-check', 'none')
  assert.deepEqual(gone.pruned, ['prose'])
})

test('the shared-need check counts skills of the project file', () => {
  const start = { skills: {}, needs: { ui: 'Building a screen.' } }
  const r = applyChoice(start, 'writing-guide', 'need', { key: 'ui', text: 'Something else.' }, { 'ui-checklist': { need: 'ui' } })
  const key = doc(r.config).skills['writing-guide']!.need as string
  assert.notEqual(key, 'ui')
  assert.equal(doc(r.config).needs.ui, 'Building a screen.')
})

test('the injected label says it is rare and is never the first answer unless it is the current setting', () => {
  assert.equal(CHOICE_LABEL.injected, 'Loaded by its own plugin at start (rare)')
  for (const rec of ['start', 'need', 'none', 'injected'] as const) {
    assert.notEqual(options('terse:terse-mode', undefined, rec)[0], CHOICE_LABEL.injected)
    assert.notEqual(options('terse:terse-mode', 'need', rec)[0], CHOICE_LABEL.injected)
  }
  assert.equal(options('terse:terse-mode', 'injected', 'start')[0], CHOICE_LABEL.injected)
})

test('the help text for the injected answer gives an example and names the other answers', () => {
  assert.match(INJECTED_HELP, /session start/i)
  assert.match(INJECTED_HELP, /for example/i)
  assert.ok(INJECTED_HELP.includes(CHOICE_LABEL.injected))
  assert.doesNotMatch(INJECTED_HELP, /[–—]/)
})

test('injectedWarning has a line for every result except a hook that names the skill', () => {
  assert.equal(injectedWarning('flow:plan', 'mentions'), undefined)
  assert.match(injectedWarning('flow:plan', 'none')!, /^Warning: the plugin flow has no SessionStart hook/)
  assert.match(injectedWarning('flow:plan', 'exists')!, /^Note: the plugin flow has a SessionStart hook; Souffleur cannot tell whether it prints flow:plan/)
  assert.match(injectedWarning('flow:plan', 'unknown')!, /could not check/i)
  assert.equal(injectedWarning('plain-skill', 'none'), undefined)
})

test('explicitOnly spots descriptions that run only on request', () => {
  assert.equal(explicitOnly('Use ONLY when the owner asks for it by name'), true)
  assert.equal(explicitOnly('Only use when the user explicitly asks for a deep review.'), true)
  assert.equal(explicitOnly('Review code. Invoke only when explicitly requested.'), true)
  assert.equal(explicitOnly('Draft notes. Run it only when the owner asks.'), true)
  assert.equal(explicitOnly('Use when writing text that people read'), false)
  assert.equal(explicitOnly(undefined), false)
})

test('picksPrompt asks for a clear match before a need is reused and allows no need', () => {
  const p = picksPrompt([{ name: 'a', description: 'x' }], { prose: 'Writing text people read.' })
  assert.match(p, /only when the description clearly/i)
  assert.match(p, /"need": null/)
  assert.match(p, /explicit request/i)
})

test('parseSkips lists installed skills the model gave no need', () => {
  const raw = JSON.stringify({ skills: [{ name: 'a', need: null }, { name: 'b', need: 'ui', needText: 't' }, { name: 'ghost', need: null }, { name: 'c', need: 'none' }] })
  assert.deepEqual(parseSkips(raw, ['a', 'b', 'c']), ['a', 'c'])
  assert.deepEqual(parseSkips('no json', ['a']), [])
})

test('explicitOnly leaves skills that merely mention explicit requests alone', () => {
  for (const text of [
    'Security guidance. Run the complete workflow only for explicit codebase audit or pen-test requests',
    'Only use the strict mode if the user asks',
    'Review the plan, then explicitly invoke the detector at the end',
  ]) assert.equal(explicitOnly(text), false, text)
})

test('setupSteps lists warnings after the recommendations', () => {
  const plans = [{ skill: 'flow:plan', source: 'user' as const, current: 'injected' as const, recommended: 'injected' as const }]
  const text = setupSteps({ plans, userConfig: undefined, configPath: '~/c.json', unwatched: [], warnings: ['Warning: x.'] })
  assert.match(text, /Warning: x\./)
})
