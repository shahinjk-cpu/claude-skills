# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

- Version notice: when Claude Code is newer than the newest version Souffleur was checked on, `/souffleur` shows one line with both versions. The status line stays unchanged.
- The plugin has a version, `0.1.0`, in `plugin.json` and `marketplace.json`, so `claude plugin update` can find later changes. CONTRIBUTING explains when to raise it.
- CI runs `claude plugin validate .` and `claude plugin test .` on the verified Claude Code version, and a weekly workflow runs them on the latest one and opens an issue when they fail.
- Learn rules from skills: when the main session loads a skill file Souffleur has not read, a small model reads it in the background (30 second limit) and queues at most three rules or notes the skill states as obligations, with source `skill:<name>`. It needs the user file, a person at the prompt and no pause. A version is read once and marked only after its proposals were queued; five reads per session at most, six skill proposals waiting at most, your own proposals first. The question says it was read from a skill's text and names the skill, plugin or project skill; project and MCP skills need the root in `trustProjects`. A subagent's loads are skipped, except that a background subagent's load can be read as the main session's. `"learn": { "skills": false }` in the user file turns it off.
- Rules and notes in the user file: a rule waits for a skill before a call, requires a field on a call, or requires evidence after a call; a note is a standing instruction for the system prompt section or, with a `need`, for the prompt context. Rules follow `mode`, `/souffleur pause` stops them, and a project file that holds them gets an error.
- The tool `souffleur_propose` lets the model propose a rule or note when something went wrong or you ask it to remember something. Proposals queue (20 at most), and one question per turn is asked at the end of a turn with `Yes, everywhere`, `Yes, this project only` and `No`.
- `/souffleur rule <text>`, `/souffleur review`, `/souffleur accept <id> [here|project]` and `/souffleur decline <id>`; they act only when the user types them. Without a dialog proposals stay queued and nothing is written. `/souffleur migrate` queues standing instructions from `CLAUDE.md` and the memory index as note proposals.
- Fix: a skill is marked `not installed here` only from the session's own skill listing, never from the command list, and not when the listing is incomplete. Names match with or without the plugin prefix. Such a skill opens no duty and does not appear in the always-on text, the brief check or the open duties.
- Fix: the injected answer gets a line in the summary every time it is the result, including when it stays unchanged and in the text without a dialog. A plugin with a `SessionStart` hook gets a note, one without gets a warning, and unreadable files say so.
- Fix: a session start, a reload and any event on a session that missed a config change bring the ledger in line with the config. The skill listing no longer holds up the prompt.
- Fix: `/souffleur migrate` reads the config fresh, counts only user file skills as watched, lists every skill a hook names, treats a bare word as a guess, and notes watched skills that are not installed in the session.
- Fix: `/souffleur init` now applies its answers to the running session: new skills show as absent, removed ones leave the table and the status line updates, with no new session needed.
- Fix: the answer `Injected by its plugin` is now `Loaded by its own plugin at start (rare)`, explained with an example and listed last. `init` warns when the plugin declares no `SessionStart` hook, because the status would report the skill as loaded when it is not.
- Fix: a configured skill that this session does not list shows as `not installed here` and is neither requested nor gated, so a user file can name a skill of one project without noise elsewhere.
- Fix: `/souffleur migrate` warns when a hook serves a skill Souffleur does not watch, or names no skill, and then lists `Keep` first.
- Fix: `init` proposes an existing need only when the skill's description clearly matches it, and recommends `Don't watch` for skills that run only on an explicit request.
- Install with `/plugin install skill-souffleur --marketplace r4KK4n/skill-souffleur`; the repository now holds a marketplace file.
- `/souffleur init`: asks per skill how it is kept (from the start, injected by its plugin, when the task needs it, or not watched) and writes each answer to `~/.claude/souffleur.json`. Without a dialog it prints the recommendations and changes nothing.
- `/souffleur migrate`: lists hooks in `settings.json` that do what Souffleur does, including guesses from script names such as `preload` and `reload`, and turns off the ones you pick after a backup. It never edits scripts, `CLAUDE.md` or memory files.
- Status line `souffleur: not set up, run /souffleur init` while no user config exists.
- Config file: user file `~/.claude/souffleur.json`, optional project file with restricted rights.
- Need detection: a prompt is matched against the configured needs, and the skills those needs name are asked for when missing.
- Gates and duties: a step can wait until its skills are loaded, and a duty can require evidence after a step. Nothing is denied in `observe` mode, the default.
- Restore after compaction and resume: the mod keeps a ledger per session, marks skills stale when `/compact` runs and asks the model to load them again on the next prompt.
- `/souffleur` command: shows the ledger, the active needs, open duties and calls that `observe` mode would have denied. Also `need`, `drop` and `pause`.
- Status line: `souffleur: 2 loaded, 1 stale`, or `souffleur: degraded, see /souffleur` when a config file or an event could not be read.
- System prompt section that tells the model to follow Souffleur's load requests and names the always-on skills.
