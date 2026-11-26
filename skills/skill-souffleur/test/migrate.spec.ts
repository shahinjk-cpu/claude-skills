import { test } from 'node:test'
import assert from 'node:assert/strict'
import { MIGRATE_INTRO, findHookOverlaps, findPassages, hookQuestion, migrateSteps, passageLines, removeHook, watchWarning } from '../src/core/migrate.ts'

const SKILLS = ['writing-guide', 'ui-checklist', 'terse:terse-mode']

const settings = () => ({
  model: 'opus',
  hooks: {
    SessionStart: [
      { matcher: 'compact|resume', hooks: [{ type: 'command', command: 'bash ~/.claude/hooks/writing-guide-reload.sh' }] },
      { matcher: 'startup', hooks: [{ type: 'command', command: 'notify-send started' }] },
    ],
    UserPromptSubmit: [
      { hooks: [{ type: 'command', command: '~/.claude/hooks/remind.sh ui-checklist' }, { type: 'command', command: 'date >> ~/log.txt' }] },
    ],
    PostToolUse: [{ matcher: 'Bash', hooks: [{ type: 'command', command: 'prettier --write .' }] }],
  },
})

test('finds a SessionStart hook that re-injects a known skill', () => {
  const found = findHookOverlaps(settings(), SKILLS)
  const start = found.find((o) => o.event === 'SessionStart')
  assert.ok(start)
  assert.equal(start.command, 'bash ~/.claude/hooks/writing-guide-reload.sh')
  assert.equal(start.matcher, 'compact|resume')
  assert.deepEqual(start.index, [0, 0])
  assert.match(start.why, /writing-guide/)
  const prompt = found.find((o) => o.event === 'UserPromptSubmit')
  assert.deepEqual(prompt?.index, [0, 0])
})

test('finds a preload script by its name pattern even without a known skill name', () => {
  const s = { hooks: { SessionStart: [{ hooks: [{ type: 'command', command: '~/.claude/hooks/skill-preload.sh' }] }] } }
  const found = findHookOverlaps(s, [])
  assert.equal(found.length, 1)
  assert.match(found[0]!.why, /preload/)
})

test('ignores unrelated hooks', () => {
  const s = {
    hooks: {
      SessionStart: [{ hooks: [{ type: 'command', command: 'notify-send started' }] }],
      PostToolUse: [{ matcher: 'Bash', hooks: [{ type: 'command', command: 'prettier --write .' }] }],
      Stop: [{ hooks: [{ type: 'command', command: 'echo reload the page' }] }],
    },
  }
  assert.deepEqual(findHookOverlaps(s, SKILLS), [])
  assert.deepEqual(findHookOverlaps(undefined, SKILLS), [])
  assert.deepEqual(findHookOverlaps({ hooks: 'nope' }, SKILLS), [])
})

test('a short skill name inside another word is not an overlap', () => {
  assert.deepEqual(findHookOverlaps({ hooks: { Stop: [{ hooks: [{ type: 'command', command: 'git init' }] }] } }, [], ['init']), [])
})

test('removeHook removes only that entry and keeps the rest byte-equal in content', () => {
  const before = settings()
  const frozen = structuredClone(before)
  const target = findHookOverlaps(before, SKILLS).find((o) => o.event === 'UserPromptSubmit')!
  const after = removeHook(before, target) as ReturnType<typeof settings>
  assert.deepEqual(before, frozen, 'the input is not changed')
  assert.deepEqual(after.hooks.UserPromptSubmit, [{ hooks: [{ type: 'command', command: 'date >> ~/log.txt' }] }])
  assert.deepEqual(after.hooks.SessionStart, frozen.hooks.SessionStart)
  assert.deepEqual(after.hooks.PostToolUse, frozen.hooks.PostToolUse)
  assert.equal(after.model, 'opus')
})

test('removeHook drops an emptied matcher group', () => {
  const before = settings()
  const target = findHookOverlaps(before, SKILLS).find((o) => o.event === 'SessionStart')!
  const after = removeHook(before, target) as ReturnType<typeof settings>
  assert.deepEqual(after.hooks.SessionStart, [{ matcher: 'startup', hooks: [{ type: 'command', command: 'notify-send started' }] }])
})

test('removeHook drops an emptied event, and leaves settings alone when the entry changed', () => {
  const only = { hooks: { SessionStart: [{ hooks: [{ type: 'command', command: 'writing-guide-reload.sh' }] }] }, theme: 'dark' }
  const target = findHookOverlaps(only, SKILLS)[0]!
  assert.deepEqual(removeHook(only, target), { theme: 'dark', hooks: {} })
  const edited = { hooks: { SessionStart: [{ hooks: [{ type: 'command', command: 'something else' }] }] } }
  assert.deepEqual(removeHook(edited, target), edited)
})

test('guess rule flags preload style scripts of skills that are not installed', () => {
  const s = {
    hooks: {
      UserPromptSubmit: [{ hooks: [{ type: 'command', command: 'bash ~/.claude/hooks/old-skill-preload.sh' }] }],
      PostToolUse: [{ matcher: 'Skill', hooks: [{ type: 'command', command: 'bash ~/.claude/hooks/old-skill-preload.sh' }] }],
      SessionStart: [{ matcher: 'compact|resume|clear', hooks: [{ type: 'command', command: 'bash ~/.claude/hooks/context-reload.sh' }] }],
    },
  }
  const found = findHookOverlaps(s, SKILLS)
  assert.equal(found.length, 3)
  for (const o of found) assert.match(o.why, /^guess:/)
  assert.equal(found.find((o) => o.event === 'PostToolUse')?.matcher, 'Skill')
})

test('a hook whose script file or matcher names a skill is not a guess; a bare word is', () => {
  const found = findHookOverlaps(settings(), SKILLS)
  assert.ok(found.length > 0)
  for (const o of found) {
    const bareWord = o.command.includes('remind.sh ui-checklist')
    assert.equal(/^guess:/.test(o.why), bareWord, o.command)
  }
})

test('a hook that names several skills lists them all and warns when any is unwatched', () => {
  const [o] = findHookOverlaps(one('bash ~/h/writing-guide-ui-checklist.sh'), SKILLS)
  assert.deepEqual(o!.skills, ['writing-guide', 'ui-checklist'])
  assert.match(watchWarning(o!, ['writing-guide'])!, /does not watch ui-checklist yet/)
  assert.equal(watchWarning(o!, ['writing-guide', 'ui-checklist']), undefined)
})

test('a hook that names a watched skill only as a bare word gets the cannot-tell warning', () => {
  const [o] = findHookOverlaps(one('echo writing-guide'), SKILLS)
  assert.match(o!.why, /^guess: /)
  assert.match(watchWarning(o!, ['writing-guide'])!, /cannot tell/)
})

test('guess rule needs a script name, not a bare word', () => {
  const s = { hooks: { Stop: [{ hooks: [{ type: 'command', command: 'echo inject the milk' }, { type: 'command', command: 'npm run reload' }] }] } }
  assert.deepEqual(findHookOverlaps(s, SKILLS), [])
})

test('passages only for configured skills with loading words', () => {
  const text = [
    'Use pdf tools for forms.',
    'Always load writing-guide first.',
    'The writing-guide skill is long.',
    'The hook reminds the model about ui-checklist.',
    'Run xlsx-helper to load a sheet.',
  ].join('\n')
  const got = findPassages([{ file: 'CLAUDE.md', text }], ['writing-guide', 'ui-checklist'])
  assert.deepEqual(
    got.map((p) => p.line),
    [2, 4],
  )
})

test('findPassages lists file and line of text that names a skill', () => {
  const got = findPassages([{ file: 'CLAUDE.md', text: 'one\nAlways load writing-guide first.\nthree' }], SKILLS)
  assert.deepEqual(got, [{ file: 'CLAUDE.md', line: 2, text: 'Always load writing-guide first.' }])
})

test('MIGRATE_INTRO says what it does, what each answer does, and what it never edits', () => {
  assert.match(MIGRATE_INTRO, /Turn off/)
  assert.match(MIGRATE_INTRO, /Keep/)
  assert.match(MIGRATE_INTRO, /Show me what to do/)
  assert.match(MIGRATE_INTRO, /backup/i)
  assert.match(MIGRATE_INTRO, /CLAUDE\.md/)
  assert.doesNotMatch(MIGRATE_INTRO, /[\u2013\u2014]/)
})

test('migrateSteps starts with the explanation and lists hooks and steps for the no-dialog case', () => {
  const text = migrateSteps({
    hooks: findHookOverlaps(settings(), SKILLS),
    passages: [{ file: 'CLAUDE.md', line: 2, text: 'Always load writing-guide first.' }],
    settingsPath: '~/.claude/settings.json',
  })
  assert.ok(text.startsWith(MIGRATE_INTRO))
  assert.match(text, /nothing was changed/i)
  assert.match(text, /writing-guide-reload\.sh/)
  assert.match(text, /CLAUDE\.md:2/)
  assert.match(text, /Steps/)
})

const one = (command: string, event = 'Stop') => ({ hooks: { [event]: [{ hooks: [{ type: 'command', command }] }] } })

test('installed but unconfigured names do not match plain words, and guesses stay guesses', () => {
  const installed = ['review', 'brief', 'config', 'schedule']
  assert.deepEqual(findHookOverlaps(one('notify-send "ready for review"'), [], installed), [])
  assert.deepEqual(findHookOverlaps(one('git status --brief'), [], installed), [])
  for (const command of ['~/bin/update-config.sh', 'python3 ~/.claude/hooks/schedule-guard.py']) {
    for (const o of findHookOverlaps(one(command), [], installed)) assert.match(o.why, /^guess:/)
  }
})

test('an installed plugin skill counts by its full name or inside a script file name, as a guess', () => {
  const full = findHookOverlaps(one('run-skill terse:terse-mode'), [], ['terse:terse-mode'])
  assert.equal(full.length, 1)
  assert.match(full[0]!.why, /^guess:/)
  assert.equal(full[0]!.skill, 'terse:terse-mode')
  const script = findHookOverlaps(one('bash ~/hooks/writing-guide-run.sh'), [], ['writing-guide'])
  assert.match(script[0]!.why, /^guess:/)
  assert.deepEqual(findHookOverlaps(one('echo writing-guide'), [], ['writing-guide']), [])
})

test('short configured names match, short installed names do not', () => {
  const s = one('bash ~/hooks/pdf.sh')
  assert.match(findHookOverlaps(s, ['pdf'], [])[0]!.why, /^names the skill pdf/)
  assert.deepEqual(findHookOverlaps(s, [], ['pdf']), [])
})

test('guess rule skips URLs and needs a script extension or a hooks folder', () => {
  assert.deepEqual(findHookOverlaps(one('curl https://example.com/reload.sh'), [], []), [])
  assert.deepEqual(findHookOverlaps(one('bash ~/x/reload'), [], []), [])
  assert.equal(findHookOverlaps(one('~/.claude/hooks/preload'), [], []).length, 1)
  assert.equal(findHookOverlaps(one('node ~/x/inject.mjs'), [], []).length, 1)
})

test('passageLines cuts at 20 and says how many more', () => {
  const many = Array.from({ length: 25 }, (_, i) => ({ file: 'CLAUDE.md', line: i + 1, text: 'load writing-guide' }))
  const lines = passageLines(many)
  assert.equal(lines.length, 21)
  assert.match(lines.at(-1)!, /and 5 more/)
  assert.equal(passageLines(many.slice(0, 3)).length, 3)
})

test('watchWarning names a skill Souffleur does not watch, and a hook whose skill is unknown', () => {
  const o = (command: string, why: string, skill?: string) => ({ event: 'UserPromptSubmit', command, index: [0, 0] as [number, number], why, ...(skill === undefined ? {} : { skill }) })
  assert.equal(watchWarning(o('x writing-guide', 'names the skill writing-guide', 'writing-guide'), ['writing-guide']), undefined)
  assert.match(watchWarning(o('~/h/review-preload.sh', 'guess: the script name contains review', 'review'), ['writing-guide'])!, /does not watch review yet; turning this off leaves it without reminders/)
  assert.match(watchWarning(o('~/h/rules-preload.sh', 'guess: the script name contains preload'), ['writing-guide'])!, /rules file/)
})

test('hookQuestion puts Keep first when there is a warning and Turn off first otherwise', () => {
  const o = { event: 'UserPromptSubmit', command: '~/h/rules-preload.sh', index: [0, 0] as [number, number], why: 'guess: the script name contains preload' }
  const warned = hookQuestion(o, ['writing-guide'])
  assert.deepEqual(warned.options, ['Keep', 'Turn off', 'Show me what to do', 'Stop'])
  assert.match(warned.text, /without reminders/)
  const named = { ...o, why: 'names the skill writing-guide', skill: 'writing-guide' }
  assert.deepEqual(hookQuestion(named, ['writing-guide']).options, ['Turn off', 'Keep', 'Show me what to do', 'Stop'])
})

test('migrateSteps shows the warning next to the hook', () => {
  const o = { event: 'UserPromptSubmit', command: '~/h/rules-preload.sh', index: [0, 0] as [number, number], why: 'guess: the script name contains preload' }
  assert.match(migrateSteps({ hooks: [o], passages: [], settingsPath: '~/s.json', watched: ['writing-guide'] }), /Warning: .*without reminders/)
})
