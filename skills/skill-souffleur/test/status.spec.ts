import { test } from 'node:test'
import assert from 'node:assert/strict'
import { decide, initSession } from '../src/core/decide.ts'
import type { CoreEvent, Session } from '../src/core/decide.ts'
import { requested, skillLoaded } from '../src/core/ledger.ts'
import { renderTable, statusLine } from '../src/core/status.ts'
import type { Config } from '../src/core/types.ts'
import { parseConfig } from '../src/core/config.ts'

const T0 = Date.UTC(2026, 10, 25, 8, 0)
const T1 = Date.UTC(2026, 10, 25, 9, 5)

const config: Config = {
  mode: 'enforce',
  needs: { prose: 'Writing text people read.', ui: 'Building a screen.' },
  trustProjects: [], rules: [], notes: [], learn: { skills: true },
  skills: {
    'writing-guide': { need: 'prose', from: 'user' },
    'writing-check': { need: 'prose', from: 'user' },
    'terse:terse-mode': { always: true, from: 'user' },
    'ui-checklist': { need: 'ui', from: 'user' },
  },
}

const fresh = (c: Config = config, version?: string): Session => initSession(c, 'session-1', T0, 'clear', version)

test('status line counts loaded and restoring', () => {
  const s0 = fresh()
  const s: Session = {
    ...s0,
    ledger: requested(skillLoaded(s0.ledger, 'writing-guide', T1, 'matched prompt'), ['writing-check'], T1),
  }
  assert.equal(statusLine(s, 'enforce'), '1 loaded, 1 restoring')
})

test('status line says degraded when errors exist', () => {
  const s: Session = { ...fresh(), errors: ['tool_name missing from payload'] }
  assert.equal(statusLine(s, 'enforce'), 'degraded, see /souffleur')
})

test('status line is undefined without skills', () => {
  const empty: Config = { ...config, skills: {} }
  assert.equal(statusLine(fresh(empty), 'enforce'), undefined)
})

test('observe mode prefix in status line', () => {
  const s0 = fresh()
  const s: Session = { ...s0, ledger: skillLoaded(s0.ledger, 'writing-guide', T1, 'matched prompt') }
  assert.equal(statusLine(s, 'observe'), 'observe · 1 loaded')
})

test('table lists every configured skill with state and reason', () => {
  const s0 = fresh(config, '2.1.332')
  const s: Session = { ...s0, ledger: skillLoaded(s0.ledger, 'writing-guide', T1, 'matched prompt') }
  const out = renderTable(config, s, T1)
  const lines = out.split('\n')
  assert.equal(lines[0], 'Mode: enforce')
  assert.match(out, /^\| Skill \| State \| Since \| Reason \|$/m)
  assert.match(out, /^\| writing-guide \| loaded \| 09:05 \| matched prompt \|$/m)
  assert.match(out, /^\| terse:terse-mode \| absent \| 08:00 \|  \|$/m)
  for (const name of Object.keys(config.skills)) assert.match(out, new RegExp(`^\\| ${name.replace(':', '\\:')} \\|`, 'm'))
  assert.equal(lines.at(-1), 'Claude Code 2.1.332')
})

test('table shows not seen after 2 requests', () => {
  let ledger = fresh().ledger
  for (let i = 0; i < 3; i++) ledger = requested(ledger, ['writing-check'], T1)
  const s: Session = { ...fresh(), ledger }
  assert.match(renderTable(config, s, T1), /^\| writing-check \| unavailable \| 09:05 \| not seen after 2 requests \|$/m)
})

test('table lists open duties and active needs', () => {
  const s: Session = {
    ...fresh(),
    duties: [{ skill: 'ui-checklist', openedAt: T1, by: 'Write index.html', denied: false }],
    needs: { ui: { since: T1, reason: 'command' } },
    errors: ['tool_name missing from payload'],
  }
  const out = renderTable(config, s, T1)
  assert.match(out, /^Open duties:\n- ui-checklist \(Write index\.html\)$/m)
  assert.match(out, /^Active needs:\n- ui: command$/m)
  assert.match(out, /^Errors:\n- tool_name missing from payload$/m)
})

test('observe mode shows would-have-denied reasons in table', () => {
  const observe: Config = { ...config, mode: 'observe' }
  const s: Session = {
    ...fresh(observe),
    observed: [{ at: Date.UTC(2026, 10, 25, 9, 30), reason: 'gate: ui-checklist needs ui' }],
  }
  const out = renderTable(observe, s, T1)
  assert.equal(out.split('\n')[0], 'Mode: observe')
  assert.match(out, /^Would have denied:\n- 09:30 gate: ui-checklist needs ui$/m)
})

test('paused shows in first line', () => {
  const s: Session = { ...fresh(), paused: true }
  assert.equal(renderTable(config, s, T1).split('\n')[0], 'Mode: enforce (paused)')
})

test('decide status command replies with the table', () => {
  const s = fresh()
  const e: CoreEvent = { type: 'command', now: T1, args: 'status' }
  const r = decide(config, s, e)
  assert.deepEqual(r.actions, [{ kind: 'reply', text: renderTable(config, s, T1) }])
})

test('table cells escape backslashes, pipes and line breaks', () => {
  const config = parseConfig(JSON.stringify({ skills: { 'writing-guide': { always: true } } }), undefined).config
  const s = initSession(config, 'session-1', T0, 'startup')
  s.ledger['writing-guide'] = { ...s.ledger['writing-guide'], state: 'loaded', reason: 'a\\|b\r\nc' }
  assert.match(renderTable(config, s, T0), /^\| writing-guide \| loaded \| \d\d:\d\d \| a\\\\\\\|b c \|$/m)
})

test('status line counts skills not installed here separately', () => {
  const s0 = fresh()
  const s = decide(config, s0, { type: 'installed', now: T1, names: ['writing-guide'] }).session
  assert.equal(statusLine(s, 'enforce'), '0 loaded, 3 not installed here')
  assert.match(renderTable(config, s, T1), /\| ui-checklist \| not installed here \|/)
})

test('open duties of a skill not installed here are not listed', () => {
  const s0 = decide(config, fresh(), { type: 'installed', now: T1, names: ['writing-guide'] }).session
  const s = { ...s0, duties: [{ skill: 'ui-checklist', openedAt: T1, by: 'Write', denied: false }] }
  assert.doesNotMatch(renderTable(config, s, T1), /Open duties/)
})

test('the table carries the version notice when Claude Code is newer than the verified version, and the status line stays quiet', () => {
  const newer = fresh(config, '99.0.0')
  const table = renderTable(config, newer, T0)
  assert.match(table, /^Running Claude Code 99\.0\.0; Souffleur was checked up to \d+\.\d+\.\d+\. Report problems with `claude --version`\.$/m)
  assert.equal(table.split('\n').filter((l) => l.startsWith('Running Claude Code')).length, 1)
  assert.doesNotMatch(statusLine(newer, 'observe') ?? '', /Claude Code|checked up to/)
})

test('the table has no version notice for a verified or unknown version', () => {
  assert.doesNotMatch(renderTable(config, fresh(config, '2.1.322'), T0), /checked up to/)
  assert.doesNotMatch(renderTable(config, fresh(config), T0), /checked up to/)
})
