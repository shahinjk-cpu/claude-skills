# timewatch

A [Claude Code](https://claude.com/claude-code) skill that fills missing days in the
[TimeWatch](https://c.timewatch.co.il) attendance report (09:00-18:00 by default,
through the end of the month). It's a headless version of the TI-TimeWatch Chrome extension.

## Install

```bash
git clone https://github.com/tomerbendror/timewatch-skill ~/.claude/skills/timewatch
```

Restart Claude Code, then run `/timewatch`.

## First run

- If [`uv`](https://docs.astral.sh/uv/) isn't installed, Claude asks before installing it.
- macOS pop-ups ask for your company number (default 4630), employee number and password.
  The password is stored in your macOS Keychain, never in a file.
- It uses your installed Google Chrome (or downloads Chromium once if Chrome is missing).

## Usage

- `/timewatch`: fill every missing day this month
- `/timewatch just check`: list missing days without changing anything
- `/timewatch 08:30 to 17:30`: custom hours
- `/timewatch only until today`: skip future days

Re-enter credentials: `uv run ~/.claude/skills/timewatch/fill_timewatch.py --setup --dry-run`

## Update

```bash
git -C ~/.claude/skills/timewatch pull
```

Requires macOS.
