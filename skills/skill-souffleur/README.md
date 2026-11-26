# skill-souffleur

Keeps Claude Code skills loaded and in use for the whole session, including after the context is compacted or the session is resumed.

In a theatre, the souffleur sits out of sight at the edge of the stage and gives an actor the line they forgot, at the moment they need it. Souffleur does the same for skills: when compaction drops a skill the current task needs, it brings the skill back.

> **Status:** work in progress, no release yet. See the [roadmap](#roadmap).
>
> **Early access.** Souffleur is a Claude Code mod: TypeScript that runs inside Claude Code through its mod API, shipped and installed as a plugin. Anthropic still changes that API between releases, so an update of Claude Code can break Souffleur until it is adapted. It is provided as is, with no guarantee of fixes or dates. [docs/compatibility.md](docs/compatibility.md) lists the versions each behaviour was checked on.

## The problem

Claude Code loads a skill's instructions into the context when the skill is invoked. Long sessions compact that context, and the skill text does not reliably come back. Tested on Claude Code 2.1.322 with a 43 KB skill:

- In a running session, compaction re-attaches the skill cut off at 20,000 characters. The model no longer sees the rest.
- When a session is resumed and then compacted, the skill is not re-attached at all.
- Claude Code re-attaches at most 5,000 tokens per skill and 25,000 tokens across all skills. Skills that do not fit the budget are dropped.
- Invoking the skill again restores the full text.

The skill list itself comes back after compaction since Claude Code 2.1.304. What gets lost is the content of skills you already used. The model then keeps working without rules it followed an hour earlier, and nothing tells you. Related upstream reports: [#94564](https://github.com/anthropics/claude-code/issues/94564), [#82144](https://github.com/anthropics/claude-code/issues/82144), [#74990](https://github.com/anthropics/claude-code/issues/74990).

## What Souffleur will do

- Keep a ledger of the skills a session has loaded, and notice when compaction or a resume drops or truncates one.
- Decide from what you are working on which skills the current task needs, and load the missing ones by invoking them again.
- Hold back a step, such as writing a file, until the skills that step needs are loaded.
- Show which skills are active in the session, since when, and why.

You choose the skills and the rules in a configuration file. Souffleur never pastes a full skill text into every prompt.

Souffleur is a Claude Code mod, an in-process plugin. For why, including test results on Claude Code 2.1.322, see [docs/background.md](docs/background.md).

## How it works in a session

You work as usual. Souffleur stays quiet while nothing is missing. You notice it in three places:

- When the task needs a skill that is not loaded, or a compaction has cut one, Souffleur adds a short note to your prompt asking the model to invoke that skill first. The model loads it before it answers.
- The status line shows a summary such as `observe · 3 loaded, 1 restoring`. If your app does not show it, `/souffleur` gives the same summary as a table.
- In `enforce` mode, a step that needs a missing skill is refused once with the reason, and the model loads the skill and tries again.

A good way to start: install it, run `/souffleur init`, keep `observe` for a few sessions, and look at `/souffleur` after a compaction. If the ledger matches what you saw, switch to `enforce`.

Instructions you give in the chat still win. If you tell the model not to invoke any skill, it follows you and only mentions Souffleur's request.

## Why your own reload hooks are no longer needed

Hooks that re-inject a skill at session start or remind the model on every prompt run blind: they do not know whether the skill text is still there, so they repeat it when nothing is missing and cannot tell when compaction cut it in the middle of a turn. Souffleur sees each skill load and each compaction as it happens and asks for a skill again only when it is missing or cut. Keeping both doubles every reminder and leaves your rules in two places, which is why `/souffleur init` offers to turn the old hooks off.

## Install

Souffleur needs Claude Code 2.1.332 or later. Type this at the prompt of a terminal session:

```
/plugin install skill-souffleur --marketplace r4KK4n/skill-souffleur
```

Claude Code asks whether to add the marketplace; answer `y`. It then asks for a scope: choose user to cover every project, or project for one repository. Souffleur starts with no configuration. Until you add one, the status line reads `not set up, run /souffleur init`, and nothing else changes in your session.

`/plugin` exists only in the terminal interface. In a Remote Control session from the desktop or mobile app it is not available ("Plugins aren't available in this environment"). Install from a shell on the machine that runs Claude Code instead:

```
claude plugin marketplace add r4KK4n/skill-souffleur
claude plugin install skill-souffleur@skill-souffleur --scope user
```

New sessions load it. A running session picks it up after `/reload-plugins` or a restart.

### Update

```
claude plugin marketplace update skill-souffleur
claude plugin update skill-souffleur@skill-souffleur
```

Restart Claude Code afterwards. Every change that users notice raises the plugin version, so the update finds it. If Claude Code is newer than the version Souffleur was checked on, `/souffleur` says so in one line.

## Quick start

Create `~/.claude/souffleur.json`, or let `/souffleur init` write it for you:

```json
{
  "mode": "observe",
  "skills": {
    "terse:terse-mode": { "always": true },
    "writing-guide": { "need": "prose" },
    "ui-checklist": { "need": "ui" }
  },
  "needs": {
    "prose": "Writing text people read: docs, specs, plans, issues.",
    "ui": "Designing or building something a user sees."
  }
}
```

A skill with `"always": true` is needed from the first turn. A skill with `"need"` is needed once a prompt matches that need's description. After a compaction or a resume, Souffleur asks the model to load the skills it needs again. A project can add its own `.claude/souffleur.json`, but it cannot change your entries or your mode. The full format, including gates and duties, is in [docs/design.md](docs/design.md#configuration).

## Commands

- `/souffleur` or `/souffleur status` shows the mode, one row per skill with its state, the active needs, open duties, and the calls that `observe` mode would have denied.
- `/souffleur need <name>` turns a need on for this session, even when no prompt matched it.
- `/souffleur drop <name>` turns a need off again.
- `/souffleur pause` switches every check off for this session.
- `/souffleur init` asks, skill by skill, how Souffleur should keep each one and writes your answers to `~/.claude/souffleur.json`. See [Setting up your skills](#setting-up-your-skills).
- `/souffleur migrate` goes through your old reload hooks and offers to turn them off. See [Coming from your own hooks](#coming-from-your-own-hooks).
- `/souffleur rule <text>` turns your words into a rule or a note and asks before it keeps anything. See [Rules and notes](#rules-and-notes).
- `/souffleur review` asks about every waiting proposal, one dialog each. Without a dialog it lists them.
- `/souffleur accept <id> [here|project]` keeps a waiting proposal in text mode, everywhere or for this project only. `/souffleur decline <id>` declines one. `rule`, `review`, `accept` and `decline` act only when you type them; a plugin or the model cannot run them.

## Modes

`observe` is the default. Souffleur keeps the ledger, asks the model to reload skills and reports through `/souffleur`, but it never denies a tool call. Calls it would have denied are listed under "Would have denied", so you can see what `enforce` would do before you turn it on.

`enforce` lets gates and duties deny a tool call until the skill it names is loaded. Only your user file `~/.claude/souffleur.json` can set it, with `"mode": "enforce"`. A project file that sets a mode gets an error and is ignored, so a cloned repository can neither switch gates on nor off.

## Rules and notes

Some instructions have a trace Souffleur can see, and others are standing wishes. Souffleur keeps both in the user file, next to the skills, and asks you before it keeps anything.

A rule has one of three shapes. `before` with `skill` means a matching call waits until that skill is loaded. `before` with `field` means a matching call must carry that argument, for example a `model` on every `Agent` call. `after` with `evidence` means a matching call opens the rule, and a later call that matches the evidence closes it. In `observe` a broken rule is listed under "Would have denied". In `enforce` a skill rule denies every matching call until the skill is loaded (the call that loads the skill is never denied), while a field rule and an after rule deny once and let the retry pass, so a wrong rule cannot trap a session. `/souffleur pause` switches rules off with everything else. A note is never checked. Notes without a `need` go into the system prompt section (2,000 characters at most), notes with a `need` go into the prompt context when that need first matches and again after each compaction.

```json
{
  "rules": [
    { "id": "agent-names-model", "before": { "tools": ["Agent"] }, "field": "model", "source": "slip" },
    { "id": "test-after-edit", "after": { "tools": ["Edit"], "paths": ["src/**"] }, "evidence": { "tool": "Bash", "command": "npm test" }, "source": "user" }
  ],
  "notes": [
    { "id": "reply-language", "text": "Reply to the user in German, briefly.", "source": "user" }
  ]
}
```

Only the user file may hold `rules` and `notes`. A project file that has them gets an error for those keys, because a cloned repository must not deny calls or write into your system prompt. `where` limits an entry to one project and names the main repository root, so a rule made in one worktree holds in the others.

Proposals come from the model and from you. When something goes wrong that a rule would have caught, or when you write "remember as a rule: ...", the model calls the tool `souffleur_propose`. `/souffleur rule <text>` does the same for your own words. A proposal waits in a queue of at most 20. At the end of a turn in a session with a person at the prompt, Souffleur asks about the first one, with `Yes, everywhere`, `Yes, this project only` and `No`. Text typed under "Other" goes to the model with your next prompt as a request to revise the proposal. A declined proposal is remembered and not proposed again. The queue belongs to the session. Under `claude -p`, nothing is asked: proposals stay queued for `/souffleur review` and `/souffleur accept <id>`. The model may make five proposals per session, and a subagent may make none. Rule strings are one line without control characters, with at most 20 list items. Souffleur writes an entry to `~/.claude/souffleur.json` only after your yes, reads the file fresh first, stops when it cannot read it, and keeps every other key.

`/souffleur migrate` also queues the standing instructions it finds in your `CLAUDE.md` files and memory index as note proposals, with or without a dialog. The question names the file and line, and offers `Yes, this project only` first for a passage from the project's own files. The report says how many passages were skipped and why. 

Souffleur also reads your skills. This needs your user file and a session with a person at the prompt, and it stops under `/souffleur pause`. When the main session loads a skill whose file Souffleur has not seen, a small model looks for obligations the skill states about itself, such as "always run `npm test` after editing files under `src/`", and queues up to three as proposals named `skill:<name>`. The question starts with "Read from a skill's text, not verified:" and names the skill, the plugin or the project skill it came from. A skill version is read once and at most five are read per session (`/clear` starts a new session with five more); at most six skill proposals wait at once, and your own proposals come first. Skills from a project or an MCP server are read only when the project is in `trustProjects`. Skills a subagent loads are skipped, but a background subagent that loads a skill while the main session loads nothing can be read as the main session, because the load event does not say who loaded it. Each read sends the skill file, up to 60,000 characters, to the small model with a limit of 30 seconds, so to switch this off set `"learn": { "skills": false }` in `~/.claude/souffleur.json`. Nothing is written without your yes.

## Setting up your skills

`/souffleur init` can run at any time: after install, when you add a skill, or when one behaves differently. It asks about the skills in your user file first, then the skills one of your hooks reloads, then up to ten more that a small model picks from the descriptions of all installed skills. A skill that only a project file configures is listed and not asked, because `init` writes the user file. You answer one dialog per skill:

- `From the start`: the skill is needed from the first turn, and Souffleur asks for it after every compaction.
- `Loaded by its own plugin at start (rare)`: a plugin puts the text in at session start itself, for example with a `SessionStart` hook, so Souffleur counts it as loaded and asks for it only after a compaction or a clear. Offered last, for plugin skills (`plugin:skill`) only. Pick it for a plugin that merely lists its skills and the status will say loaded when it is not; `init` warns when the plugin has no such hook.
- `When the task needs it`: the skill is needed once a prompt matches a short description. The dialog shows the proposed description, and text you type under "Other" replaces it.
- `Don't watch`: no entry. A skill with a hand-written gate or duty keeps its entry, and `init` says so.

Each answer is written as it comes, with every other key in the file left as it was, and the running session uses the new entries at once. A skill your config names but this session does not list shows as `not installed here` and is never requested. Closing a dialog stops `init` and keeps the answers you gave. The closing summary names the installed skills that are not watched and points to `/souffleur migrate` when your settings hold hooks that may do the same job.

## Coming from your own hooks

If you already keep skills alive with a `SessionStart` or `UserPromptSubmit` hook, or with a standing line in `CLAUDE.md`, running Souffleur next to them doubles every reminder. Souffleur changes none of your files on install. `/souffleur migrate` starts with a short explanation of what it does and then asks one question per hook:

1. It reads the hooks in `~/.claude/settings.json`, your user and project `CLAUDE.md`, and the memory index of the current project.
2. A hook is listed when its command or matcher names a configured skill. A hook that points at an installed skill only by its script file name, or that runs a script with `preload`, `reload` or `inject` in its name, is listed too, even when the skill is gone; the dialog marks these as guesses.
3. For each hook you answer `Turn off`, `Keep` or `Show me what to do`.

`Turn off` first copies `settings.json` to `settings.json.bak-souffleur-<date>-<time>` (it never overwrites an older copy), then removes only that one hook entry, and stops if the file changed in the meantime. `Show me what to do` changes nothing and adds the manual steps to the closing report. `migrate` never edits a hook script, `CLAUDE.md` or a memory file. It lists passages that name a configured skill and read like a loading or reminding instruction, with file and line, and you decide what to do with them.

Where no dialog can answer, for example under `claude -p`, both commands print what they would ask, the config entries as JSON and the steps, and change nothing.

## What Souffleur reads, stores and costs

- It reads `~/.claude/souffleur.json`, the project's `.claude/souffleur.json` and, only during `/souffleur init` and `/souffleur migrate`, your `settings.json`, `CLAUDE.md` files and the current project's memory index.
- `/souffleur init` writes `~/.claude/souffleur.json` after each of your answers, and so does a yes to a rule or note proposal. `/souffleur migrate` writes `settings.json` only after you answer `Turn off`, with a backup copy first.
- It keeps the ledger per session in Claude Code's plugin store on your machine. Nothing is sent anywhere except through Claude Code's own model calls.
- Detecting needs costs one small-model call per configured need on each prompt you type, about 0.8 seconds, with a 1.5 second limit after which the prompt goes on without a verdict. A restored skill adds its full text to the context again.

## Limits

- Subagents are not gated. When the session hands work to a subagent while a need is active, the brief has to name the skills the subagent should load, or say `skills: none`.
- Souffleur checks that a skill is loaded and that a duty left its trace. It does not judge how well the model followed a skill.
- A restore request after a compaction in the middle of a long turn rides on the next tool result. Models may treat such notes as untrusted and skip them; in `enforce` the gate still catches the next gated step.
- A skill that does not load after two requests is marked `unavailable` and is neither requested nor gated again in that session.

## Troubleshooting

- The status line says `degraded, see /souffleur`: Souffleur could not read its config or an event changed shape after a Claude Code update. `/souffleur` lists what failed.
- No status line at all: your app may not show mod status lines. Use `/souffleur`.
- Please report problems with your Claude Code version (`claude --version`) through the [issue tracker](https://github.com/r4KK4n/skill-souffleur/issues).

## Switching off

- `/souffleur pause` switches every check off for the current session.
- `/plugin uninstall skill-souffleur` removes the mod. Your `~/.claude/souffleur.json` stays where it is, and the backup of `settings.json` stays too.

## Roadmap

- [x] Research and tests on Claude Code 2.1.322 and 2.1.332 ([background](docs/background.md))
- [x] Design document ([docs/design.md](docs/design.md))
- [x] Implementation plan
- [x] Ledger of loaded, truncated and dropped skills
- [x] Restore missing skills after compaction and resume
- [x] Detect from the prompt which skills a task needs
- [x] Block a step until its skills are loaded
- [x] `/souffleur status` command and status line
- [x] Rules and notes: from slips and the user's own words, confirmed in a dialog
- [x] Learn rules from the text of the user's skills
- [x] `/souffleur init` per skill and `/souffleur migrate` for old hooks
- [ ] Install guide
- [ ] First release, installable with `/plugin install`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security problems go through [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). Provided as is, without warranty. Review the code before you install it.
