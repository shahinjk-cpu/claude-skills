# Frontmatter

Verified against the Claude Code skills documentation. Fields do not always do what their names suggest — check here rather than assuming (principle #9).

## The trap

**`allowed-tools` does not restrict.** It pre-approves tools so they do not prompt, for the single turn that invokes the skill. The grant clears on the next message. Every unlisted tool remains callable under normal permission settings.

**`disallowed-tools` restricts.** This is the field to use when a skill must be prevented from doing something.

Writing `allowed-tools: Read, Grep` and expecting the skill to be read-only is wrong. It will happily call `Write`.

## Fields

| Field | Effect |
|---|---|
| `name` | Display name. Defaults to the directory name. |
| `description` | When and why to use it. Drives auto-activation — write it as trigger conditions, not a summary. |
| `when_to_use` | Additional trigger context. |
| `argument-hint` | Autocomplete hint. |
| `arguments` | Named positional args for `$name` substitution. |
| `allowed-tools` | **Grants** — pre-approves without prompting, one turn. Does not restrict. |
| `disallowed-tools` | **Restricts** — blocks the tool while the skill is active. |
| `disable-model-invocation` | `true` hides it from auto-invocation. Use when two skills would compete for the same triggers. |
| `user-invocable` | `false` hides it from the `/` menu. |
| `model` / `effort` | Override session model or reasoning effort. |
| `context` | `fork` runs the skill in a subagent. |
| `agent` | Subagent type when `context: fork`. |
| `hooks` | Lifecycle hooks scoped to this skill. |
| `paths` | Glob patterns limiting auto-activation. **Removes the skill from the model's skill list** when nothing matches — see below. |
| `shell` | `bash` (default) or `powershell`. |

## Two ways to vanish from the skill list

Observed, not inferred. Both are easy to mistake for a broken skill.

**`disable-model-invocation: true`** removes the skill from the list the model sees. It stays user-invocable by name. This is the correct field for a skill that should never auto-trigger — for example a v2 rewrite that would otherwise compete with the skill it replaces.

**`paths`** also removes it from that list when nothing in scope matches the globs. A skill scoped to `.claude/skills/**` did not appear while working in a project that has that directory. Whether the field gates listing or gates activation-and-therefore-listing was not isolated — only the effect is confirmed.

Consequence: **use `paths` only for a skill that is genuinely useless outside its file scope.** For a skill that should be reachable from anywhere but rarely, constrain it with a precise `description` instead — trigger phrases the user would actually type, not internal vocabulary.

## Scoping syntax

`allowed-tools` and `disallowed-tools` accept a space- or comma-separated string, or a YAML list.

Bash scoping works: `Bash(git add *)`, `Bash(npm test *)`. Path substitution works: `Bash(${CLAUDE_PROJECT_DIR}/scripts/lint.sh *)`.

MCP tools match on **server name** — `mcp__server-name` grants the whole server. Per-tool wildcards (`mcp__server__*`) are not supported; enumerate individual tools instead when a blanket server grant would include destructive operations.

## Supporting files

**Never auto-loaded.** A file in the skill directory is inert until `SKILL.md` tells the model to read it. Link every reference and state when to load it.

Keep `SKILL.md` under ~500 lines by the documentation's guidance, under ~120 by this standard.
