import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseConfig } from '../src/core/config.ts'
import { decide, initSession } from '../src/core/decide.ts'
import type { Action, CoreEvent, Session } from '../src/core/decide.ts'
import { NOTE_CAP, sectionNotes } from '../src/core/rules.ts'
import type { Config, Note, Rule } from '../src/core/types.ts'

const empty: Config = { mode: 'enforce', skills: {}, needs: { ui: 'Building a screen.' }, trustProjects: [], rules: [], notes: [], learn: { skills: true } }
const cfg = (patch: Partial<Config>): Config => ({ ...empty, ...patch })

let t = 0
const at = () => ++t
const tool = (name: string, extra: Partial<Extract<CoreEvent, { type: 'tool' }>> = {}): CoreEvent => ({ type: 'tool', now: at(), tool: name, ...extra })
const prompt = (matched: string[] = [], root = '/work/a'): CoreEvent => ({ type: 'prompt', now: at(), text: 'do it', fromUser: true, matched, root })
const loadSkill = (skill: string): CoreEvent => ({ type: 'skill', now: at(), skill })
const compact = (): CoreEvent => ({ type: 'compact', now: at(), phase: 'after', trigger: 'manual' })

function run(config: Config, events: CoreEvent[], start?: Session): { s: Session; out: Action[][] } {
  let s = start ?? initSession(config, 'session-1', 0, 'clear')
  const out: Action[][] = []
  for (const e of events) {
    const r = decide(config, s, e)
    s = r.session
    out.push(r.actions)
  }
  return { s, out }
}
const last = (config: Config, events: CoreEvent[]) => run(config, events).out.at(-1)!
const denial = (a: Action[]) => a.filter((x) => x.kind === 'deny').map((x) => (x as { reason: string }).reason).join('\n')
const ctx = (a: Action[]) => a.filter((x) => x.kind === 'context').map((x) => (x as { text: string }).text).join('\n')

const fieldRule: Rule = { id: 'agent-names-model', before: { tools: ['Agent'] }, field: 'model', source: 'slip' }
const skillRule: Rule = { id: 'agent-needs-workflow', before: { tools: ['Agent'] }, skill: 'dev-workflow', source: 'skill:dev-workflow' }
const afterRule: Rule = { id: 'test-after-edit', after: { tools: ['Edit'], paths: ['src/**'] }, evidence: { tool: 'Bash', command: 'npm test' }, source: 'user' }

test('field rule denies Agent without model once', () => {
  const c = cfg({ rules: [fieldRule] })
  const { out } = run(c, [tool('Agent', { present: ['prompt'] }), tool('Agent', { present: ['prompt'] }), tool('Agent', { present: ['prompt', 'model'] })])
  assert.match(denial(out[0]!), /agent-names-model/)
  assert.match(denial(out[0]!), /before Agent: field model/)
  assert.equal(denial(out[1]!), '', 'the retry passes')
  assert.equal(denial(out[2]!), '')
})

test('field rule is satisfied by a call that carries the field', () => {
  assert.equal(denial(last(cfg({ rules: [fieldRule] }), [tool('Agent', { present: ['model'] })])), '')
})

test('skill rule denies until loaded, then skill is needed after compaction', () => {
  const c = cfg({ rules: [skillRule] })
  const { out, s } = run(c, [tool('Agent'), loadSkill('dev-workflow'), tool('Agent'), compact(), prompt()])
  assert.match(denial(out[0]!), /dev-workflow/)
  assert.equal(denial(out[2]!), '')
  assert.equal(s.ledger['dev-workflow']?.state, 'restoring')
  assert.match(ctx(out[4]!), /invoke these skills[^\n]*dev-workflow/)
})

test('a rule that fired makes its skill needed even without a load', () => {
  const c = cfg({ rules: [skillRule] })
  const { out } = run(c, [tool('Agent'), prompt()])
  assert.match(ctx(out[1]!), /dev-workflow/)
})

test('a skill only named in a rule gets a ledger entry', () => {
  assert.equal(initSession(cfg({ rules: [skillRule] }), 's', 0, 'clear').ledger['dev-workflow']?.state, 'absent')
})

test('after rule denies next matching call once', () => {
  const c = cfg({ rules: [afterRule] })
  const edit = () => tool('Edit', { path: '/work/a/src/x.ts', root: '/work/a' })
  const { out, s } = run(c, [edit(), edit(), edit(), tool('Bash', { command: 'npm test' }), edit()])
  assert.equal(denial(out[0]!), '', 'the first edit opens the rule')
  assert.match(denial(out[1]!), /test-after-edit/)
  assert.equal(denial(out[2]!), '', 'the retry passes')
  assert.equal(s.openRules.length, 1, 'evidence closed it, the last edit opened it again')
  assert.equal(denial(out[4]!), '')
  assert.match(ctx(run(c, [edit(), prompt()]).out[1]!), /Open rule: test-after-edit/)
})

test('evidence closes an after rule', () => {
  const c = cfg({ rules: [afterRule] })
  const { s } = run(c, [tool('Edit', { path: '/work/a/src/x.ts', root: '/work/a' }), tool('Bash', { command: 'npm test' })])
  assert.deepEqual(s.openRules, [])
})

test('one denial lists every broken rule and the brief check', () => {
  const c = cfg({ rules: [fieldRule, skillRule], skills: { 'ui-guide': { need: 'ui', from: 'user' } } })
  const { out } = run(c, [prompt(['ui']), tool('Agent', { present: ['prompt'], brief: 'do the thing' })])
  const reason = denial(out[1]!)
  assert.match(reason, /agent-names-model/)
  assert.match(reason, /agent-needs-workflow/)
  assert.match(reason, /skills: <names>/)
  assert.equal(out[1]!.filter((a) => a.kind === 'deny').length, 1)
})

test('observe mode records rule breaks only', () => {
  const c = cfg({ mode: 'observe', rules: [fieldRule] })
  const { out, s } = run(c, [tool('Agent', { present: [] })])
  assert.equal(denial(out[0]!), '')
  assert.match(s.observed[0]!.reason, /agent-names-model/)
})

test('pause stops every rule', () => {
  const c = cfg({ rules: [fieldRule, skillRule] })
  const { out } = run(c, [{ type: 'command', now: at(), args: 'pause' }, tool('Agent', { present: [] })])
  assert.equal(denial(out[1]!), '')
})

test('a rule with where applies in that project only', () => {
  const c = cfg({ rules: [{ ...fieldRule, where: '/work/a' }] })
  assert.match(denial(last(c, [tool('Agent', { present: [], root: '/work/a' })])), /agent-names-model/)
  assert.equal(denial(last(c, [tool('Agent', { present: [], root: '/work/b' })])), '')
})

test('a subagent call is never checked by a rule', () => {
  const c = cfg({ rules: [fieldRule] })
  assert.equal(denial(last(c, [tool('Agent', { present: [], agentId: 'a1' })])), '')
})

test('user file rules and notes parse; project file rules are an error', () => {
  const user = JSON.stringify({
    needs: { ui: 'Building a screen.' },
    rules: [fieldRule, skillRule, afterRule],
    notes: [{ id: 'reply-language', text: 'Reply in German.', source: 'user' }, { id: 'ui-copy', text: 'Show copy first.', need: 'ui', source: 'user' }],
    learn: { skills: false },
  })
  const ok = parseConfig(user, undefined)
  assert.deepEqual(ok.errors, [])
  assert.equal(ok.config.rules.length, 3)
  assert.equal(ok.config.notes.length, 2)
  assert.equal(ok.config.learn.skills, false)
  const project = parseConfig(undefined, JSON.stringify({ rules: [fieldRule], notes: [{ id: 'n', text: 'x', source: 'user' }], learn: { skills: false } }))
  assert.equal(project.config.rules.length, 0)
  assert.equal(project.config.notes.length, 0)
  assert.equal(project.config.learn.skills, true)
  assert.equal(project.errors.filter((e) => /only allowed in the user config/.test(e)).length, 3)
})

test('invalid rule and note entries are dropped one by one', () => {
  const r = parseConfig(JSON.stringify({
    rules: [fieldRule, { id: 'two-kinds', before: { tools: ['A'] }, skill: 's', field: 'f', source: 'user' }, { id: 'no-evidence', after: { tools: ['A'] }, source: 'user' }, fieldRule],
    notes: [{ id: 'n1', text: 'a\nb', source: 'user' }, { id: 'n2', text: 'ok', need: 'missing', source: 'user' }, { id: 'n3', text: 'fine', source: 'user' }],
  }), undefined)
  assert.deepEqual(r.config.rules.map((x) => x.id), ['agent-names-model'])
  assert.deepEqual(r.config.notes.map((x) => x.id), ['n3'])
  assert.equal(r.errors.length, 5)
})

test('note without need goes to section, capped at 2000 chars', () => {
  const note = (id: string, text: string, extra: Partial<Note> = {}): Note => ({ id, text, source: 'user', ...extra })
  const long = 'x'.repeat(500)
  const c = cfg({ notes: [note('a', 'Reply in German.'), note('b', 'Only here.', { where: '/work/b' }), note('c', 'Needs ui.', { need: 'ui' }), note('d', long), note('e', long), note('f', long), note('g', long), note('h', long)] })
  const r = sectionNotes(c, '/work/a')
  assert.match(r.text, /Reply in German\./)
  assert.doesNotMatch(r.text, /Only here/)
  assert.doesNotMatch(r.text, /Needs ui/)
  assert.ok(r.text.length <= NOTE_CAP + 200)
  assert.deepEqual(r.leftOut.map((n) => n.id), ['g', 'h'])
  assert.equal(sectionNotes(cfg({}), '/work/a').text, '')
})

test('need note sent on first match and after compaction', () => {
  const c = cfg({ notes: [{ id: 'ui-copy', text: 'Show copy first.', need: 'ui', source: 'user' }] })
  const { out } = run(c, [prompt(), prompt(['ui']), prompt(), compact(), prompt()])
  assert.equal(ctx(out[0]!), '')
  assert.match(ctx(out[1]!), /Show copy first\./)
  assert.equal(ctx(out[2]!), '', 'once while the need stays')
  assert.match(ctx(out[4]!), /Show copy first\./, 'again after a compaction')
})

test('confirmed note sent once in next context', () => {
  const c = cfg({ notes: [{ id: 'reply-language', text: 'Reply in German.', source: 'user' }] })
  const start = { ...initSession(c, 's', 0, 'clear'), freshNotes: ['reply-language'] }
  const { out } = run(c, [prompt(), prompt()], start)
  assert.match(ctx(out[0]!), /Reply in German\./)
  assert.equal(ctx(out[1]!), '')
})

// --- Fix round ---

const parseRules = (rules: unknown[], extra: Record<string, unknown> = {}) => parseConfig(JSON.stringify({ rules, ...extra }), undefined)

test('a skill rule does not deny the Skill call that loads its own skill', () => {
  const c = cfg({ rules: [{ id: 'skill-first', before: { tools: ['Agent'] }, skill: 'dev-workflow', source: 'user' }] })
  const { out } = run(c, [tool('Skill', { skill: 'dev-workflow' })])
  assert.equal(denial(out[0]!), '')
  const r = parseRules([{ id: 'loop', before: { tools: ['Skill'] }, skill: 'dev-workflow', source: 'user' }])
  assert.equal(r.config.rules.length, 0)
  assert.match(r.errors.join('\n'), /Skill/)
  assert.equal(parseRules([{ id: 'fine', before: { tools: ['Skill'] }, field: 'skill', source: 'user' }]).config.rules.length, 1)
})

test('a retry denied by another rule does not use up the field retry', () => {
  const c = cfg({ rules: [fieldRule, skillRule] })
  const { out } = run(c, [tool('Agent', { present: [] }), tool('Agent', { present: [] }), loadSkill('dev-workflow'), tool('Agent', { present: [] })])
  assert.match(denial(out[0]!), /agent-names-model/)
  assert.match(denial(out[1]!), /agent-needs-workflow/)
  assert.doesNotMatch(denial(out[1]!), /agent-names-model/, 'the field rule already denied once')
  assert.equal(denial(out[3]!), '', 'the field retry is still unused, so this call passes')
})

test('evidence that is itself denied does not close an after rule', () => {
  const gate: Rule = { id: 'bash-needs-guide', before: { tools: ['Bash'] }, skill: 'bash-guide', source: 'user' }
  const c = cfg({ rules: [afterRule, gate] })
  const edit = () => tool('Edit', { path: '/work/a/src/x.ts', root: '/work/a' })
  const { s, out } = run(c, [edit(), tool('Bash', { command: 'npm test' })])
  assert.match(denial(out[1]!), /bash-needs-guide/)
  assert.equal(s.openRules.length, 1, 'still open')
  const again = run(c, [edit(), loadSkill('bash-guide'), tool('Bash', { command: 'npm test' })])
  assert.deepEqual(again.s.openRules, [])
})

test('observe mode records every field-rule violation and keeps no retry state', () => {
  const c = cfg({ mode: 'observe', rules: [fieldRule] })
  const { s } = run(c, [tool('Agent', { present: [] }), tool('Agent', { present: [] })])
  assert.equal(s.observed.length, 2)
  assert.deepEqual(s.fieldDenied, [])
})

test('where is compared without trailing slashes', () => {
  const r = parseRules([{ ...fieldRule, where: '/work/a/' }])
  assert.equal(r.config.rules[0]!.where, '/work/a')
  const c = cfg({ rules: [{ ...fieldRule, where: '/work/a' }] })
  assert.match(denial(last(c, [tool('Agent', { present: [], root: '/work/a/' })])), /agent-names-model/)
})

test('globs match against the working tree root and where against the main root', () => {
  const rule: Rule = { ...afterRule, where: '/work/main' }
  const c = cfg({ rules: [rule] })
  const edit = () => tool('Edit', { path: '/work/main/.claude/worktrees/w/src/x.ts', root: '/work/main', tree: '/work/main/.claude/worktrees/w' })
  const { s } = run(c, [edit()])
  assert.equal(s.openRules.length, 1, 'src/** is relative to the worktree, and where names the main root')
  const other = run(c, [tool('Edit', { path: '/work/main/.claude/worktrees/w/src/x.ts', root: '/work/main' })])
  assert.equal(other.s.openRules.length, 0, 'against the main root the path is not under src/')
})

test('rule strings are one line with limits', () => {
  const bad = (r: Partial<Rule> & Record<string, unknown>) => parseRules([{ id: 'x', source: 'user', ...r }]).config.rules.length
  const ok = { before: { tools: ['Agent'] }, field: 'model' }
  assert.equal(bad(ok), 1)
  assert.equal(bad({ before: { tools: ['A'.repeat(101)] }, field: 'model' }), 0)
  assert.equal(bad({ before: { tools: Array.from({ length: 21 }, (_, i) => `T${i}`) }, field: 'model' }), 0)
  assert.equal(bad({ before: { tools: ['Edit'], paths: ['a'.repeat(201)] }, field: 'model' }), 0)
  assert.equal(bad({ before: { tools: ['Edit'], paths: ['a\nb'] }, field: 'model' }), 0)
  assert.equal(bad({ after: { tools: ['Edit'] }, evidence: { tool: 'Bash', command: 'x'.repeat(201) } }), 0)
  assert.equal(bad({ after: { tools: ['Edit'] }, evidence: { tool: 'B'.repeat(101) } }), 0)
})

test('control and bidi characters are refused in notes and rules', () => {
  for (const ch of ['\u0007', '\u0085', '‮', '⁦', '‏', '\u007f']) {
    const n = parseConfig(JSON.stringify({ notes: [{ id: 'n', text: `Reply${ch}in German`, source: 'user' }] }), undefined)
    assert.equal(n.config.notes.length, 0, `note with U+${ch.charCodeAt(0).toString(16)}`)
    const r = parseRules([{ id: 'r', before: { tools: ['Edit'], paths: [`src${ch}/**`] }, field: 'model', source: 'user' }])
    assert.equal(r.config.rules.length, 0, `rule with U+${ch.charCodeAt(0).toString(16)}`)
  }
})

test('proposals are checked against the needs of the user file only', () => {
  const r = parseConfig(JSON.stringify({ needs: { ui: 'Screens.' } }), JSON.stringify({ needs: { extra: 'Project only.' } }))
  assert.deepEqual(r.config.userNeeds, ['ui'])
  assert.ok('extra' in r.config.needs)
})

test('an open after rule is told once per opening', () => {
  const c = cfg({ rules: [afterRule] })
  const edit = () => tool('Edit', { path: '/work/a/src/x.ts', root: '/work/a' })
  const { out } = run(c, [edit(), prompt(), prompt(), tool('Bash', { command: 'npm test' }), edit(), prompt()])
  assert.match(ctx(out[1]!), /Open rule: test-after-edit/)
  assert.equal(ctx(out[2]!), '')
  assert.match(ctx(out[5]!), /Open rule: test-after-edit/, 'a new opening is told again')
})

test('the need-note block is capped and the rest is listed in the status', async () => {
  const { renderTable } = await import('../src/core/status.ts')
  const long = 'y'.repeat(450)
  const notes: Note[] = ['a', 'b', 'c', 'd', 'e', 'f'].map((id) => ({ id, text: long, need: 'ui', source: 'user' }))
  const c = cfg({ notes })
  const { out, s } = run(c, [prompt(['ui'])])
  const sent = ctx(out[0]!)
  assert.ok(sent.length < 2400)
  assert.deepEqual(s.notesSent, ['a', 'b', 'c', 'd'])
  assert.match(renderTable(c, s, 0, '/work/a'), /Notes waiting for a later prompt[^\n]*: e, f/)
  const next = run(c, [prompt()], s)
  assert.match(ctx(next.out[0]!), /y{50}/, 'the rest follows on the next prompt')
})
