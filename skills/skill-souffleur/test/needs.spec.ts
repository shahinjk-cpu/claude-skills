import { test } from 'node:test'
import assert from 'node:assert/strict'
import { classifyPrompt, neededSkills } from '../src/core/needs.ts'
import type { Config } from '../src/core/types.ts'

const needs = { prose: 'Writing text people read.', ui: 'Building a screen.' }

test('returns needs answered match', async () => {
  const seen: { text: string; labels: readonly string[] }[] = []
  const got = await classifyPrompt(
    'write the docs',
    needs,
    async (text, labels) => {
      seen.push({ text, labels })
      return text.includes('Writing text') ? 'match' : 'no-match'
    },
    () => new Promise(() => {}),
  )
  assert.deepEqual(got, ['prose'])
  assert.equal(seen.length, 2)
  assert.deepEqual(seen[0]!.labels, ['match', 'no-match'])
  assert.equal(seen[0]!.text, 'Need: Writing text people read.\n\nPrompt: write the docs')
})

test('a need whose call rejects is not matched', async () => {
  const got = await classifyPrompt(
    'x',
    needs,
    async (text) => {
      if (text.includes('Writing text')) throw new Error('boom')
      return 'match'
    },
    () => new Promise(() => {}),
  )
  assert.deepEqual(got, ['ui'])
})

test('budget ends before slow call: that need is dropped, fast one kept', async () => {
  let release: () => void = () => {}
  const timeoutGate = new Promise<void>((r) => (release = r))
  let slowFinished = false
  const slow = new Promise<string>((resolve) => {
    setTimeout(() => {
      slowFinished = true
      resolve('match')
    }, 50)
  })
  const run = classifyPrompt(
    'x',
    needs,
    (text) => (text.includes('Writing text') ? slow : Promise.resolve('match')),
    () => timeoutGate,
  )
  await new Promise((r) => setImmediate(r))
  release()
  const got = await run
  assert.equal(slowFinished, false)
  assert.deepEqual(got, ['ui'])
})

test('neededSkills keeps config order and includes always skills', () => {
  const config: Config = {
    mode: 'observe',
    needs,
    trustProjects: [], rules: [], notes: [], learn: { skills: true },
    skills: {
      a: { need: 'ui', from: 'user' },
      b: { always: true, from: 'user' },
      c: { need: 'prose', from: 'user' },
      d: { from: 'user' },
    },
  }
  assert.deepEqual(neededSkills(config, { prose: 1 }), ['b', 'c'])
  assert.deepEqual(neededSkills(config, { prose: 1, ui: 1 }), ['a', 'b', 'c'])
  assert.deepEqual(neededSkills(config, {}), ['b'])
})
