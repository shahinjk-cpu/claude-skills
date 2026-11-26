/**
 * The newest Claude Code version Souffleur was checked on. Keep it equal to the newest version named in
 * `docs/compatibility.md`; a test compares the two.
 */
export const VERIFIED_UP_TO = '2.1.332'

interface Parsed {
  core: [number, number, number]
  pre: string[]
}

const SEMVER = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/

function parse(text: string): Parsed | undefined {
  const m = SEMVER.exec(text.trim())
  if (!m) return undefined
  return { core: [Number(m[1]), Number(m[2]), Number(m[3])], pre: m[4] === undefined ? [] : m[4].split('.') }
}

const numeric = (id: string): boolean => /^\d+$/.test(id)

function comparePre(a: string[], b: string[]): -1 | 0 | 1 {
  // A version without a prerelease ranks above one with it.
  if (a.length === 0 || b.length === 0) return a.length === b.length ? 0 : a.length === 0 ? 1 : -1
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const x = a[i]!
    const y = b[i]!
    if (x === y) continue
    if (numeric(x) && numeric(y)) return Number(x) > Number(y) ? 1 : -1
    if (numeric(x) !== numeric(y)) return numeric(x) ? -1 : 1
    return x > y ? 1 : -1
  }
  return a.length === b.length ? 0 : a.length > b.length ? 1 : -1
}

/** Semver order of two versions: -1, 0 or 1; `undefined` when either is not a version. Build metadata is ignored. */
export function compareVersions(a: string, b: string): -1 | 0 | 1 | undefined {
  const x = parse(a)
  const y = parse(b)
  if (!x || !y) return undefined
  for (let i = 0; i < 3; i++) {
    if (x.core[i]! !== y.core[i]!) return x.core[i]! > y.core[i]! ? 1 : -1
  }
  return comparePre(x.pre, y.pre)
}

/** One line for `/souffleur` when the running Claude Code is newer than the verified one; otherwise `undefined`. */
export function versionNotice(running: string | undefined, verified: string = VERIFIED_UP_TO): string | undefined {
  if (running === undefined) return undefined
  if (compareVersions(running, verified) !== 1) return undefined
  return `Running Claude Code ${running}; Souffleur was checked up to ${verified}. Report problems with \`claude --version\`.`
}
