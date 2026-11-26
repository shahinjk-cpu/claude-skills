# Fixtures

Each file is a recording of a real headless Claude Code session, reduced so it carries no personal data and no skill text. Every file starts with the `claudeCode` version it was recorded on, followed by the list of `events`. Each event has `event`, `at` (milliseconds since the first event), `session` and `input`. The shapes are typed in [fixtures.ts](../fixtures.ts).

How the recordings are reduced:

- A `skill.prompt` event keeps `skill`, `len`, `head` and `tail` instead of the skill text. `len` is the length in characters, `head` and `tail` are the first and last characters.
- Prompt texts are cut at 80 characters.
- Paths and agent ids are replaced with neutral ones (`/project/...`, `agent-1`).
- `session.compact.before` and `session.compact.after` are the two halves of one hook. They share a trigger.
- Tool arguments are flat beside `tool` on a `tool.call` event, so a Skill call has `skill` and a Read call has `file_path`.

What each file shows:

- `compact-in-process.json`: two skills loaded, then `/compact` in the same process.
- `resume-then-compact-then-clear.json`: a skill loaded, a resume, `/compact`, then `/clear`.
- `subagent.json`: a subagent loads a skill, then hands back to the main session.
- `typed-skill.json`: a typed `/bigtest` loads the skill, and the model then loads it a second time through the Skill tool.
