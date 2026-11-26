# skill-authoring

A Claude Code skill for writing, updating and auditing other Claude Code skills against a fixed structural and prose standard.

A skill instructs an operator; it does not convince them. It carries what to do, what not to do, and what to emit. Anything that argues a rule is right goes in a rationale file that never loads at runtime. Each stage is built from Work, Emit and Halt: an imperative action, a literal output template with named fields, and the exact text to emit on failure.

Review gates render as plain markdown, not code blocks: a heading that names the stage, each field as a bold label, the fields that need your decision first, and code formatting only for things you'd copy and run. Skills it writes follow the same format.

## Modes

| Mode | Invoke | What it does |
|---|---|---|
| Update | `/skill-authoring my-skill --update` | Changes an existing skill, scoped to what you asked for. The default when no flag is given. |
| New | `/skill-authoring my-skill --new` | Builds a skill from scratch. Stops for you to confirm its shape before writing anything. |
| Audit | `/skill-authoring my-skill --audit` | Reviews a skill against the standard and proposes numbered changes. Applies nothing until you confirm. |

It also activates on requests like "update the X skill", "write a skill for X", or "audit this skill".

Every mode stops for your approval before it edits a file.

## Install

```sh
git clone https://github.com/thelastdoreo/skill-authoring ~/.claude/skills/skill-authoring
```

Update with `git -C ~/.claude/skills/skill-authoring pull`.

## Files

| File | Holds |
|---|---|
| `SKILL.md` | The router: modes, principles, flags, operational rules |
| `references/update.md` | Update mode stages |
| `references/structure.md` | New mode stages |
| `references/audit.md` | Audit mode stages |
| `references/prose.md` | The prose standard, loaded by every mode |
| `references/frontmatter.md` | Verified semantics of skill frontmatter fields |
| `references/rationale.md` | Why the standard is shaped this way. Not load-bearing; never read at runtime. |

## Credit

The standard is derived from the command layer of [llm-wiki](https://github.com/nvk/llm-wiki).

## License

MIT
