# Background

How Souffleur started, what the research found, and why it is built the way it is. Dates are when each step happened.

## 2026-11-24: the problem

During a two-day Claude Code session that designed a UI prototype, several skills stopped working after the context was compacted, although they had been loaded earlier:

- A token-saving skill came back as a one-line reminder instead of its full rules, and answers got long again.
- The writing skills (humanizer, stop-slop) were no longer applied to the prototype's text.
- The UI design skill's detector stopped running from the seventh prototype version on.

Four small shell hooks were supposed to prevent this. Each reacted to keywords or file names, and each checked "already loaded?" by searching the whole transcript. The transcript still contains the load from before the compaction, so the hooks stayed silent while the skill text was already gone from the context. The user had to ask again and again whether a skill was still active.

## 2026-11-25: research

### Other users report the same

About 30 issues in [anthropics/claude-code](https://github.com/anthropics/claude-code/issues) from July 2025 to November 2026 describe rules or skills lost after compaction or resume. They fall into three groups:

1. CLAUDE.md rules followed less after compaction. Claude Code now re-reads the project CLAUDE.md from disk after compaction, so the text is back, but reports of ignored rules continue.
2. The list of available skills dropped after compaction ([#74990](https://github.com/anthropics/claude-code/issues/74990)). Fixed in Claude Code 2.1.304.
3. The text of skills already used in the session. Still open: bodies come back cut to 5,000 tokens per skill and 25,000 in total ([#82144](https://github.com/anthropics/claude-code/issues/82144)), and a skill used before a resume is not re-attached at all ([#94564](https://github.com/anthropics/claude-code/issues/94564)).

Workarounds people report: a `SessionStart` hook with matcher `compact`, the `reloadSkills` hook output, and telling Claude to call the Skill tool again. Plain reminder text injected by hooks works for some and not for others. `PostCompact` hook output did not reach the model after automatic compaction.

### Existing tools

No tool found tracks which skills a session needs, which are loaded, and which a compaction dropped. The closest:

- [diet103/claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase): keyword and path rules in `skill-rules.json`, a hook that blocks edits until a required skill is loaded.
- [obra/superpowers](https://github.com/obra/superpowers): re-injects one bootstrap skill on startup, clear and compact.
- Forced-evaluation hooks that make the model answer yes or no for each skill before it starts. One author measured 80 to 100 percent activation with them against about 20 percent with plain suggestions, on older Haiku and Sonnet models.
- Several young routers that match skills by local embeddings.

### Tests on Claude Code 2.1.322

A test skill of 43 KB with marker lines at its start and end:

| Scenario | Result |
|---|---|
| Skill loaded, then `/compact` in the same process | Re-attached, cut at exactly 20,000 characters with a truncation note. The model could no longer see the end marker. |
| Skill loaded, session resumed, then `/compact` | Not re-attached at all. |
| Skill invoked again after compaction | Full 43 KB text, end marker visible. |
| `SessionStart` hook with source `compact` | Runs before the compaction boundary is written to the transcript, so it cannot read what was lost. |
| Typed `/name` command | Fires `UserPromptExpansion`, not `UserPromptSubmit`. |

A second test used Claude Code's mod API (in-process plugins, early access):

| Question | Result |
|---|---|
| Does `skill.prompt` see every skill load? | Yes, including skills the model invoked on its own. |
| Does `session.compact` fire around a compaction? | Yes, before and after. |
| Does a system prompt section added by a mod survive `/compact`? | Yes. The model quoted it after compaction. |
| How fast is `$.model.classify` with the default small model? | About 800 ms per prompt. It labelled "build me a login screen mockup" as `user-interface`. |

### Tests on Claude Code 2.1.332

Before the implementation we repeated the tests on 2.1.332 with a mod that records every event Souffleur will use. Runs were headless (`claude -p` with stream-json input, one process per scenario). Scrubbed recordings are in [test/fixtures](../test/fixtures).

| Question | Result |
|---|---|
| Do the 2.1.322 results still hold? | Yes. After `/compact` in the same process the 43 KB skill came back cut, with the note `[... skill content truncated for compaction ...]`. After a resume and `/compact` the model saw only the one-line skill listing. |
| Does `skill.prompt` fire for the re-attachment after compaction? | No `skill.prompt` fired between the compaction hooks and the model's answer to the next prompt. The model answered without tools, so the recording ends there. |
| Does the model load the skills a prompt's `context` block names, before other work? | Yes, in 10 of 10 fresh sessions (5 on Haiku, 5 on Opus). Each called the Skill tool for both named skills before answering. |
| What key does `skill.prompt` use for a plugin skill? | The full name, `<plugin>:<skill>`. |
| What does a typed `/name` fire? | `command.run`, then `prompt.submit` with `command` set, then `skill.prompt`. |
| Which compaction triggers change the context? | `/compact` reports `manual`. The API documents `precompute` as a dispatch that installs nothing, so it must not count as a compaction. |
| Does the session id survive a resume? | Yes. `session.start` fires again with the same id. |
| Does `$.state` survive a resume? | No. A resumed process starts with empty `$.state`. `$.store` is shared across sessions, so the ledger has to be stored under the session id. |
| What does `/clear` do? | It fires `command.run` with `clear`. The next prompt carries a new session id, and no `session.start` fires for it. |
| Can a subagent's skill load be told apart from the main session's? | `skill.prompt` carries no agent id. The `tool.call` for the Skill tool just before it does carry `agentId`, so the two can be paired. |
| Which prompts did the user not type? | A subagent's hand-back arrives as `prompt.submit` with `isMeta: true` and origin `peer`. |
| Where do tool arguments sit in `tool.call`? | Flat on the event: `file_path`, `command`, `prompt`, `skill`. |
| Can a mod's module live outside `hooks/`? | Yes. `hooks/hooks.json` can name `../src/mod/register.ts`, and that module can import `../core/*.ts`. `claude plugin validate` warns about the `.ts` import suffix (TS5097) but passes, and the mod loads. |
| Can a project load a local plugin folder through `env` in `.claude/settings.local.json`? | No. `CLAUDE_CODE_PLUGIN_DIRS` works only in the environment of the `claude` process, also when it starts in a git worktree. |

Not measured: how the status line looks in the desktop and mobile apps, and whether `$.state` survives a hot reload of the mod (the API documents that it does).

### Tests for rules and notes, Claude Code 2.1.332

A second recorder mod checked what the rules-and-notes design relies on, again in headless runs with a 43 KB test skill.

| Question | Result |
|---|---|
| Does a tool registered with `$.tool.register` reach the main model? | Yes. It appears as `mcp__<plugin>__<name>`, is served by a `tool.run` hook, and the model called it when the user wrote "Remember as a rule: always answer in German." after a system prompt section asked it to. |
| How fast is one small-model call over a skill text? | `$.model.complete` with `haiku` over the 43 KB skill took about 2 seconds and returned the requested JSON (an empty list, since the test skill holds no rules). |
| Does an automatic compaction fire `session.compact`? | Yes, with trigger `auto`, when the context passed the threshold during a run. |
| Does a `context` entry on a tool result reach the model? | It reaches the model, but the model may treat it as untrusted. In one run it followed a test note on a tool result; in another it said it ignored "a plugin note in the output". A restore request sent this way is a hint, not a guarantee. |
| Does invoking a loaded skill again add its text again? | No. While the skill is still in the context, a second invocation reports it as already loaded. |

Not measured yet: the `$.ui.ask` dialog in a Remote Control session in the desktop and mobile apps.

## Decision

Souffleur is built as a Claude Code mod. Hooks only see the transcript after the fact; a mod sees skill loads and compactions as they happen, can keep a short ledger in the system prompt where compaction does not touch it, can classify a prompt with the built-in small model, and can show its state in the client. The mod API is early access and changes between releases, so the rules and the ledger live in plain code with no dependency on it, and only a thin layer talks to the API.
