import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync } from 'node:fs'
import { join } from 'node:path'
import { EVENT_NAMES, loadFixtureFile } from './fixtures.ts'

const names = readdirSync(join(import.meta.dirname, 'fixtures'))
  .filter((f) => f.endsWith('.json'))
  .map((f) => f.slice(0, -'.json'.length))

test('there are fixtures to check', () => {
  assert.ok(names.length >= 4)
})

for (const name of names) {
  test(`fixture ${name}: loads, names its Claude Code version, uses known events in time order`, () => {
    const file = loadFixtureFile(name)
    assert.match(file.claudeCode, /^\d+\.\d+\.\d+$/)
    assert.ok(file.events.length > 0)
    let last = -Infinity
    for (const e of file.events) {
      assert.ok(EVENT_NAMES.includes(e.event), `unknown event ${e.event}`)
      assert.equal(typeof e.session, 'string')
      assert.ok(typeof e.input === 'object' && e.input !== null)
      assert.ok(e.at >= last, `"at" goes backwards at ${e.event} ${e.at}`)
      last = e.at
    }
  })
}
