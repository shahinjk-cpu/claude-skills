# Guide for agents

How to change skill-souffleur without breaking it. Read `README.md` for what it does and `docs/design.md` for how it works.

## What this repo contains

A Claude Code mod written in TypeScript. `src/core/` holds the rules, the ledger and the decisions, with no import of the mod API. `src/mod/` is the thin adapter that wires Claude Code events to the core. The mod API is early access and changes between releases; keeping it out of the core keeps those changes in one place.

## Changing code

- Start with a failing test. Test the core directly with recorded event sequences.
- Fixtures come from real sessions. Remove personal data and local paths before you commit one.
- When a change depends on Claude Code behaviour, name the version you verified it on in `docs/compatibility.md`.
- Add no runtime dependency without a reason stated in the pull request.

## Conventions

- English everywhere: code, comments, docs, commits.
- Conventional Commits. One change per pull request, merged with squash.
- Add an "Unreleased" entry to `CHANGELOG.md` for changes users notice, and update the roadmap in `README.md` when an item lands.
