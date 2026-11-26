---
name: timewatch
description: Fill missing days in the TimeWatch attendance report (c.timewatch.co.il) with a default 09:00-18:00, like the TI-TimeWatch Chrome extension. Trigger on "timewatch", "fill timewatch", "fill my attendance", "fill hours report", "דיווח שעות".
---

# TimeWatch

Headless port of the TI-TimeWatch Chrome extension. The script
logs in to `https://c.timewatch.co.il/punch/punch.php`, opens the monthly
attendance report, and for every day marked `חסרה כניסה/יציאה` sets the start
and end time and clicks `עדכן`. By default it fills through the end of the month.

Script: `~/.claude/skills/timewatch/fill_timewatch.py` (run with `uv`; it
installs Playwright on first run).

## Steps

0. **Make sure `uv` is installed.** Run `command -v uv || ls ~/.local/bin/uv`.
   If it's missing, ask the user once: "TimeWatch needs `uv` (a Python
   runner). Install it?" If they agree, run `brew install uv` when Homebrew exists,
   otherwise the official installer `curl -LsSf https://astral.sh/uv/install.sh | sh`,
   and use `~/.local/bin/uv` if `uv` is not on PATH yet. Never install without asking.

1. **Credentials are set up automatically.** On the first run (or with `--setup`)
   the script opens macOS pop-ups for the company number (prefilled with 4630),
   the employee number and the password, and saves them to `~/.config/timewatch_skill/config.json` and the Keychain (service
   `timewatch`). Tell the user to watch for the pop-ups.
   Never ask for the password in the chat. If login fails, the script clears
   the saved password; run it again to get the pop-ups.

2. **No input given (plain `/timewatch`, "fill timewatch"):** fill right away
   with the defaults (09:00-18:00, through the end of the month). Don't ask for
   confirmation. Filling all missing days in the month is the intended default.
   ```bash
   uv run ~/.claude/skills/timewatch/fill_timewatch.py --screenshot $CLAUDE_JOB_DIR/tmp/tw.png
   ```

3. **Input given:** pass the flags it maps to: custom hours `--start HH:MM --end HH:MM`,
   "only until today" `--until-today`, "just check" or "what's missing" `--dry-run`.
   Ask first only if the request is unclear (for example, hours that look like a
   typo).

4. **Report** what was filled, any failed days, and any days still missing. To
   confirm that the page saved the change, read the bottom of the screenshot.
   If a day that was filled before shows up as missing again, just fill it
   without asking. Don't investigate why it's empty and don't run extra checks; only troubleshoot when the script reports a failed day
   or still-missing days after filling.
   If a day fails or a selector seems wrong, run again with
   `--headed --screenshot $CLAUDE_JOB_DIR/tmp/tw.png` (or `/tmp/tw.png`) and read
   the screenshot to see the page.

## Notes

- Network access is needed. If the sandbox blocks PyPI or timewatch.co.il, tell
  the user to run the command themselves with `! uv run ...`.
- The selectors come from the extension: login `#login-comp-input`,
  `#login-name-input`, `#login-pw-input`, `#cpick button[type=submit]`; report link
  `.edit-info .new-link`; day dialog `#ehh0 #emm0 #xhh0 #xmm0`.
- By default, days after today are filled too, through the end of the month. Use
  `--until-today` to skip them; it compares the row date (`dd-mm-yyyy`) to today,
  because the page does not reliably flag future rows. If TimeWatch changes its UI, update the constants
  and selectors in the script.
- The script only works on the month the report opens to (the current month),
  the same as the extension.

## Setup

Nothing to set up by hand: unzip into `~/.claude/skills/` and run `/timewatch`.
The first run asks to install `uv` if needed, then shows pop-ups for credentials.
It uses the installed Google Chrome; if Chrome is missing, Playwright downloads
Chromium (~300 MB) once. Use `--setup` to re-enter the company, employee
number or password later.
