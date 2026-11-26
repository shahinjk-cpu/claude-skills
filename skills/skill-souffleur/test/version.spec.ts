import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { compareVersions, versionNotice, VERIFIED_UP_TO } from '../src/core/version.ts'

const root = join(import.meta.dirname, '..')
const read = (path: string): string => readFileSync(join(root, path), 'utf8')

test('compareVersions orders numbers, not strings', () => {
  assert.equal(compareVersions('2.1.332', '2.1.332'), 0)
  assert.equal(compareVersions('2.1.333', '2.1.332'), 1)
  assert.equal(compareVersions('2.1.99', '2.1.332'), -1)
  assert.equal(compareVersions('2.2.0', '2.1.999'), 1)
  assert.equal(compareVersions('10.0.0', '9.9.9'), 1)
})

test('compareVersions ranks a prerelease below its release and ignores build metadata', () => {
  assert.equal(compareVersions('2.1.333-beta.1', '2.1.333'), -1)
  assert.equal(compareVersions('2.1.333-beta.2', '2.1.333-beta.10'), -1)
  assert.equal(compareVersions('2.1.333-alpha', '2.1.333-1'), 1)
  assert.equal(compareVersions('2.1.333+build5', '2.1.333'), 0)
})

test('compareVersions answers undefined for text that is not a version', () => {
  assert.equal(compareVersions('', '2.1.332'), undefined)
  assert.equal(compareVersions('2.1', '2.1.332'), undefined)
  assert.equal(compareVersions('2.1.332', 'next'), undefined)
  assert.equal(compareVersions('2.1.x', '2.1.332'), undefined)
})

test('versionNotice speaks only when the running version is newer than the verified one', () => {
  assert.equal(
    versionNotice('2.1.400', '2.1.332'),
    'Running Claude Code 2.1.400; Souffleur was checked up to 2.1.332. Report problems with `claude --version`.',
  )
  assert.equal(versionNotice('2.1.332', '2.1.332'), undefined)
  assert.equal(versionNotice('2.1.322', '2.1.332'), undefined)
  assert.equal(versionNotice(undefined, '2.1.332'), undefined)
  assert.equal(versionNotice('unknown', '2.1.332'), undefined)
})

test('the verified version is the newest version named in docs/compatibility.md', () => {
  const found = read('docs/compatibility.md').match(/\b\d+\.\d+\.\d+\b/g) ?? []
  assert.ok(found.length > 0, 'docs/compatibility.md names no version')
  const newest = found.reduce((a, b) => (compareVersions(b, a) === 1 ? b : a))
  assert.equal(VERIFIED_UP_TO, newest)
})

test('plugin.json and marketplace.json carry the same version', () => {
  const plugin = JSON.parse(read('.claude-plugin/plugin.json')) as { name: string; version?: string }
  const market = JSON.parse(read('.claude-plugin/marketplace.json')) as { plugins: { name: string; version?: string }[] }
  const entry = market.plugins.find((p) => p.name === plugin.name)
  assert.ok(entry, 'marketplace.json has no entry for the plugin')
  assert.match(plugin.version ?? '', /^\d+\.\d+\.\d+$/)
  assert.equal(entry.version, plugin.version)
})
