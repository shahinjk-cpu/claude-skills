# Compatibility

Souffleur depends on Claude Code's mod API, which is early access and changes between releases. This page lists the behaviour Souffleur relies on and the version each item was verified on. The evidence is in [background.md](background.md).

| Behaviour | Verified on |
|---|---|
| `skill.prompt` fires for the Skill tool and for a typed `/name`, with the plugin skill key `<plugin>:<skill>` | 2.1.332 |
| `skill.prompt` does not fire for the re-attachment after compaction | 2.1.332 |
| `session.compact` runs a hook before and after; `/compact` reports trigger `manual` | 2.1.332 |
| A `context` entry added in `prompt.submit` makes the model invoke the named skills first (no fixture) | 2.1.332 |
| `prompt.compose` sections survive `/compact` | 2.1.322 |
| `$.session.id()` is stable across resume; `/clear` starts a new id without `session.start` | 2.1.332 |
| `$.state` is empty after a resume; `$.store` keeps values across sessions (no fixture) | 2.1.332 |
| `tool.call` carries tool arguments flat on the event and `agentId` for subagent calls | 2.1.332 |
| A hooks module outside `hooks/` can import sibling `.ts` files (no fixture) | 2.1.332 |
| After `/compact` in the same process, the engine re-attaches the skill with the note "Do NOT re-execute these skills". A plain request to load them again is ignored; a request that names that note and says it does not apply is followed | 2.1.332 |
| A `prompt.submit` `context` entry reaches the model as a hook note on the user's turn, also on the first prompt after `/compact` | 2.1.332 |
| `$.ui.status(text)` shows in headless stream-json output as a `ui_status` system message | 2.1.332 |
| `$.command.register` makes `/souffleur` reach a `command.run` hook with `command: "souffleur"` | 2.1.332 |
| `$.fs.exists` and `$.fs.read` read `~/.claude/souffleur.json` and `<project>/.claude/souffleur.json`; `$.env.get("HOME")` gives the home folder | 2.1.332 |
| `claude plugin test` cannot set `origin`, `command` or `isMeta` on a `prompt.submit` call, and a `session.compact` call carries no `messages`, so the adapter tests treat a prompt without `origin` as typed | 2.1.332 |
| `$.tool.register` adds `mcp__<plugin>__<name>`, served by a `tool.run` hook, and the main model calls it (no fixture) | 2.1.332 |
| `$.model.complete` with `haiku` reads a 43 KB text in about 2 s (no fixture) | 2.1.332 |
| Automatic compaction fires `session.compact` with trigger `auto` (no fixture) | 2.1.332 |
| A `context` entry on a tool result reaches the model, which may still disregard it as untrusted (no fixture) | 2.1.332 |
| `/souffleur init` lists the installed skills from `$.session.usage({ breakdown: "summary" })` (`context.breakdown.skills.skillFrontmatter`), with `$.command.list()` names as the fallback, and takes one-line descriptions from `$.command.list()` for the small-model call. Taken from the typings, not yet run in a live session | 2.1.332 (typings) |
| `/souffleur init` and `/souffleur migrate` ask with `$.ui.ask(question, { options, header })`, which the typings say rejects when nobody can answer. A rejection on the first question counts as "no dialog". Not yet run in a live session | 2.1.332 (typings) |
| `/souffleur init` writes `~/.claude/souffleur.json` and `/souffleur migrate` writes `~/.claude/settings.json`, both with `$.fs.write`; `init` reads a small-model answer from `$.model.complete`. That the running session picks up a changed settings hook is documented, not yet measured | 2.1.332 (typings) |
| `$.session.usage({ breakdown: "summary" }).context.breakdown.skills` is already filled at `session.start` and on `prompt.submit`. It holds `totalSkills`, `includedSkills`, `tokens` and `skillFrontmatter`, one `{ name, source, tokens }` per skill; `source` is `userSettings`, `plugin` or `built-in`. Plugin skills are named `plugin:skill`, the others bare (probe in a headless run, 90 of 90 skills listed) | 2.1.332 (observed) |
| `/souffleur init` reads `~/.claude/plugins/installed_plugins.json` (`plugins` maps `name@marketplace` to a list of copies with `installPath`) and each copy's `hooks/hooks.json` and `.claude-plugin/plugin.json` with `$.fs.read` to look for `SessionStart` hooks, because the mod API lists no plugin hooks at run time. The file layout is observed, not documented | 2.1.332 (observed) |
| `$.tool.register` adds `mcp__skill-souffleur__souffleur_propose`. In a headless run (`claude -p`) the model found it through ToolSearch, called it on "Remember as a rule: answer in German" and got the queued text back; a second run resumed that session and `/souffleur review` listed the proposal, with `~/.claude/souffleur.json` unchanged | 2.1.332 (observed) |
| `turn.complete` carries `agentId` for subagent turns and `reason`; Souffleur asks about a proposal only for a main-loop turn with `reason` `answer` and a session started with `isInteractive`. The dialog at turn end is not yet run in a live interactive session | 2.1.332 (typings) |
| `$.session.repo()` gives the main working tree's root for a worktree, which `where` uses (typings, not yet run in a worktree session) | 2.1.332 (typings) |
| `command.run` carries `origin` (`composer`, `bridge`, `sdk` for the user, `{ kind: "plugin", name }` for a plugin's `$.command.run`). A typed `/probecmd` under `claude -p` reported `origin.kind` `sdk`. The model has no tool for a mod command: asked to run one it used the Skill tool and got "is a built-in CLI command, not a skill". `/souffleur rule`, `review`, `accept` and `decline` act only for the user origins | 2.1.332 (observed) |
| In a git worktree `$.vcs.detect({ path: cwd })` answers `root` (the worktree) and `mainRoot` (the main working tree), while `$.session.repo().root` is the main working tree. Rule globs are relative to the first, `where` names the second | 2.1.332 (observed) |
| Learning from skills calls `$.model.complete` with `system`, `prompt`, `maxTokens` and `timeoutMs` (30,000 ms) after the `skill.prompt` hook has answered, without awaiting it. `skill.prompt` carries the skill's `text`, `source`, `pluginName` and `path`; a typed `/name` load has no `Skill` tool call before it and counts as a main-session load. `skill.prompt` has no `agentId`, so a background subagent's load that arrives while the main session expects none can be read as a main load | 2.1.332 (typings, smoke run) |
