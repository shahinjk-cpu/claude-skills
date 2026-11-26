/** What `/souffleur migrate` works with. Pure functions only: the adapter reads, asks and writes. */

/** `skill` is the first skill the hook names, `skills` all of them. */
export type HookOverlap = { event: string; matcher?: string; command: string; index: [number, number]; why: string; skill?: string; skills?: string[] }
export type Passage = { file: string; line: number; text: string }

const MAX_PASSAGES = 20
const MAX_LINE = 120
/** A line that reads like an instruction to load or remind of a skill. */
const LOADING_WORDS = /\b(load|invoke|preload|reload|remind|inject|hook)/i
/** A script name that does the job Souffleur does. */
const RELOAD_SCRIPT = /(preload|reload|inject)/i

export const MIGRATE_INTRO = [
  'Souffleur migrate looks for old setup that does what Souffleur now does: hooks in ~/.claude/settings.json that load skills or remind the model of them, and lines in your CLAUDE.md files and memory index that say the same.',
  'It asks one question per hook. Turn off makes a backup copy of settings.json and then removes only that hook entry. Keep leaves it alone. Show me what to do changes nothing and adds the manual steps to the final report.',
  'Hook scripts, CLAUDE.md and memory files are never edited. Passages are listed with file and line, and you decide what to do with them.',
].join('\n\n')

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const isWordChar = (c: string | undefined) => c !== undefined && /[A-Za-z0-9]/.test(c)

/**
 * True when `text` names `skill` (a script name like `skill-x-reload.sh` counts; letters or digits around it do not). A plugin skill `plugin:name` also counts by its
 * part after the colon. With `allowShort` false, names shorter than 5 characters without `-` or `:` (`init`, `run`, `pdf`)
 * never count: they are too common in ordinary commands (`git init`). A skill the user configured passes `allowShort`.
 */
function names(text: string, skill: string, allowShort: boolean): boolean {
  const forms = [skill]
  const bare = skill.split(':').pop()
  if (bare !== undefined && bare !== skill) forms.push(bare)
  return forms.some((form) => {
    if (!allowShort && form.length < 5 && !/[-:]/.test(form)) return false
    for (let at = text.indexOf(form); at !== -1; at = text.indexOf(form, at + 1)) {
      if (!isWordChar(text[at - 1]) && !isWordChar(text[at + form.length])) return true
    }
    return false
  })
}

/** Every one of the user's configured `skills` that `text` names. */
const namedSkills = (text: string, skills: string[]): string[] => skills.filter((s) => names(text, s, true))

const tokens = (command: string) => command.split(/\s+/).map((t) => t.replace(/^["']+|["']+$/g, '')).filter((t) => t !== '' && !t.includes('://'))

/**
 * The installed skill (not configured) a command points at: its full `plugin:skill` name, or its name inside a
 * script file name (a token with `/` or `.`). Plain words never count, so `notify-send "ready for review"` is not about a skill `review`.
 */
function installedMatches(command: string, installedOnly: string[]): string[] {
  const files = tokens(command).filter((t) => /[/.]/.test(t))
  return installedOnly.filter((skill) => (skill.includes(':') && command.includes(skill)) || files.some((t) => names(t, skill, false)))
}

/** A configured skill named by a script file name (a token with `/` or `.`) or by its full `plugin:skill` name: a firm match. A bare word is only a guess. */
function firmlyNamed(command: string, skill: string): boolean {
  if (skill.includes(':') && command.includes(skill)) return true
  return tokens(command).some((t) => /[/.]/.test(t) && names(t, skill, true))
}

export const isGuess = (o: HookOverlap): boolean => o.why.startsWith('guess:')

/** The `preload`, `reload` or `inject` in the name of a script in `command`. Needs a script extension or a `hooks/` path; URLs and bare words do not count. */
function scriptName(command: string): string | undefined {
  for (const token of tokens(command)) {
    if (!/\.(sh|js|mjs|ts|py)$/i.test(token) && !token.includes('hooks/')) continue
    const name = token.slice(token.lastIndexOf('/') + 1)
    const hit = RELOAD_SCRIPT.exec(name)?.[1]
    if (hit !== undefined) return hit.toLowerCase()
  }
  return undefined
}

/**
 * Finds settings hooks that do what Souffleur does. A hook entry overlaps when
 *  1. its command or its matcher names a configured skill, or points at an installed one by its full
 *     `plugin:skill` name or inside a script file name (then `why` starts with `guess:`), or
 *  2. it runs a script whose name contains `preload`, `reload` or `inject`, even when the skill it
 *     serves is not installed. `why` then starts with `guess:`.
 * The rules err toward listing; the user decides per hook and nothing changes without a yes.
 * `index` is `[group, hook]` inside `hooks[event]`.
 */
export function findHookOverlaps(settings: unknown, configured: string[], installedOnly: string[] = []): HookOverlap[] {
  if (!isObject(settings) || !isObject(settings.hooks)) return []
  const found: HookOverlap[] = []
  for (const [event, groups] of Object.entries(settings.hooks)) {
    if (!Array.isArray(groups)) continue
    groups.forEach((group, g) => {
      if (!isObject(group) || !Array.isArray(group.hooks)) return
      const matcher = typeof group.matcher === 'string' ? group.matcher : undefined
      group.hooks.forEach((hook, h) => {
        if (!isObject(hook) || typeof hook.command !== 'string') return
        const command = hook.command
        const inMatcher = matcher === undefined ? [] : namedSkills(matcher, configured)
        const inCommand = namedSkills(command, configured)
        const bySkill = [...new Set([...inCommand, ...inMatcher])]
        const byInstalled = bySkill.length === 0 ? installedMatches(command, installedOnly) : []
        const word = scriptName(command)
        let why: string | undefined
        if (bySkill.length) {
          const firm = bySkill.every((x) => inMatcher.includes(x) || firmlyNamed(command, x))
          why = firm ? `names the skill ${bySkill.join(', ')}` : `guess: the command mentions ${bySkill.join(', ')}`
        } else if (byInstalled.length) why = `guess: the script name contains ${byInstalled.join(', ')}`
        else if (word !== undefined) why = `guess: the script name contains ${word}`
        if (why === undefined) return
        const skills = bySkill.length ? bySkill : byInstalled
        found.push({ event, ...(matcher === undefined ? {} : { matcher }), command, index: [g, h], why, ...(skills.length ? { skill: skills[0]!, skills } : {}) })
      })
    })
  }
  return found
}

/** A copy of `settings` without exactly the hook `o` names; emptied groups and events go too. Unchanged when the entry no longer matches. */
export function removeHook(settings: unknown, o: HookOverlap): unknown {
  if (!isObject(settings) || !isObject(settings.hooks)) return settings
  const groups = settings.hooks[o.event]
  const [g, h] = o.index
  const group = Array.isArray(groups) ? groups[g] : undefined
  const hook = isObject(group) && Array.isArray(group.hooks) ? group.hooks[h] : undefined
  if (!isObject(group) || !Array.isArray(group.hooks) || !isObject(hook) || hook.command !== o.command) return settings
  const left = group.hooks.filter((_: unknown, i: number) => i !== h)
  const nextGroups = (groups as unknown[]).flatMap((x, i) => (i !== g ? [x] : left.length ? [{ ...group, hooks: left }] : []))
  const hooks: Record<string, unknown> = {}
  for (const [event, value] of Object.entries(settings.hooks)) {
    if (event !== o.event) hooks[event] = value
    else if (nextGroups.length) hooks[event] = nextGroups
  }
  const { hooks: _old, ...rest } = settings
  return { ...rest, hooks }
}

/** Lines of CLAUDE.md or memory text that name a configured skill and read like a loading or reminding instruction, with file and line, at most `max` (20). Never edited. */
export function findPassages(files: { file: string; text: string }[], configuredSkills: string[], max = MAX_PASSAGES): Passage[] {
  const out: Passage[] = []
  for (const { file, text } of files) {
    const lines = text.split(/\r\n|\r|\n/)
    for (let i = 0; i < lines.length && out.length < max; i++) {
      const line = lines[i]!.trim()
      if (line && LOADING_WORDS.test(line) && namedSkills(line, configuredSkills).length > 0) out.push({ file, line: i + 1, text: line.length > MAX_LINE ? `${line.slice(0, MAX_LINE)}...` : line })
    }
  }
  return out
}

/** Report lines for passages: the first 20, then how many more there are. */
export function passageLines(passages: Passage[], max = MAX_PASSAGES): string[] {
  const lines = passages.slice(0, max).map((p) => `- ${p.file}:${p.line} ${p.text}`)
  return passages.length > max ? [...lines, `- and ${passages.length - max} more`] : lines
}

export const describeHook = (o: HookOverlap): string => `${o.event}${o.matcher === undefined ? '' : ` [${o.matcher}]`}: ${o.command} (${o.why})`

/**
 * A warning when turning the hook off could leave something without reminders: a skill it names is not in `watched`
 * (the skills of the user file), the match is only a guess, or the hook names no skill at all, so it may serve a skill
 * of another project or a rules file.
 */
export function watchWarning(o: HookOverlap, watched: string[]): string | undefined {
  const named = o.skills ?? (o.skill === undefined ? [] : [o.skill])
  const unwatched = named.filter((x) => !watched.includes(x))
  if (unwatched.length) return `Souffleur does not watch ${unwatched.join(', ')} yet; turning this off leaves ${unwatched.length === 1 ? 'it' : 'them'} without reminders.`
  if (!isGuess(o)) return undefined
  return 'Souffleur cannot tell which skill this reloads. If it serves a skill of another project or a rules file, Souffleur does not watch it, and turning this off leaves it without reminders.'
}

/** The dialog for one hook. With a warning, `Keep` comes first and the question gives the warning instead of the claim that Souffleur does the job. */
export function hookQuestion(o: HookOverlap, watched: string[]): { text: string; options: string[] } {
  const warning = watchWarning(o, watched)
  const rest = ['Show me what to do', 'Stop']
  return warning === undefined
    ? { text: `Turn off the ${describeHook(o)} hook? Souffleur now does this job.`, options: ['Turn off', 'Keep', ...rest] }
    : { text: `${warning} Turn off the ${describeHook(o)} hook?`, options: ['Keep', 'Turn off', ...rest] }
}

/** Manual steps for one hook, for the `Show me what to do` answer and the no-dialog text. */
export const hookSteps = (o: HookOverlap, settingsPath: string): string =>
  `Remove the ${o.event} hook "${o.command}" from ${settingsPath} (copy the file first). If the script is only used for this, delete it too.`

/** The text `/souffleur migrate` returns when it cannot ask: the explanation, hooks and steps; nothing is changed. */
export function migrateSteps(a: { hooks: HookOverlap[]; passages: Passage[]; settingsPath: string; watched?: string[] }): string {
  const out = [MIGRATE_INTRO, '', 'No dialog is available here, so nothing was changed.', '']
  if (a.hooks.length) out.push('Hooks that do what Souffleur now does:', ...a.hooks.map((o) => {
      const warning = a.watched === undefined ? undefined : watchWarning(o, a.watched)
      return `- ${describeHook(o)}${warning === undefined ? '' : ` Warning: ${warning}`}`
    }), '')
  else out.push('No overlapping hooks found.', '')
  if (a.passages.length) out.push('Standing instructions that name a configured skill (Souffleur never edits these):', ...passageLines(a.passages), '')
  out.push('Steps:')
  let n = 1
  for (const o of a.hooks) out.push(`${n++}. ${hookSteps(o, a.settingsPath)}`)
  if (a.passages.length) out.push(`${n++}. Decide whether the passages above still belong in your instructions once Souffleur keeps the skills loaded.`)
  out.push(`${n}. Run /souffleur in a new session to check the ledger. Run /souffleur migrate in a session with a dialog to let it make these changes with your yes on each.`)
  return out.join('\n')
}
