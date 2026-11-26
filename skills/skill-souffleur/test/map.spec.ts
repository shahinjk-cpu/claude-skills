import assert from 'node:assert/strict'
import { test } from 'node:test'
import { isFromUser, toolFields } from '../src/mod/map.ts'

const input = (extra: Record<string, unknown> = {}) => ({ text: 'hello', origin: { kind: 'composer' }, ...extra })

test('isFromUser accepts composer, bridge and sdk prompts', () => {
  for (const kind of ['composer', 'bridge', 'sdk']) assert.equal(isFromUser(input({ origin: { kind } })), true)
})

test('isFromUser rejects typed commands, meta prompts and other origins', () => {
  assert.equal(isFromUser(input({ command: { name: 'compact', args: '' } })), false)
  assert.equal(isFromUser(input({ isMeta: true })), false)
  for (const kind of ['peer', 'task-notification', 'scheduled-trigger']) {
    assert.equal(isFromUser(input({ origin: { kind } })), false)
  }
})

test('toolFields reads the flat string arguments and ignores other types', () => {
  const e = { tool: 'Agent', tool_use_id: 't1', file_path: '/a/x.html', command: 'ls', prompt: 'skills: none', skill: 'writing-guide', model: 'haiku' }
  assert.deepEqual(toolFields(e), { path: '/a/x.html', command: 'ls', brief: 'skills: none', skill: 'writing-guide', model: 'haiku' })
  assert.deepEqual(toolFields({ tool: 'Write', tool_use_id: 't2', file_path: 5, command: null }), {})
})

test('isFromUser treats a prompt without origin as typed (the test kit sets none)', () => {
  assert.equal(isFromUser({ text: 'hello' } as never), true)
})
