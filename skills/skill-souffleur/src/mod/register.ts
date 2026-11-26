import type { Register } from 'claude-code'
import { parseConfig } from '../core/config.ts'
import { decide, initSession, normalizeSession } from '../core/decide.ts'
import { MIGRATE_INTRO, describeHook, findHookOverlaps, findPassages, hookQuestion, hookSteps, isGuess, migrateSteps, passageLines, removeHook } from '../core/migrate.ts'
import type { HookOverlap, Passage } from '../core/migrate.ts'
import { CHOICE_LABEL, INJECTED_HELP, NOT_SET_UP, SETUP_INTRO, applyChoice, candidates, choiceOf, cleanNeedText, configProblem, currentChoice, describePlan, explicitOnly, injectedWarning, needKeyFor, options, parsePicks, parseSkips, picksPrompt, setupSteps } from '../core/setup.ts'
import type { LoadChoice, NeedText, Plan, StartHooks, Suggestion } from '../core/setup.ts'
import type { Action, CoreEvent, Session } from '../core/decide.ts'
import { classifyPrompt } from '../core/needs.ts'
import { EXTRACT_SYSTEM, MAX_SKILL_TEXT, extractPrompt, hashKey, parseAnswer, shouldRead, skillHash, trusted } from '../core/learn.ts'
import { NO, YES_EVERYWHERE, YES_PROJECT, addEntry, answer, describeProposal, enqueue, findProposal, makeProposal, nextQuestion, parseShaped, proposalLines, shapePrompt } from '../core/proposals.ts'
import { ruleSkillNames, sectionNotes } from '../core/rules.ts'
import { statusLine } from '../core/status.ts'
import type { Config, Note, Rule } from '../core/types.ts'
import { isFromUser, isUserOrigin, toolFields } from './map.ts'

// The hooks' `$` is the engine interface; the adapter calls only documented members.
type Dollar = any
/** `root` is the main repository root (what `where` names), `tree` the session's own working tree (what globs are relative to). */
type Loaded = { config: Config; errors: string[]; root: string; tree: string; cwd: string; setUp: boolean }

const REF = { plugin: 'skill-souffleur', key: 'session' } as const
const RULE =
  'Souffleur keeps track of skills in this session. If a message from Souffleur asks you to load skills, invoke each one with the Skill tool before you continue.'
const PROPOSE_SENTENCE =
  ' When something went wrong that a rule would have caught, or the user asks you to remember a rule, call the souffleur_propose tool. Souffleur then asks the user; do not write the rule anywhere yourself.'
const PROPOSE_TOOL = 'mcp__skill-souffleur__souffleur_propose'
const DECLINED_KEY = 'souffleur:declined'

// Module variables start over on a reload; the config is read again by `session.start`, which a reload runs.
let loaded: Loaded | undefined
/** The session this process stored last, with its revision. */
let latest: Session | undefined
/** Set by `session.start`: a person is at the prompt, and the propose tool is registered. */
let interactive = false
let proposeReady = false
/** A dialog was dismissed or could not open: no more questions at turn end in this session. */
let askStopped = false

const now = () => Date.now()
const message = (err: unknown) => (err instanceof Error ? err.message : String(err))

const stripBom = (text: string) => text.replace(/^\uFEFF/, '')
const parseJson = (text: string): unknown => JSON.parse(stripBom(text))
const shownPath = (home: string | undefined, path: string) => (home && path.startsWith(`${home}/`) ? `~${path.slice(home.length)}` : path)
/** An error text with the home folder written as `~`. */
const scrub = (home: string | undefined, text: string) => (home ? text.split(home).join('~') : text)

async function readOptional($: Dollar, path: string, errors: string[], home?: string): Promise<string | undefined> {
  try {
    if (!(await $.fs.exists(path))) return undefined
    return await $.fs.read(path)
  } catch (err) {
    errors.push(`cannot read ${shownPath(home, path)}: ${scrub(home, message(err))}`)
    return undefined
  }
}

/** A file as a command that writes it must see it: missing is not the same as unreadable. */
type FileState = { kind: 'missing' } | { kind: 'ok'; text: string } | { kind: 'error'; why: string }
async function readState($: Dollar, path: string, home: string): Promise<FileState> {
  try {
    if (!(await $.fs.exists(path))) return { kind: 'missing' }
    return { kind: 'ok', text: await $.fs.read(path) }
  } catch (err) {
    return { kind: 'error', why: scrub(home, message(err)) }
  }
}

async function getLoaded($: Dollar): Promise<Loaded> {
  if (loaded) return loaded
  const errors: string[] = []
  const home = await $.env.get('HOME')
  const root = (await $.session.repo())?.root ?? (await $.session.cwd())
  const cwd: string = await $.session.cwd()
  const userText = home ? await readOptional($, `${home}/.claude/souffleur.json`, errors, home) : undefined
  const projectText = await readOptional($, `${root}/.claude/souffleur.json`, errors, home)
  const parsed = parseConfig(userText === undefined ? undefined : stripBom(userText), projectText === undefined ? undefined : stripBom(projectText))
  let tree = cwd
  try {
    const copy = await $.vcs.detect({ path: cwd })
    if (copy && typeof copy.root === 'string') tree = copy.root
  } catch {
    // outside a repository, or no detection: the working directory is the tree
  }
  loaded = { config: parsed.config, errors: [...errors, ...parsed.errors], root, tree, cwd, setUp: userText !== undefined }
  return loaded
}

const isSession = (v: unknown, id: string): v is Session =>
  typeof v === 'object' && v !== null && (v as Session).id === id && typeof (v as Session).ledger === 'object' && (v as Session).ledger !== null

async function freshSession($: Dollar, l: Loaded, id: string, start: 'startup' | 'clear'): Promise<Session> {
  const version = (await $.session.version()).version
  let s = initSession(l.config, id, now(), start, version)
  for (const msg of l.errors) s = decide(l.config, s, { type: 'error', now: now(), where: 'config', message: msg }).session
  return s
}

/** The session this hook works on: `$.state`, else the stored copy of a resumed session, else a new one. */
async function current($: Dollar): Promise<{ l: Loaded; session: Session }> {
  const l = await getLoaded($)
  const id: string = await $.session.id()
  let held: Session | undefined = (await $.state.get(REF)).value
  // What this process wrote last wins over a state read that has not caught up (hooks that run at the same moment).
  if (latest && latest.id === id && (held === undefined || (isSession(held, id) && (held.rev ?? 0) < (latest.rev ?? 0)))) held = latest
  if (held && held.id === id) return { l, session: heal(l, held) }
  // A different id with no session.start in between is /clear (D6).
  if (held) return { l, session: await freshSession($, l, id, 'clear') }
  const stored = await $.store.get(`session:${id}`)
  if (isSession(stored, id)) return { l, session: heal(l, stored) }
  return { l, session: await freshSession($, l, id, 'startup') }
}

/** A session whose ledger lists other skills than the config (a session that missed a config change) follows the config. */
function heal(l: Loaded, held: Session): Session {
  const s = normalizeSession(held)
  const want = [...new Set([...Object.keys(l.config.skills), ...ruleSkillNames(l.config)])]
  const have = Object.keys(s.ledger)
  if (want.length === have.length && want.every((name) => name in s.ledger)) return s
  return decide(l.config, s, { type: 'config', now: now(), errors: l.errors }).session
}

async function persist($: Dollar, l: Loaded, s0: Session): Promise<void> {
  const s: Session = { ...s0, rev: (s0.rev ?? 0) + 1 }
  latest = s
  // A broken file shows as degraded; only a clean start without a user file says "not set up".
  $.ui.status(!l.setUp && !s.errors.length ? NOT_SET_UP : statusLine(s, l.config.mode, sectionNotes(l.config, l.root).leftOut.length))
  await $.state.set(REF, s)
  await $.store.set(`session:${s.id}`, s)
}

/** Session reads and writes wait for each other: two hooks at the same moment must not both read the old state. */
let chain: Promise<unknown> = Promise.resolve()
function serial<T>(work: () => Promise<T>): Promise<T> {
  const run = chain.then(work, work)
  chain = run.catch(() => undefined)
  return run
}

/** Feeds one event to the core and stores the result. */
function apply($: Dollar, make: (l: Loaded) => CoreEvent): Promise<{ actions: Action[]; l: Loaded }> {
  return serial(async () => {
    const { l, session } = await current($)
    const r = decide(l.config, session, make(l))
    await persist($, l, r.session)
    return { actions: r.actions, l }
  })
}

/** Runs the adapter's own work. A throw becomes an `error` event and `fallback`; it never reaches the event. */
async function safe<T>($: Dollar, where: string, fallback: T, work: () => Promise<T>): Promise<T> {
  try {
    return await work()
  } catch (err) {
    try {
      await apply($, () => ({ type: 'error', now: now(), where, message: message(err) }))
    } catch {
      // Recording failed too; the event still goes through.
    }
    return fallback
  }
}

/** How long the skill listing may take before the prompt goes on without it. */
const LIST_BUDGET_MS = 300

/**
 * The names `$.session.usage` lists (observed on 2.1.332: plugin skills as `plugin:skill`, others bare), or undefined when
 * that list is missing, empty or incomplete. The command list is not used: it is a different list, so it would mark skills wrongly.
 */
async function listedSkills($: Dollar): Promise<string[] | undefined> {
  try {
    const skills = (await $.session.usage({ breakdown: 'summary' }))?.context?.breakdown?.skills
    const listed: { name: string }[] | undefined = skills?.skillFrontmatter
    if (!listed?.length) return undefined
    if (typeof skills.totalSkills === 'number' && typeof skills.includedSkills === 'number' && skills.includedSkills < skills.totalSkills) return undefined
    return [...new Set(listed.map((x) => x.name))]
  } catch {
    return undefined
  }
}

/** Tells the ledger which skills this session lists, so configured skills it lacks are neither requested nor gated. Gives up after the budget. */
async function refreshInstalled($: Dollar): Promise<void> {
  const names = await Promise.race([listedSkills($), $.clock.sleep(LIST_BUDGET_MS).then(() => undefined)])
  if (names?.length) await apply($, () => ({ type: 'installed', now: now(), names }))
}

/**
 * What the plugin behind `skill` (`plugin:name`) says about SessionStart hooks, over every installed copy of it: its
 * `hooks/hooks.json` and the hooks declared in `plugin.json`. `mentions`: a hook command names the skill. `none` only
 * when every file could be read and none declares one; anything unsure is `unknown`.
 */
async function pluginStartHooks($: Dollar, home: string, skill: string): Promise<StartHooks> {
  const plugin = skill.split(':')[0]!
  const bareName = skill.split(':').pop()!
  const names = new RegExp(`(^|[^A-Za-z0-9])${bareName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}([^A-Za-z0-9]|$)`)
  try {
    const listed: unknown = parseJson(await $.fs.read(`${home}/.claude/plugins/installed_plugins.json`))
    const plugins = (listed as { plugins?: Record<string, { installPath?: unknown }[]> }).plugins ?? {}
    const dirs = Object.entries(plugins)
      .filter(([key]) => key.split('@')[0] === plugin)
      .flatMap(([, copies]) => (Array.isArray(copies) ? copies : []))
      .flatMap((copy) => (typeof copy?.installPath === 'string' ? [copy.installPath] : []))
    if (!dirs.length) return 'unknown'
    let read = 0
    let unsure = false
    let declared = false
    const commands: string[] = []
    const take = (hooks: unknown) => {
      const groups = typeof hooks === 'object' && hooks !== null ? (hooks as Record<string, unknown>).SessionStart : undefined
      if (!Array.isArray(groups) || groups.length === 0) return
      declared = true
      for (const g of groups) for (const h of Array.isArray(g?.hooks) ? g.hooks : []) if (typeof h?.command === 'string') commands.push(h.command)
    }
    for (const dir of dirs) {
      for (const file of [`${dir}/hooks/hooks.json`, `${dir}/.claude-plugin/plugin.json`]) {
        if (!(await $.fs.exists(file))) continue
        try {
          const doc = parseJson(await $.fs.read(file)) as { hooks?: unknown }
          read += 1
          if (typeof doc.hooks === 'string') {
            const more = `${dir}/${doc.hooks.replace(/^\.\//, '')}`
            if (await $.fs.exists(more)) take((parseJson(await $.fs.read(more)) as { hooks?: unknown }).hooks)
            else unsure = true
          } else take(doc.hooks)
        } catch {
          unsure = true
        }
      }
    }
    if (declared) return commands.some((c) => names.test(c)) ? 'mentions' : 'exists'
    return read > 0 && !unsure ? 'none' : 'unknown'
  } catch {
    return 'unknown'
  }
}

/** The names `$.session.usage` lists, with the command list as a fallback. For init's candidates only: it says nothing about what is installed here. */
async function installedSkills($: Dollar): Promise<string[]> {
  const listed = await listedSkills($)
  if (listed) return listed
  try {
    const usage = await $.session.usage({ breakdown: 'summary' })
    const partial: { name: string }[] | undefined = usage?.context?.breakdown?.skills?.skillFrontmatter
    if (partial?.length) return [...new Set(partial.map((x) => x.name))]
  } catch {
    // fall through to the command list
  }
  try {
    return (await $.command.list()).map((c: { name: string }) => c.name)
  } catch {
    return []
  }
}

const stamp = (ms: number) => {
  const iso = new Date(ms).toISOString()
  return `${iso.slice(0, 10).replace(/-/g, '')}-${iso.slice(11, 19).replace(/:/g, '')}`
}

/** A backup name nobody has used yet: the time to the second, then a counter. */
async function freeBackupPath($: Dollar, settingsPath: string): Promise<string> {
  const base = `${settingsPath}.bak-souffleur-${stamp(now())}`
  for (let n = 0; n < 1000; n++) {
    const path = n === 0 ? base : `${base}-${n}`
    if (!(await $.fs.exists(path))) return path
  }
  throw new Error('no free backup name')
}

/** `~/.claude/settings.json` as a value; `error` says why it cannot be used (unreadable or not JSON). */
async function readSettings($: Dollar, path: string, home: string): Promise<{ text?: string; value?: unknown; error?: string }> {
  const st = await readState($, path, home)
  if (st.kind === 'missing') return {}
  if (st.kind === 'error') return { error: `could not read ${shownPath(home, path)} (${st.why})` }
  try {
    return { text: st.text, value: parseJson(st.text) }
  } catch {
    return { text: st.text, error: `${shownPath(home, path)} is not valid JSON` }
  }
}

/** Installed skill names with the one-line description the command list gives, where there is one. */
async function installedWithDescriptions($: Dollar): Promise<{ name: string; description?: string }[]> {
  const names = await installedSkills($)
  let described = new Map<string, string>()
  try {
    described = new Map((await $.command.list()).map((c: { name: string; description?: string }) => [c.name, c.description ?? '']))
  } catch {
    // names alone are enough
  }
  return names.map((name) => {
    const description = described.get(name)
    return description ? { name, description } : { name }
  })
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/**
 * The standing instructions to scan: user and project CLAUDE.md, the files a CLAUDE.md imports with `@path` (one level),
 * and the memory index of the project (named after the main repository root).
 */
async function readStanding($: Dollar, l: Loaded, home: string, notes: string[]): Promise<{ file: string; text: string; project: boolean }[]> {
  const slug = l.root.replace(/[^A-Za-z0-9]/g, '-')
  const claudeMds = [...new Set([`${home}/.claude/CLAUDE.md`, `${l.root}/CLAUDE.md`, `${l.cwd}/CLAUDE.md`])]
  const files: { file: string; text: string; project: boolean }[] = []
  const seen = new Set<string>()
  for (const path of claudeMds) {
    const text = await readOptional($, path, notes, home)
    if (text === undefined) continue
    seen.add(path)
    const project = path !== `${home}/.claude/CLAUDE.md`
    files.push({ file: shownPath(home, path), text, project })
    const dir = path.slice(0, path.lastIndexOf('/'))
    for (const m of text.matchAll(/(?:^|\s)@([^\s@]+\.[A-Za-z0-9]+)/g)) {
      const ref = m[1]!
      const target = ref.startsWith('/') ? ref : ref.startsWith('~/') ? `${home}/${ref.slice(2)}` : `${dir}/${ref.replace(/^\.\//, '')}`
      if (seen.has(target)) continue
      seen.add(target)
      const imported = await readOptional($, target, notes, home)
      if (imported !== undefined) files.push({ file: shownPath(home, target), text: imported, project })
    }
  }
  const memory = `${home}/.claude/projects/${slug}/memory/MEMORY.md`
  const text = await readOptional($, memory, notes, home)
  if (text !== undefined) files.push({ file: shownPath(home, memory), text, project: false })
  return files
}

const withNotes = (text: string, notes: string[]) => (notes.length ? `${text}\n\nNotes:\n${notes.map((n) => `- ${n}`).join('\n')}` : text)

/**
 * `/souffleur init`: asks per skill how it is kept and writes each answer to the user file as it comes.
 * It reads the files fresh, writes only the user file, and writes nothing when the file cannot be read or edited.
 * Where no dialog answers, it returns the recommendations and the config they give, and writes nothing.
 */
async function runInit($: Dollar, l0: Loaded): Promise<string> {
  const notes: string[] = []
  const home: string | undefined = await $.env.get('HOME')
  if (!home) return 'Souffleur init: the home folder is unknown, so nothing was changed.'
  const configPath = `${home}/.claude/souffleur.json`
  const settingsPath = `${home}/.claude/settings.json`
  const shown = (path: string) => shownPath(home, path)
  const stop = (why: string) => `Souffleur init: ${why}, so nothing was changed. Fix that and run /souffleur init again.`

  // Fresh reads: the config cached at session start may be out of date.
  const user = await readState($, configPath, home)
  if (user.kind === 'error') return stop(`could not read ${shown(configPath)} (${user.why})`)
  let userDoc: unknown
  if (user.kind === 'ok') {
    try {
      userDoc = parseJson(user.text)
    } catch (err) {
      return stop(`${shown(configPath)} is not valid JSON (${message(err)})`)
    }
    const problem = configProblem(userDoc)
    if (problem) return stop(`${shown(configPath)} cannot be edited because ${problem}`)
  }
  const projectText = await readOptional($, `${l0.root}/.claude/souffleur.json`, notes, home)
  const parsed = parseConfig(user.kind === 'ok' ? stripBom(user.text) : undefined, projectText === undefined ? undefined : stripBom(projectText))
  const config = parsed.config
  notes.push(...parsed.errors)
  const projectSkills: Record<string, unknown> = Object.fromEntries(Object.entries(config.skills).filter(([, r]) => r.from === 'project'))

  const settings = await readSettings($, settingsPath, home)
  if (settings.error) notes.push(`${settings.error}, so its hooks were not checked.`)
  const described = await installedWithDescriptions($)
  const installed = described.map((x) => x.name)
  const configured = Object.keys(config.skills)
  const hooks = findHookOverlaps(settings.value, configured, installed.filter((n) => !configured.includes(n)))
  const reloadHooked = [...new Set(hooks.flatMap((o) => (o.skill !== undefined && installed.includes(o.skill) && !(o.skill in config.skills) ? [o.skill] : [])))]
  const startHooked = new Set(hooks.flatMap((o) => (o.event === 'SessionStart' && o.skill !== undefined ? [o.skill] : [])))
  const passages = findPassages(await readStanding($, l0, home, notes), configured, Infinity)

  // One small-model call over the installed skills that have no need yet: unconfigured, hook-reloaded, or in the user file without one.
  // Skills whose description says they run only on an explicit request are not sent; they are advised against watching.
  const explicit = new Set(described.filter((x) => explicitOnly(x.description)).map((x) => x.name))
  const pool = described.filter((x) => {
    const rule = config.skills[x.name]
    return !explicit.has(x.name) && (rule === undefined || (rule.from === 'user' && rule.need === undefined))
  })
  const skips = new Set(explicit)
  let picks: Suggestion[] = []
  if (pool.length) {
    try {
      const r = await $.model.complete({ model: 'haiku', prompt: picksPrompt(pool, config.needs) })
      if (r.isAnswered) {
        picks = parsePicks(r.text, pool.map((x) => x.name), config.needs)
        for (const name of parseSkips(r.text, pool.map((x) => x.name))) skips.add(name)
      }
      else notes.push('The small model gave no answer, so no descriptions are proposed.')
    } catch (err) {
      notes.push(`The small model failed (${scrub(home, message(err))}), so no descriptions are proposed.`)
    }
  }

  const plans: Plan[] = candidates(config, installed, reloadHooked, picks.map((x) => x.skill)).map(({ skill, source }) => {
    const current = currentChoice(config.skills[skill])
    const pick = picks.find((x) => x.skill === skill)
    const need = pick ? { need: pick.need } : {}
    if (source === 'hook') return { skill, source, recommended: startHooked.has(skill) ? 'start' : skips.has(skill) ? 'none' : 'need', ...need }
    if (source === 'model') return { skill, source, recommended: 'need', ...need }
    return { skill, source, ...(current === undefined ? {} : { current }), recommended: current ?? (skips.has(skill) ? 'none' : 'need'), ...need }
  })
  const watched = new Set(plans.map((p) => p.skill))
  const unwatched = installed.filter((name) => !watched.has(name))
  const toAsk = plans.filter((p) => p.source !== 'project')

  /** The line for an injected result: the plugin's SessionStart hooks decide which one. */
  const injectedLine = async (skill: string) => injectedWarning(skill, await pluginStartHooks($, home, skill))
  const noDialog = async () => {
    const warnings: string[] = []
    for (const p of toAsk) {
      const line = p.recommended === 'injected' ? await injectedLine(p.skill) : undefined
      if (line) warnings.push(`${p.skill}: ${line}`)
    }
    return withNotes(setupSteps({ plans, userConfig: userDoc, configPath: shown(configPath), unwatched, warnings }), notes)
  }
  const done: string[] = []
  let asked = false
  let wrote = false
  /** The description a dialog shows for "When the task needs it", and whether it is only the fallback. */
  const proposal = (p: Plan): { need: NeedText; fallback: boolean } => {
    if (p.need) return { need: p.need, fallback: false }
    const key = config.skills[p.skill]?.need
    const text = key === undefined ? undefined : config.needs[key]
    if (key !== undefined && text !== undefined) return { need: { key, text }, fallback: false }
    return { need: { key: needKeyFor(p.skill), text: `The task calls for ${p.skill}.` }, fallback: true }
  }

  try {
    for (const [i, p] of toAsk.entries()) {
      const prop = proposal(p)
      const lines = [
        `${describePlan(p)}.`,
        prop.fallback
          ? `No description was proposed, so "When the task needs it" would read: "${prop.need.text}" Text typed under Other replaces it.`
          : `Description for "When the task needs it": ${prop.need.text} Text typed under Other replaces it.`,
        ...(p.skill.includes(':') ? [INJECTED_HELP] : []),
        'How should Souffleur keep it?',
      ]
      const question = `${asked ? '' : `${SETUP_INTRO}\n\n`}${lines.join(' ')}`
      const answer: unknown = await $.ui.ask(question, { options: options(p.skill, p.current, p.recommended), header: 'Souffleur' })
      asked = true
      const picked = typeof answer === 'string' && answer !== '' ? choiceOf(answer) : 'stop'
      if (picked === 'stop') {
        done.push(`Stopped at ${p.skill}; ${plural(toAsk.length - i, 'skill')} not asked.`)
        break
      }
      let choice: LoadChoice
      let need: NeedText | undefined
      if (picked === undefined) {
        const text = cleanNeedText(answer as string)
        if (text === undefined) {
          done.push(`${p.skill}: skipped, a description must be one line of 1 to 200 characters. Nothing was written for it.`)
          continue
        }
        choice = 'need'
        need = { key: prop.need.key, text }
      } else {
        choice = picked
        need = choice === 'need' ? prop.need : undefined
      }

      // Read again: the file may have changed since the scan, and earlier answers are already in it.
      const now2 = await readState($, configPath, home)
      if (now2.kind === 'error') {
        done.push(`Stopped: could not read ${shown(configPath)} (${now2.why}). Nothing was written for ${p.skill}.`)
        break
      }
      if (now2.kind === 'missing' && user.kind === 'ok') {
        done.push(`Stopped: ${shown(configPath)} was there at the start and is not now. Nothing was written for ${p.skill}.`)
        break
      }
      let doc: unknown
      if (now2.kind === 'ok') {
        try {
          doc = parseJson(now2.text)
        } catch (err) {
          done.push(`Stopped: ${shown(configPath)} is not valid JSON now (${message(err)}). Nothing was written for ${p.skill}.`)
          break
        }
        const problem = configProblem(doc)
        if (problem) {
          done.push(`Stopped: ${shown(configPath)} cannot be edited because ${problem}. Nothing was written for ${p.skill}.`)
          break
        }
      }
      const r = applyChoice(doc, p.skill, choice, need, projectSkills)
      if (r.note) done.push(r.note)
      const label = choice === 'none' ? 'not watched' : CHOICE_LABEL[choice]
      if (r.note || JSON.stringify(r.config) === JSON.stringify(doc) || (now2.kind === 'missing' && choice === 'none')) {
        if (!r.note) {
          done.push(`Kept ${p.skill}: ${label}. Nothing was written.`)
          if (choice === 'injected') {
            const line = await injectedLine(p.skill)
            if (line) done.push(line)
          }
        }
        continue
      }
      await $.fs.write(configPath, `${JSON.stringify(r.config, null, 2)}\n`)
      wrote = true
      loaded = undefined // the session reads the new file on its next event
      done.push(`${p.skill}: ${label}.`)
      if (choice === 'injected') {
        const line = await injectedLine(p.skill)
        if (line) done.push(line)
      }
      if (r.pruned?.length) done.push(`Removed the unused ${r.pruned.length === 1 ? 'need' : 'needs'} ${r.pruned.join(', ')}.`)
    }
  } catch (err) {
    if (!asked) return noDialog()
    done.push(`Stopped early: ${scrub(home, message(err))}. Answers given so far are kept.`)
  }
  if (!asked && toAsk.length && !done.length) return noDialog()

  if (wrote) {
    // Apply at once: read the file again, let the running session's ledger follow it, and refresh the status line.
    try {
      loaded = undefined
      const { l, session } = await current($)
      await persist($, l, decide(l.config, session, { type: 'config', now: now(), errors: l.errors }).session)
    } catch (err) {
      notes.push(`The new entries could not be applied to this session (${scrub(home, message(err))}). They apply from the next session start.`)
      wrote = false
    }
    // The skill listing is its own step: when it fails the entries are still applied.
    if (wrote) await safe($, 'installed', undefined, () => refreshInstalled($))
  }

  const out = ['Souffleur init', '', ...(toAsk.length || done.length ? done.map((d) => `- ${d}`) : ['- Nothing to ask: no skill is configured yet and none looks worth watching.'])]
  const project = plans.filter((p) => p.source === 'project')
  if (project.length) out.push('', `Set only in the project file, so init leaves ${project.length === 1 ? 'it' : 'them'} alone: ${project.map((p) => p.skill).join(', ')}.`)
  if (unwatched.length) out.push('', `Installed and not watched: ${unwatched.slice(0, 30).join(', ')}${unwatched.length > 30 ? `, and ${unwatched.length - 30} more` : ''}.`)
  const sure = hooks.filter((o) => !isGuess(o)).length
  const guessed = hooks.length - sure
  if (sure || guessed || passages.length) {
    const found = [plural(sure, 'hook'), plural(passages.length, 'passage')].join(' and ')
    out.push('', `Found ${found} that look like old setup${guessed ? `, and ${guessed} more guessed from script names` : ''}. /souffleur migrate goes through them with you.`)
  }
  if (notes.length) out.push('', 'Notes:', ...notes.map((n) => `- ${n}`))
  if (wrote) out.push('', 'New entries apply to this session now. The default mode is observe: nothing is blocked until you set "mode": "enforce" in the user file.')
  return out.join('\n')
}

/**
 * `/souffleur migrate`: goes through hooks in settings.json that do what Souffleur does, one dialog each.
 * `Turn off` copies settings.json first (never over an older copy) and removes only that entry, and only when the
 * file is still what the edit was based on. Scripts, CLAUDE.md and memory are never edited.
 */
async function runMigrate($: Dollar, l: Loaded): Promise<string> {
  const notes: string[] = []
  const home: string | undefined = await $.env.get('HOME')
  if (!home) return 'Souffleur migrate: the home folder is unknown, so nothing was changed.'
  const settingsPath = `${home}/.claude/settings.json`
  const shown = (path: string) => shownPath(home, path)
  const settings = await readSettings($, settingsPath, home)
  if (settings.error) return `Souffleur migrate: ${settings.error}, so nothing was changed.`

  const files = await readStanding($, l, home, notes)
  const configured = Object.keys(l.config.skills)
  // Only skills of the user file count as watched: a project file's entry works in that project alone.
  const watched = Object.entries(l.config.skills).filter(([, r]) => r.from === 'user').map(([name]) => name)
  const installed = await installedSkills($)
  const hooks: HookOverlap[] = findHookOverlaps(settings.value, configured, installed.filter((n) => !configured.includes(n)))
  const passages: Passage[] = findPassages(files, configured, Infinity)
  const known = { configured, installedOnly: installed.filter((n) => !configured.includes(n)) }

  const { queued: queuedNotes, skipped } = await queuePassages($, passages, new Set(files.filter((f) => f.project).map((f) => f.file)))
  if (queuedNotes.length) notes.push(`${plural(queuedNotes.length, 'passage')} queued as note proposals. /souffleur review asks about them one by one; nothing is written before you say yes.`)
  if (skipped) notes.push(`${passages.length - queuedNotes.length} skipped (${skipped}).`)
  const { session } = await current($)
  for (const o of hooks) {
    for (const name of o.skills ?? []) {
      const note = `${name} is configured but not installed in this session, so Souffleur cannot keep it loaded here. Check before turning the hook off.`
      if (watched.includes(name) && session.ledger[name]?.state === 'not installed here' && !notes.includes(note)) notes.push(note)
    }
  }
  const noDialog = () => withNotes(migrateSteps({ hooks, passages, settingsPath: shown(settingsPath), watched }), notes)
  const done: string[] = []
  const manual: string[] = []
  const label = (o: HookOverlap) => `${o.event} hook ${o.command}`
  let asked = false
  let backedUp = false
  let expected = settings.text // what settings.json should hold; anything else means it changed under us
  try {
    for (const [i, o] of hooks.entries()) {
      const q = hookQuestion(o, watched)
      const question = `${asked ? '' : `${MIGRATE_INTRO}\n\n`}${q.text}`
      const answer: unknown = await $.ui.ask(question, { options: q.options, header: 'Souffleur' })
      asked = true
      if (typeof answer !== 'string' || answer === '' || answer === 'Stop') {
        done.push(`Stopped at the ${label(o)}; ${plural(hooks.length - i, 'hook')} not asked.`)
        break
      }
      if (answer === 'Keep') done.push(`Kept the ${label(o)}.`)
      if (answer === 'Show me what to do') {
        manual.push(hookSteps(o, shown(settingsPath)))
        done.push(`Left the ${label(o)} alone; the steps are below.`)
      }
      if (answer !== 'Turn off') continue
      // Read again: an earlier removal moved the indexes, and the file may have changed since the scan.
      const text: string = await $.fs.read(settingsPath)
      if (expected !== undefined && text !== expected) {
        done.push(`Stopped: ${shown(settingsPath)} changed since it was read. Nothing more was written. Run /souffleur migrate again.`)
        break
      }
      const current: unknown = parseJson(text)
      const target = findHookOverlaps(current, known.configured, known.installedOnly).find((x) => x.event === o.event && x.matcher === o.matcher && x.command === o.command)
      if (!target) {
        done.push(`Already gone: the ${label(o)}.`)
        continue
      }
      if (!backedUp) {
        const backup = await freeBackupPath($, settingsPath)
        try {
          await $.fs.write(backup, text)
        } catch (err) {
          done.push(`Stopped: the backup could not be written (${scrub(home, message(err))}), so ${shown(settingsPath)} was not changed.`)
          break
        }
        backedUp = true
        done.push(`Copied settings to ${shown(backup)}.`)
      }
      const again: string = await $.fs.read(settingsPath)
      if (again !== text) {
        done.push(`Stopped: ${shown(settingsPath)} changed since it was read. Nothing more was written. Run /souffleur migrate again.`)
        break
      }
      const next = `${JSON.stringify(removeHook(current, target), null, 2)}\n`
      await $.fs.write(settingsPath, next)
      expected = next
      done.push(`Turned off the ${label(o)}.`)
    }
  } catch (err) {
    if (!asked) return noDialog()
    done.push(`Stopped early: ${scrub(home, message(err))}.`)
  }
  if (!asked && hooks.length && !done.length) return noDialog()

  const out = [MIGRATE_INTRO, '', ...(hooks.length || done.length ? done.map((d) => `- ${d}`) : ['- Nothing to migrate: no overlapping hooks.'])]
  if (manual.length) out.push('', 'To do by hand:', ...manual.map((m) => `- ${m}`))
  if (passages.length) out.push('', 'Standing instructions that name a configured skill (Souffleur never edits these):', ...passageLines(passages))
  if (notes.length) out.push('', 'Notes:', ...notes.map((n) => `- ${n}`))
  return out.join('\n')
}

// --- Rules, notes and proposals ---

/** The fields `souffleur_propose` takes; anything else on the call is not part of a proposal. */
const PROPOSE_FIELDS = ['kind', 'text', 'need', 'before', 'skill', 'field', 'after', 'evidence']
const PROPOSE_SCHEMA = {
  type: 'object',
  properties: {
    kind: { type: 'string', enum: ['rule', 'note'] },
    source: { type: 'string', enum: ['slip', 'user'], description: '"user" when the user asked for it, "slip" when something went wrong that this would have caught.' },
    text: { type: 'string', description: 'For a note: the instruction, one line.' },
    need: { type: 'string', description: 'For a note: a configured need name, when it only matters for that kind of work.' },
    before: { type: 'object', description: 'For a rule that checks a call: { tools: ["Agent"], paths?: ["src/**"] }. Use with skill or field.' },
    skill: { type: 'string', description: 'The skill that must be loaded before a matching call.' },
    field: { type: 'string', description: 'The argument a matching call must carry, for example model.' },
    after: { type: 'object', description: 'For a rule about what must follow a call: { tools: ["Edit"], paths?: ["src/**"] }. Use with evidence.' },
    evidence: { type: 'object', description: 'What closes an "after" rule: { tool: "Bash", command?: "npm test" } (command is a glob).' },
  },
  required: ['kind'],
}

const REGISTER_PROPOSE = {
  name: 'souffleur_propose',
  description:
    'Propose a rule or a note for Souffleur to keep. Call it when something went wrong that a rule would have caught (a denial, a correction by the user), or when the user asks you to remember a rule or standing instruction. A rule has a trace Souffleur can check: a skill loaded before a call, a field a call carries, or evidence that follows a call. Anything else is a note. Souffleur asks the user before anything is kept; never write the entry into a file yourself.',
  inputSchema: PROPOSE_SCHEMA,
}

/** The session with the declined hashes of earlier sessions added (they live in the plugin store). */
async function withStoredDeclined($: Dollar, s: Session): Promise<Session> {
  try {
    const stored: unknown = await $.store.get(DECLINED_KEY)
    if (!Array.isArray(stored)) return s
    const extra = stored.filter((h): h is string => typeof h === 'string' && !s.declined.includes(h))
    return extra.length ? { ...s, declined: [...s.declined, ...extra] } : s
  } catch {
    return s
  }
}

/**
 * Adds one entry to the user file. Same care as `init`: read fresh, stop on a read error or a file that cannot be edited,
 * write only now (the caller has the user's yes), keep every other key. Returns the user-facing line.
 */
async function writeEntry($: Dollar, kind: 'rule' | 'note', entry: Rule | Note): Promise<{ ok: boolean; text: string; wrote?: boolean }> {
  const home: string | undefined = await $.env.get('HOME')
  if (!home) return { ok: false, text: 'the home folder is unknown, so nothing was written' }
  const path = `${home}/.claude/souffleur.json`
  const st = await readState($, path, home)
  if (st.kind === 'error') return { ok: false, text: `could not read ${shownPath(home, path)} (${st.why}), so nothing was written` }
  let doc: unknown
  if (st.kind === 'ok') {
    try {
      doc = parseJson(st.text)
    } catch (err) {
      return { ok: false, text: `${shownPath(home, path)} is not valid JSON (${scrub(home, message(err))}), so nothing was written` }
    }
    const problem = configProblem(doc)
    if (problem) return { ok: false, text: `${shownPath(home, path)} cannot be edited because ${problem}, so nothing was written` }
  }
  const r = addEntry(doc, kind, entry)
  if (r.note) return { ok: true, text: r.note }
  // Read once more right before the write: another session or the user may have saved the file since.
  const again = await readState($, path, home)
  if (again.kind === 'error' || again.kind !== st.kind || (again.kind === 'ok' && st.kind === 'ok' && again.text !== st.text)) {
    return { ok: false, text: `${shownPath(home, path)} changed since it was read, so nothing was written` }
  }
  await $.fs.write(path, `${JSON.stringify(r.config, null, 2)}\n`)
  return { ok: true, wrote: true, text: `added ${kind} ${entry.id} to ${shownPath(home, path)}${entry.where === undefined ? '' : ` for ${entry.where}`}` }
}

/** The session after a change the core has no event for: read, change, store. */
function update($: Dollar, change: (l: Loaded, s: Session) => Session): Promise<void> {
  return serial(async () => {
    const { l, session } = await current($)
    await persist($, l, change(l, await withStoredDeclined($, session)))
  })
}

/** Applies the user's answer to one waiting proposal: writes after a yes, remembers a no, keeps the proposal when the write fails. */
function commitAnswer($: Dollar, hash: string, label: string): Promise<string> {
  return serial(() => commitAnswerNow($, hash, label))
}

async function commitAnswerNow($: Dollar, hash: string, label: string): Promise<string> {
  const { l, session: before } = await current($)
  const session = await withStoredDeclined($, before)
  const r = answer(l.config, session, hash, label, l.root)
  if (r.note) return r.note
  if (r.write) {
    let w: { ok: boolean; text: string; wrote?: boolean }
    try {
      w = await writeEntry($, r.write.kind, r.write.entry)
    } catch (err) {
      w = { ok: false, text: `writing failed (${scrub(await $.env.get('HOME'), message(err))}), so nothing was written` }
    }
    if (!w.ok) {
      await persist($, l, session)
      return `Souffleur: ${w.text}. The proposal stays queued.`
    }
    loaded = undefined // the file changed: read it again
    const l2 = await getLoaded($)
    await persist($, l2, decide(l2.config, r.session, { type: 'config', now: now(), errors: l2.errors }).session)
    // The file is what counts: confirm that the reader kept the entry before saying it is there.
    const kept = [...l2.config.rules, ...l2.config.notes].some((x) => x.id === r.write!.entry.id)
    if (w.wrote && !kept) {
      const why = l2.errors.filter((m) => m.startsWith('user config')).slice(-2).join('; ')
      return `Souffleur: wrote ${r.write.entry.id} to the file, but the reader did not keep it${why ? ` (${why})` : ''}. Check ~/.claude/souffleur.json.`
    }
    return `Souffleur: ${w.text}.`
  }
  await persist($, l, r.session)
  if (label === NO) {
    try {
      await $.store.set(DECLINED_KEY, r.session.declined.slice(-200))
    } catch {
      // the decline holds for this session even when the store fails
    }
    return 'Souffleur: not added, and it will not be proposed again.'
  }
  return r.revise === undefined ? 'Souffleur: nothing changed.' : 'Souffleur: the model is asked to revise it with your next prompt.'
}

/** One dialog about the first waiting proposal. Returns the line to show, or undefined when nothing was asked or the dialog gave no answer. */
async function askFirst($: Dollar, stopOnFail = false): Promise<string | undefined> {
  if (!interactive) return undefined
  const { session } = await current($)
  const q = nextQuestion(await withStoredDeclined($, session))
  if (!q) return undefined
  let label: unknown
  try {
    label = await $.ui.ask(q.question, { options: q.options, header: 'Souffleur' })
  } catch {
    if (stopOnFail) askStopped = true
    return undefined
  }
  if (typeof label !== 'string' || label.trim() === '') {
    if (stopOnFail) askStopped = true
    return undefined
  }
  return commitAnswer($, q.hash, label)
}

/** Queues a proposal. `from` is `slip` or `user`. */
async function propose($: Dollar, raw: unknown, from: string): Promise<{ status: string; id?: string }> {
  const { l } = await current($)
  const made = makeProposal(raw, from, l.config)
  if (!made.proposal) return { status: `error: ${made.error}` }
  let status = 'queued'
  await update($, (l2, s) => {
    if (s.proposed.length >= MODEL_PROPOSALS) {
      status = 'capped'
      return s
    }
    const r = enqueue(l2.config, s, made.proposal!)
    status = r.status
    return r.status === 'queued' ? { ...r.session, proposed: [...r.session.proposed, made.proposal!.hash] } : r.session
  })
  return { status, id: made.proposal.entry.id }
}

// --- Learning from skill texts ---

/** Skill versions whose read is under way in this process. */
const reading = new Set<string>()
const READ_TIMEOUT_MS = 30_000

type LearnAction = Extract<Action, { kind: 'learn' }>

/**
 * Reads one skill with the small model and queues what it finds. Runs after the hook has answered, so the hook never
 * waits for the model, and every failure ends here. The version is marked done in the plugin store only after its
 * proposals were queued; a call that fails, gets no answer or gives an unusable one counts a failure for that version
 * (three end the tries) and gives the session its read back; a full queue leaves the version unmarked, so a later load tries again.
 */
async function learnFrom($: Dollar, a: LearnAction): Promise<void> {
  if (!interactive) return
  let hash: string | undefined
  let fails = 0
  let claimed = false
  try {
    const first = await current($)
    if (!first.l.setUp || !trusted(a.source, first.l.root, first.l.config)) return
    let fileText: string | undefined
    if (a.path !== undefined) {
      try {
        if (await $.fs.exists(a.path)) fileText = (await $.fs.read(a.path)).slice(0, MAX_SKILL_TEXT)
      } catch {
        // without the file the computed text stands in
      }
    }
    const text = fileText ?? a.text
    hash = skillHash(a.skill, text)
    if (reading.has(hash)) {
      hash = undefined
      return
    }
    reading.add(hash)
    const key = hashKey(hash)
    const l = await serial(async () => {
      const { l, session } = await current($)
      const stored = await $.store.get(key)
      if (!l.setUp || !interactive || !shouldRead(session, l.config, stored)) return undefined
      fails = typeof stored === 'object' && stored !== null && typeof (stored as { fails?: unknown }).fails === 'number' ? (stored as { fails: number }).fails : 0
      await persist($, l, { ...session, skillReads: (session.skillReads ?? 0) + 1 })
      return l
    })
    if (l === undefined) return
    claimed = true
    const nonce = Math.random().toString(36).slice(2, 10)
    const r = await $.model.complete({ model: 'haiku', system: EXTRACT_SYSTEM, prompt: extractPrompt(a.skill, text, nonce), maxTokens: 1500, timeoutMs: READ_TIMEOUT_MS })
    const origin = { name: a.skill, ...(a.source === undefined ? {} : { source: a.source }), ...(a.pluginName === undefined ? {} : { pluginName: a.pluginName }) }
    const found = r.isAnswered ? parseAnswer(r.text, origin, l.config, text) : undefined
    if (found === undefined) throw new Error('no usable answer')
    claimed = false
    let full = false
    if (found.length > 0) await update($, (l2, s) => found.reduce((acc, p) => {
      const q = enqueue(l2.config, acc, p)
      if (q.status === 'full') full = true
      return q.session
    }, s))
    if (!full) await $.store.set(key, { done: true })
  } catch {
    if (claimed && hash !== undefined) {
      try {
        await serial(async () => {
          const { l, session } = await current($)
          await persist($, l, { ...session, skillReads: Math.max(0, (session.skillReads ?? 0) - 1) })
          await $.store.set(hashKey(hash!), { fails: fails + 1 })
        })
      } catch {
        // the version stays as it was
      }
    }
  } finally {
    if (hash !== undefined) reading.delete(hash)
  }
}

/** The model may make this many proposals per session. */
const MODEL_PROPOSALS = 5

const PROPOSE_REPLY: Record<string, string> = {
  duplicate: 'Already a rule or note, or already waiting for the user. Nothing to do.',
  declined: 'The user declined this before. Do not propose it again.',
  capped: 'You made five proposals this session already. The user reviews them with /souffleur review; make no more.',
  full: 'Twenty proposals already wait for the user. Do not propose more until /souffleur review cleared some.',
}

async function runPropose($: Dollar, input: Record<string, unknown>): Promise<string> {
  if (input.agentId !== undefined) return 'Only the main session proposes rules and notes. Tell the main session what went wrong instead.'
  const raw: Record<string, unknown> = {}
  for (const key of PROPOSE_FIELDS) if (input[key] !== undefined) raw[key] = input[key]
  const r = await propose($, raw, input.source === 'slip' ? 'slip' : 'user')
  if (r.status.startsWith('error: ')) return `Not queued: ${r.status.slice(7)}. Fix the call and try again.`
  if (r.status !== 'queued') return PROPOSE_REPLY[r.status] ?? 'Not queued.'
  return interactive && !askStopped
    ? `Queued as ${r.id}. Souffleur asks the user at the end of this turn; do not ask again.`
    : `Queued as ${r.id}. The user reviews it with /souffleur review.`
}

/** `/souffleur rule <text>`: the small model shapes the words into a rule or note; a failure keeps them as a note. */
async function runRule($: Dollar, text: string): Promise<string> {
  if (!text.trim()) return 'Usage: /souffleur rule <what to remember>'
  const { l } = await current($)
  let raw = ''
  try {
    const r = await $.model.complete({ model: 'haiku', prompt: shapePrompt(text, l.config.needs) })
    if (r.isAnswered) raw = r.text
  } catch {
    // the words become a note
  }
  const p = parseShaped(raw, text, l.config)
  let status = 'queued'
  await update($, (l2, s) => {
    const r = enqueue(l2.config, s, p)
    status = r.status
    return r.session
  })
  if (status !== 'queued') return status === 'duplicate' ? 'Souffleur: that is already a rule or note, or already waiting.' : status === 'declined' ? 'Souffleur: you declined this before.' : 'Souffleur: twenty proposals wait already. Run /souffleur review first.'
  const asked = await askFirst($)
  if (asked !== undefined) return asked
  return `Souffleur: queued ${p.kind} ${p.entry.id}: ${describeProposal(p)}. Run /souffleur review to answer, or /souffleur accept ${p.entry.id}.`
}

/** `/souffleur review`: one dialog per waiting proposal; without a dialog the list and the text commands. */
async function runReview($: Dollar): Promise<string> {
  const { session } = await current($)
  if (session.proposals.length === 0) return 'Souffleur: no proposals are waiting.'
  const done: string[] = []
  for (let i = 0; i < 20; i++) {
    const line = await askFirst($)
    if (line === undefined) break
    done.push(line)
  }
  const { session: rest } = await current($)
  const out = [...done]
  if (rest.proposals.length) {
    out.push(done.length ? 'Still waiting:' : 'Waiting for your answer, and no dialog can open here:', ...proposalLines(rest), 'Add one with /souffleur accept <id> (everywhere) or /souffleur accept <id> here (this project only).')
  }
  return out.join('\n')
}

/** `/souffleur accept <id> [here|project]`: the text route for what a dialog would ask. */
async function runAccept($: Dollar, args: string[]): Promise<string> {
  const [id, scope] = args
  const usage = 'Usage: /souffleur accept <id> [here|project]'
  if (!id || args.length > 2 || (scope !== undefined && scope !== 'here' && scope !== 'project')) return usage
  const { session } = await current($)
  const p = findProposal(session, id)
  if (!p) return `Souffleur: no proposal ${id} is waiting.${session.proposals.length ? ` Waiting: ${session.proposals.map((q) => q.entry.id).join(', ')}.` : ''}`
  return commitAnswer($, p.hash, scope === undefined ? YES_EVERYWHERE : YES_PROJECT)
}

/** `/souffleur decline <id>`: the text route for No; the hash is remembered. */
async function runDecline($: Dollar, args: string[]): Promise<string> {
  const [id] = args
  if (!id || args.length > 1) return 'Usage: /souffleur decline <id>'
  const { session } = await current($)
  const p = findProposal(session, id)
  if (!p) return `Souffleur: no proposal ${id} is waiting.`
  return commitAnswer($, p.hash, NO)
}

const SKIP_WORDS: Record<string, string> = { short: 'too short', invalid: 'not valid as a note', duplicate: 'already known or waiting', declined: 'declined before', full: 'queue full' }

/** Standing instructions `migrate` found become note proposals with their file and line. Returns the ids queued and why the rest were skipped. */
async function queuePassages($: Dollar, passages: Passage[], projectFiles: Set<string>): Promise<{ queued: string[]; skipped: string }> {
  const queued: string[] = []
  const counts: Record<string, number> = {}
  const skip = (why: string) => void (counts[why] = (counts[why] ?? 0) + 1)
  if (!passages.length) return { queued, skipped: '' }
  await update($, (l, s) => {
    let next = s
    for (const p of passages) {
      const text = p.text.replace(/^[\s>#*\-\d.]+/, '').trim()
      if (text.length < 8) {
        skip('short')
        continue
      }
      const made = makeProposal({ kind: 'note', text }, 'user', l.config)
      if (!made.proposal) {
        skip('invalid')
        continue
      }
      const r = enqueue(l.config, next, { ...made.proposal, origin: `${p.file}:${p.line}`, project: projectFiles.has(p.file) })
      if (r.status === 'queued') queued.push(made.proposal.entry.id)
      else skip(r.status)
      next = r.session
    }
    return next
  })
  const skipped = Object.entries(counts).map(([why, n]) => `${n} ${SKIP_WORDS[why] ?? why}`).join(', ')
  return { queued, skipped }
}

export const register: Register = (on) => {
  on('session.start', async ($, e, next) => {
    await safe($, 'session.start', undefined, async () => {
      loaded = undefined
      const l = await getLoaded($)
      const id: string = await $.session.id()
      const version = (await $.session.version()).version
      const held: Session | undefined = (await $.state.get(REF)).value
      const stored = held?.id === id ? undefined : await $.store.get(`session:${id}`)
      const before = held?.id === id ? held : isSession(stored, id) ? stored : undefined
      let s: Session
      if (before) {
        // Resume or reload: the ledger stays, what the config said last time does not.
        s = decide(l.config, { ...before, errors: [] }, { type: 'start', now: now(), start: 'resume', version }).session
        s = decide(l.config, s, { type: 'config', now: now(), errors: l.errors }).session
      } else s = await freshSession($, l, id, 'startup')
      await persist($, l, s)
    })
    await safe($, 'installed', undefined, () => refreshInstalled($))
    await safe($, 'command.register', undefined, async () => {
      await $.command.register({ name: 'souffleur', description: 'Show which skills Souffleur keeps loaded', argumentHint: '[status | need <name> | drop <name> | pause | init | migrate | rule <text> | review | accept <id> | decline <id>]' })
    })
    interactive = e.isInteractive === true
    askStopped = false
    proposeReady = false
    try {
      await $.tool.register(REGISTER_PROPOSE)
      proposeReady = true
    } catch {
      // The tool does not reach the model: the system prompt leaves out the sentence about it, and /souffleur rule stays.
    }
    return next(e)
  })

  on('skill.prompt', async ($, e, next) => {
    await safe($, 'skill.prompt', undefined, async () => {
      const { actions } = await apply($, () => ({ type: 'skill', now: now(), skill: e.skill, text: e.text, ...(e.source === undefined ? {} : { source: e.source }), ...(e.pluginName === undefined ? {} : { pluginName: e.pluginName }), ...(e.path === undefined ? {} : { path: e.path }) }))
      for (const a of actions) if (a.kind === 'learn') void learnFrom($, a)
    })
    return next(e)
  })

  on('session.compact', async ($, e, next) => {
    const agentId = e.agentId === undefined ? {} : { agentId: e.agentId }
    await safe($, 'session.compact', undefined, async () => {
      await apply($, () => ({ type: 'compact', now: now(), phase: 'before', trigger: e.trigger, ...agentId }))
    })
    // The engine always sends the messages; the test kit's compaction call sends none, and next() refuses that.
    const r = await next(Array.isArray(e.messages) ? e : { ...e, messages: [{ role: 'user' as const, text: '', toolUses: [] }] })
    await safe($, 'session.compact', undefined, async () => {
      const skipped = 'skip' in r && r.skip !== undefined
      await apply($, () => ({ type: 'compact', now: now(), phase: 'after', trigger: e.trigger, skipped, ...agentId }))
    })
    return r
  }).catch(($, e, next) => next(e))

  on('prompt.submit', async ($, e, next) => {
    const fromUser = isFromUser(e)
    const texts = await safe($, 'prompt.submit', [] as string[], async () => {
      const { config } = await getLoaded($)
      // The skill listing runs beside the classification and gives up after its own short budget.
      const listing = fromUser ? safe($, 'installed', undefined, () => refreshInstalled($)) : undefined
      const matched =
        fromUser && Object.keys(config.needs).length > 0
          ? await classifyPrompt(
              e.text,
              config.needs,
              async (text, labels) => (await $.model.classify(text, labels)) ?? '',
              (ms) => $.clock.sleep(ms),
            )
          : []
      await listing
      const { actions } = await apply($, (l) => ({ type: 'prompt', now: now(), text: e.text, fromUser, matched, root: l.root }))
      return actions.flatMap((a) => (a.kind === 'context' ? [a.text] : []))
    })
    return texts.length ? next({ ...e, context: [...(e.context ?? []), ...texts] }) : next(e)
  }).catch(($, e, next) => next(e))

  on('prompt.compose', async ($, e, next) => {
    const r = await next(e)
    const text = await safe($, 'prompt.compose', undefined as string | undefined, async () => {
      const { l, session } = await current($)
      const always = Object.entries(l.config.skills)
        .filter(([name, rule]) => rule.always === true && session.ledger[name]?.state !== 'not installed here')
        .map(([name]) => name)
      const notes = sectionNotes(l.config, l.root).text
      return `${RULE}${always.length ? ` Always-on skills: ${always.join(', ')}.` : ''}${proposeReady && l.setUp ? PROPOSE_SENTENCE : ''}${notes ? `\n\n${notes}` : ''}`
    })
    return text === undefined ? r : { ...r, sections: [...r.sections, { id: 'souffleur', scope: 'session' as const, text }] }
  })

  on('tool.call', async ($, e, next) => {
    const actions = await safe($, 'tool.call', [] as Action[], async () => {
      const fields = toolFields(e)
      const r = await apply($, (l) => ({
        type: 'tool',
        now: now(),
        tool: e.tool,
        ...fields,
        present: Object.entries(e).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k]) => k),
        ...(e.agentId === undefined ? {} : { agentId: e.agentId }),
        root: l.root,
        tree: l.tree,
      }))
      return r.actions
    })
    const deny = actions.find((a) => a.kind === 'deny')
    if (deny) return { deny: deny.reason }
    let r
    try {
      r = await next(e)
    } finally {
      if (e.tool === 'Agent' && e.agentId === undefined) {
        await safe($, 'tool.call', undefined, async () => {
          await apply($, () => ({ type: 'agentDone', now: now() }))
        })
      }
    }
    const extra = actions.flatMap((a) => (a.kind === 'toolContext' ? [a.text] : []))
    if (!extra.length || r.deny !== undefined) return r
    return { ...r, context: [...(r.context ?? []), ...extra] }
  }).catch(($, e, next) => next(e))

  on('tool.run', { tool: PROPOSE_TOOL }, async ($, e) => {
    const text = await safe($, 'souffleur_propose', 'Souffleur could not queue the proposal. Tell the user and carry on.', () => runPropose($, e as unknown as Record<string, unknown>))
    return { result: text }
  })

  // At the end of a turn: one question about the first waiting proposal, in a session with a person at the prompt.
  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    if (e.agentId === undefined && e.reason === 'answer' && interactive && !askStopped) {
      await safe($, 'turn.complete', undefined, async () => {
        const line = await askFirst($, true)
        if (line !== undefined) {
          try {
            $.ui.toast(line)
          } catch {
            // a toast is a courtesy
          }
        }
      })
    }
    return r
  })

  on('command.run', async ($, e, next) => {
    if (e.command === 'souffleur') {
      const verb0 = (e.args ?? '').trim().split(/\s+/)[0]
      if (verb0 === 'init' || verb0 === 'migrate') {
        const text = await safe($, 'command.run', undefined as string | undefined, async () => {
          loaded = undefined // read the files again: another session may have changed them
          const { l } = await current($)
          return verb0 === 'init' ? runInit($, l) : runMigrate($, l)
        })
        if (text !== undefined) return { text }
        return next(e)
      }
      if (verb0 === 'rule' || verb0 === 'review' || verb0 === 'accept' || verb0 === 'decline') {
        if (!isUserOrigin(e)) return { text: `Souffleur: only the user can run /souffleur ${verb0}; a plugin or the model cannot.` }
        const rest = (e.args ?? '').trim().slice(verb0.length).trim()
        const text = await safe($, 'command.run', undefined as string | undefined, async () => {
          loaded = undefined
          return verb0 === 'rule' ? runRule($, rest) : verb0 === 'review' ? runReview($) : verb0 === 'accept' ? runAccept($, rest.split(/\s+/).filter(Boolean)) : runDecline($, rest.split(/\s+/).filter(Boolean))
        })
        if (text !== undefined) return { text }
        return next(e)
      }
      const reply = await safe($, 'command.run', undefined as string | undefined, async () => {
        const { actions, l } = await apply($, (l0) => ({ type: 'command', now: now(), args: e.args ?? '', root: l0.root }))
        const text = actions.flatMap((a) => (a.kind === 'reply' ? [a.text] : []))[0]
        const verb = (e.args ?? '').trim().split(/\s+/)[0] ?? ''
        const note = '\n\nSouffleur is not set up: there is no ~/.claude/souffleur.json. Run /souffleur init to add one.'
        return text !== undefined && !l.setUp && (verb === '' || verb === 'status') ? `${text}${note}` : text
      })
      if (reply !== undefined) return { text: reply }
      return next(e)
    }
    await safe($, 'command.run', undefined, async () => {
      await apply($, () => ({ type: 'typed', now: now(), name: e.command }))
    })
    return next(e)
  }).catch(($, e, next) => next(e))
}
