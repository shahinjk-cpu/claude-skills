---
name: claude-console
description: Multi-project dashboard and terminal console for agentic execution. Live project board, auto-relay cycles, quota & token battery tracking, interactive Git branch graphs, and cross-model task dispatching (Claude, Codex, Gemini).
triggers:
  - claude console
  - multi-project console
  - quota battery
  - auto relay
  - project board
category: general_tools
---

# claude-console

**A console for keeping several projects moving from inside Claude Code.** One pane shows where every project stands and who it is waiting on; decisions are pressed, dispatch is one button, and Git, PR, CI and quota sit beside them, so you don't switch windows.

<p align="center"><a href="docs/demo.mp4"><img src="docs/demo.gif" alt="claude-console demo: /console demo opens the console, n opens what waits on you one by one, number keys answer a decision and fill it into the prompt; then five real Git projects with the branch graph, a commit's details and ⟳ auto-cycle" width="900"></a></p>
<p align="center"><a href="docs/demo.mp4">▶ Watch the 65-second demo (MP4)</a> · <a href="#version-history">Version history</a> · <a href="README.md">繁體中文</a></p>
<p align="center"><sub>The real screen of Claude Code 2.1.308 with console-status 0.32.0 in a terminal (captured frame by frame with tmux, then encoded). The first half shows <code>/console demo</code> data, the second half five Git projects the <a href="scripts/demo-video">recording script</a> builds; the captions and mouse pointer were added afterwards, and the recording host's own startup warnings removed.</sub></p>

## Quick start

1. **Install.** Type these two lines in Claude Code; the plugin works at once, no restart. Press Esc on the settings screen the install opens to keep every default. To install from a terminal, see [Install](#install).

   ```text
   /plugin marketplace add SaM-runtime/claude-console
   /plugin install console-status@claude-console
   ```

2. **See the demo.** `/console demo` shows the whole pane with no project at all; `/console refresh` goes back to your own data.
3. **Add your projects.** Open Claude Code in a project's folder and run `/console add`. It makes the registry and the STATUS card (`.console/STATUS.md`) for you, once per project (see [Adding a project](#adding-a-project)).
4. **Use it.** Run `/console` in any session to open the pane. Write a next step in the project's CARD (`o` in the action menu opens the file; change `- 下一步：無` to the task), press `⇢ 繼續下一步`, and a background executor does it. From then on, what waits on you sits in the next-step card, and `n` walks through it.

Every setting has a default, so nothing needs configuring; to change one, see [Configure](#configure).

## Features

- **Every project in one table.** One row per project: its state (`●` decision needed, `◆` awaiting review, `▶` running, `↻` needs sync, `○` idle), a six-step pipeline (spec → build → sync → verify → review → release), when it was updated, and a Git summary. The next-step card on top names the one thing to handle now, and when nothing waits on you it names a project you can continue instead (`⇢ 沒有在等你，可以繼續`, with its continue button); an idle project with a next step shows `⇢ <next step>` in its row, apart from projects with nothing to do; a project with something left to do and no CARD change for days gets an amber age and `久未動`, and is offered first (`staleDays`). `n` jumps to each thing waiting on you in turn (decisions, gates, syncs, failed CI, failed verifications) and opens its action menu; `/console inbox` lists the same as text. With the pane closed, the band above the prompt still counts each state. See [Project actions](#project-actions) and [Pipeline and project mode](#pipeline-and-project-mode).
- **Decisions are pressed, not typed.** Every option in a card can be pressed; with the action menu open, number keys answer the decisions in order (`2` then `1` reads `1B 2-1`) and Backspace takes the last pick back. `✎ 填入決策` or `✎ 做決定` puts the answer in the prompt; Enter sends it.
- **One-button actions.** Verify, sync STATUS, continue to the next step, review a gate, open STATUS.md: right-click or `m` opens the action menu, and every action has a single-key shortcut. When an executor finished without writing the CARD back, the console dispatches one sync by itself (`autoSync`) and shows its progress step by step. An executor 
