---
name: commit
description: Makes one conventional commit from the current changes - reads the staged diff, writes a type(scope) subject that says why, commits locally and never pushes or amends. Use when asked to "commit", "commit this" or "save this work", or when a skill needs a clean commit of what is staged.
argument-hint: "[type(scope) hint]"
---

<!-- Adapted from coleam00/skills .claude/skills/piv-commit/SKILL.md (MIT) -->

# Commit

One commit, conventional format, for exactly the changes the owner or the calling skill means. Release tooling
reads these messages to pick versions, so the type and scope matter.

## Steps

1. `git status --short` and `git branch --show-current`. On the default branch, stop and tell the owner; a
   build never commits there.
2. Decide what goes in. Staged files are the intent; if nothing is staged, stage the files the task touched by
   name (never `git add -A` or `.`, which sweeps in secrets and scratch files). Unrelated changes stay out:
   say so and offer a second commit.
3. Read the staged diff (`git diff --staged`) before writing the message. If it mixes two concerns, make two
   commits, one at a time.
4. Write the message: `type(scope): subject`, imperative, at most 72 characters, saying what changed and why
   rather than listing files. Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`,
   `build`. A breaking change gets `!` after the scope and a `BREAKING CHANGE:` footer. Add a body only when
   the why is not obvious from the subject. Add any attribution line the session or project instructs.
5. Commit with `git commit`. If a hook blocks it (the security gate, a linter), read the reason and fix the
   cause; never bypass with `--no-verify`.
6. Report the short sha and subject.

## Rules

- A single commit per run. Never amend, rebase or otherwise rewrite history, and never force anything.
- Never push: pushing belongs to the skill that owns the branch (`/build:implement`, `/build:pr`).
- No secrets, no files outside the task, no personal data in the message.
