import { test } from 'node:test'
import assert from 'node:assert/strict'
import { builtinModules } from 'node:module'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const coreDir = join(import.meta.dirname, '..', 'src', 'core')
const builtins = new Set(builtinModules)

function forbiddenModule(spec: string): boolean {
  if (spec.startsWith('node:') || spec.startsWith('claude-code')) return true
  const bare = spec.startsWith('@') ? spec : spec.split('/')[0]!
  return builtins.has(spec) || builtins.has(bare)
}

/** Returns what a core source file must not use: node builtins, claude-code, `process`. */
export function findForbidden(source: string): string[] {
  const found: string[] = []
  const importForms = [
    /\bfrom\s*(['"])([^'"]*)\1/g, // import x from '...', export ... from '...' (also across lines)
    /\bimport\s*(['"])([^'"]*)\1/g, // import '...'
    /\bimport\s*\(\s*(['"])([^'"]*)\1/g, // import('...')
    /\brequire\s*\(\s*(['"])([^'"]*)\1/g, // require('...')
  ]
  for (const form of importForms) {
    for (const m of source.matchAll(form)) {
      if (forbiddenModule(m[2]!)) found.push(`import of "${m[2]}"`)
    }
  }
  if (/\bprocess\s*\./.test(source)) found.push('use of process')
  return found
}

test('findForbidden flags each forbidden form', () => {
  const bad = [
    `import { readFileSync } from 'node:fs'`,
    `import { readFileSync } from 'fs'`,
    `import { join } from "path"`,
    `import { x } from 'fs/promises'`,
    `import { x } from 'node:module'`,
    `import { builtinModules } from 'module'`,
    `const os = await import('node:os')`,
    `const os = await import( "os" )`,
    `import { x } from 'claude-code'`,
    `import { x } from 'claude-code/api'`,
    `import 'node:fs'`,
    `const fs = require('fs')`,
    `import {\n  a,\n  b,\n} from\n  'node:path'`,
    `import { a } from\n'fs'`,
    `const home = process.env.HOME`,
    `process\n  .exit(1)`,
  ]
  for (const source of bad) assert.notDeepEqual(findForbidden(source), [], source)
})

test('findForbidden accepts plain core code', () => {
  const good = [
    `import type { Config } from './types.ts'`,
    `import { matches } from './config.ts'`,
    `const processed = 3\nconst x = processing.length`,
    `export const from = 'fs'`,
  ]
  for (const source of good) assert.deepEqual(findForbidden(source), [], source)
})

test('src/core imports neither claude-code nor node builtins and never touches process', () => {
  const files = readdirSync(coreDir, { recursive: true, encoding: 'utf8' }).filter((f) => f.endsWith('.ts'))
  assert.ok(files.length > 0, 'src/core has no .ts files')
  for (const file of files) {
    assert.deepEqual(findForbidden(readFileSync(join(coreDir, file), 'utf8')), [], `src/core/${file}`)
  }
})
