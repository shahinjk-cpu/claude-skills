import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const literals = (text: string) => [...text.matchAll(/'([^']+)'/g)].map((m) => m[1]!).sort()

test('the state union in types/index.d.ts equals SkillState in src/core/ledger.ts', () => {
  const ledger = readFileSync(new URL('../src/core/ledger.ts', import.meta.url), 'utf8')
  const contract = readFileSync(new URL('../types/index.d.ts', import.meta.url), 'utf8')
  const fromCode = /export type SkillState =([^\n]*)/.exec(ledger)?.[1]
  const fromTypes = /state:([^\n]*)/.exec(contract)?.[1]
  assert.ok(fromCode && fromTypes)
  assert.deepEqual(literals(fromTypes), literals(fromCode))
  assert.ok(literals(fromCode).includes('not installed here'))
})
