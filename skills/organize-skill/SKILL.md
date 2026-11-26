---
name: organize
description: Tidy the user's computer (macOS, Windows or Linux) — empty Desktop, Downloads and Trash/Recycle Bin and sort everything into topic folders in Documents with English, Title Case names. Asks yes/no before every action, every run can be undone, and it ends with advice on staying organized. Use when the user runs /organize or asks to organize, clean up or tidy their computer, Desktop, Downloads, Documents or Trash.
---

# /organize

You organize the user's files. **Talk to the user in their language**; folder names you create are **English, Title Case** (`Finance`, `Job Applications`) unless the user asks otherwise.

## The script

All file operations go through `scripts/organizer.py` inside this skill's base directory (the "Base directory for this skill" shown above). Never move, rename or delete the user's files with shell commands or file tools yourself.

```
python3 <base-dir>/scripts/organizer.py <command>      # macOS / Linux
python  <base-dir>\scripts\organizer.py <command>      # Windows (or: py -3 ...)
```

| Command | What it does |
|---|---|
| `info` | platform, the real Desktop/Downloads/Documents paths (XDG dirs on Linux, OneDrive redirects on Windows), trash backend, whether the trash is readable |
| `scan [paths...]` | JSON of top-level items (default: the three folders) with `flags`: `duplicate` (+`duplicate_of`), `archive_extracted`, `code_project`, `installer`, `screenshot`, `temp`, `empty_dir`; plus `size`, `modified`, `kind` and `where_from` (download URL) when the OS provides them |
| `check-project <path>` | virtualenvs and scheduled jobs (launchd / cron / systemd / Task Scheduler) that break if the folder moves; `safe_to_move` |
| `apply <plan.json>` | runs `[{"op":"move"\|"rename"\|"mkdir"\|"trash","src":..,"dst":..}]`; never overwrites (adds ` (2)`); `trash` uses the real Trash / Recycle Bin; prints `run_id` + per-action status |
| `undo [run-id]` / `runs` | reverse a run (default: last) / list runs. Items sent to the Windows Recycle Bin are restored from the Recycle Bin by the user |
| `trash-list` | Trash contents, or `{"error":"no_access"}` (exit 2) |
| `empty-trash --yes-really` | **permanent** — only after its own explicit yes |

Write scan output and plan files to a temporary/scratch directory, never into the user's folders.

## Hard rules

1. **Nothing changes without a yes.** Every action belongs to a batch the user approved via AskUserQuestion.
2. "Delete" always means `trash` (recoverable). Permanent deletion only in step 7, separately confirmed.
3. **Code projects** (`code_project` flag, or a folder that clearly is one): run `check-project` first. If `safe_to_move` is false, explain what would break (venv paths, scheduled jobs) and recommend leaving it in place. Otherwise move the whole folder into `Documents/Projects/`, never touch its insides, ask for each one individually, and ask before renaming it.
4. Never reorganize **inside** an existing topic folder unless the user says yes for that folder.
5. Topic → sub-topic, max ~3 levels (`Finance/Taxes/2026` is the deepest).
6. **Protected — never move or rename:** this skill's own folder, anything a symlink or shortcut in `~/.claude/` points into, cloud-sync roots (iCloud Drive, OneDrive, Dropbox, Google Drive folders themselves), and system/app folders.
7. If unsure what something is, **read it** (the Read tool handles PDFs, images and text; list zip contents; check metadata). Don't guess on personal documents. Before trashing an "extracted" archive, verify the folder really contains its files.

## Flow

### 1. Check the environment
Run `info`. If `trash_readable` is false, tell the user in one line how to fix it (macOS: System Settings → Privacy & Security → Full Disk Access → enable the app running Claude Code, then restart it) and continue without listing the Trash.

### 2. Scan
Run `scan > <scratch>/scan.json`, then summarize: counts per folder, duplicates, extracted archives, installers, temp files, code projects, space that can be freed. Peek inside folders whose name says nothing.

### 3. Documents structure
Look at the existing top-level folders in Documents (peek inside ambiguous ones). Propose a taxonomy of **English Title Case** topic folders built from what's there and what's coming from Desktop/Downloads. A typical set — adapt, don't force:
`Finance`, `University` / `School`, `Work` (CV, applications, employers), `Personal` (ID, contracts, health, receipts), `Fitness`, `Publications`, `Books`, `Languages`, `Media` (Photos, Videos, Wallpapers, Designs, Screenshots), `Projects` (code), `Datasets`, `Archive` (old but worth keeping).
Show it as a tree, including renames/merges of existing top-level folders. Ask the user to approve or change it **before anything else**. If Documents is already organized from a previous run, only propose new folders.

### 4. Classify
For every item decide one of:
- **move** → a destination in the approved structure,
- **trash** → with a concrete reason: identical `duplicate` of X, archive already extracted (verified), installer for an app that is already installed (check `/Applications`, `Program Files`, or the package manager), `temp` file (Office `~$` locks, partial downloads), empty folder, files that clearly belong to someone else and were already delivered (ask),
- **ask** → you genuinely can't tell.

Use names, `kind`, `where_from` (a university portal URL → University), dates, and file contents. Group related files across folders (e.g. a challenge ticket in Downloads and its solution script on the Desktop).

### 5. Confirm in batches
Group items by destination (or by trash reason). Use AskUserQuestion, up to 4 questions per call, one question per group. Each question lists the files (up to ~8 names, then "+N more") and the proposed action. Options:
- `Yes` — do it
- `No, leave it` — skip this group
- `Let me choose one by one` — split the group into individual questions next round
(The user can always type a different destination — honor it. If an answer is ambiguous about part of a group, do only the clear part and ask again about the rest.)

Start with the obvious batches (duplicates, temp files, installers, extracted archives) so the count drops fast.

### 6. Apply
Write only the approved actions to `<scratch>/plan-N.json`, run `apply`, and report: moved / trashed / skipped / errors, renamed-on-clash items, the `run_id`, and how to undo ("say 'undo'"). Repeat 4–6 until Desktop and Downloads are empty or hold only what the user chose to keep.

### 7. Trash
Run `trash-list`; show count, size and the biggest items. Ask a **separate** AskUserQuestion: "Empty the Trash permanently? This can't be undone." Only on yes run `empty-trash --yes-really`. If the Trash isn't readable, say so in the question (the user can't see its full contents through you); on macOS `empty-trash` falls back to asking Finder.

### 8. Advice
Finish with a short report (max ~10 bullets): what was done (numbers, space freed), what was left and why, patterns you noticed (many versions of the same CV, zip + extracted folder kept, screenshots piling up, huge folders in Downloads), and concrete fixes for their OS, for example:
- macOS: `defaults write com.apple.screencapture location ~/Documents/Media/Screenshots && killall SystemUIServer`; Finder → Settings → Advanced → "Remove items from the Trash after 30 days".
- Windows: Settings → System → Storage → Storage Sense (auto-empty Recycle Bin and Downloads); move the Screenshots folder via its Properties → Location.
- Linux: GNOME Settings → Privacy → File History & Trash → auto-delete; set the screenshot folder in the screenshot tool.
- Make the browser ask where to save each download; use dated, descriptive names (`CV - Company - 2026-10.pdf`).
- Suggest running `/organize` again in 2–3 weeks.

## Undo
If the user says "undo": run `runs`, confirm which run, then `undo <run-id>` and report. Trashed items are restored too (on Windows, tell them to restore from the Recycle Bin).
