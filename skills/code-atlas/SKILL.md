---
name: code-atlas
description: Turn any codebase, in any programming language, into a private, visual, beginner-friendly website that explains how the code works. It shows a zoomable map of areas, folders, files and functions with plain-English explanations, wires showing who calls whom, step-by-step "Play" walkthroughs, clickable code that points into the map, a Beginner view with jobs and inputs/outputs, a Story view that retells the code as a town (or any world) with characters, scenes and quizzes, and a knowledge-graph view of every file and function and how they connect (exportable as JSON and GraphML). Use this skill whenever someone wants to understand, learn, explore, onboard onto, visualise, map or explain a codebase or repository ("help me understand this repo", "explain this project visually", "make a map of my code", "I'm new to this codebase", "how does this app work", "show me how my code connects", "knowledge graph of my code"), even if they don't say "map" or "skill".
---

# Code Atlas

Builds a local website (`code-atlas/index.html`) that explains a codebase visually. One person learns from it in a browser: an overview of areas, then folders, files and functions, each with a plain-English explanation and the real code. It has three views:

- **Map:** boxes and wires.
- **Beginner:** the same map with job badges (Boss, Worker, Helper, Ingredients, Decoration), wires that say what happens, Takes in → Does → Gives back, Play and Follow.
- **Story:** the code retold as a town (or any world) with characters, scenes, a code peek and a quiz.
- **Graph:** a knowledge graph of the whole codebase. Every file (or function) is a dot coloured by area, and every connection is a line. Click to light up neighbours, double-click to open in the map, and download JSON or GraphML. `scan.mjs` also writes `code-atlas/graph.json` and `code-atlas/graph.graphml` for tools like Gephi, yEd, Cytoscape or a graph database.

The engine is in `scripts/` and `assets/`. Your part is understanding the code and writing explanations that are true, plain and useful. The scanner does the rest.

**Supported runtime:** Claude Code (or any agent with a shell, Node 18+ and a checkout of the repo). Python 3 and the TypeScript compiler are optional; when present they make JS/TS and Python reading exact, and when absent a plain-text reader handles every language.

## Privacy first

The output contains copies of the code. Keep it local:
- `init.mjs` writes it to `<repo>/code-atlas/` and adds that folder to `.git/info/exclude`.
- Never commit it, publish it, or upload it as an artifact.
- Secrets and dependency folders are excluded by default (`.env*`, keys, `node_modules`, `vendor`, lockfiles, builds, minified files).
- If the user wants something shareable, make a separate copy with personal or company details removed, and ask first.

## Workflow

Run the scripts with the skill folder as `$SKILL` (the folder this file is in).

1. **Look around.** Read the README, the top folders and a few entry points (`main`, `index`, routes, CLI commands, package scripts), so you know what the project does and how it is organised. Ask the user what they want to learn first if it isn't obvious.
2. **Set up.** Run `node $SKILL/scripts/init.mjs` in the repo. It copies the viewer, writes a starter `code-atlas/config.json` (areas guessed from folders) and `code-atlas/theme.json` (the project's own brand colour and fonts if it has them), a starter glossary, and prints what it found.
3. **Edit `config.json`** (see `references/config.md`):
   - Give the areas clear human names and one-line descriptions. 4 to 9 areas is ideal; merge or split the guesses.
   - Set the order of `lanes` so the overview reads left to right in the direction things flow (for example: shared code, then the apps, then build and deploy).
   - Add `content` boxes for big folders of words or data (posts, fixtures, migrations), so they appear as one box instead of hundreds.
   - Choose a story `world` that fits the project if a town doesn't (a kitchen for a food app, a hospital for a health app). Give each area a `place` name in that world.
4. **Ask about colours.** Before scanning, ask the user which colours they want; the map is theirs to look at every day. Use the question tool if you have one, otherwise ask in chat. Offer:
   - **The project's brand colours (default):** the accent and fonts `init.mjs` found, with the source it reports, for example "`--brand-primary` #E11D48 in web/src/styles.css". If it found none, say so and make the neutral blue the default.
   - **A suggested palette** that fits the project, for example calm blues for a finance app or warm tones for a food app. Name the accent and the mood.
   - **Their own colour:** a hex code or a colour name you turn into one.
   - Optionally, whether the area colours should follow the accent (one family spread around the colour wheel, which `init.mjs` already does) or stay all in one hue.

   Write the answer into `theme.json` (`accent`, optional `accentText` and fonts), and into the area `color` fields in `config.json` if the palette changed. Keep the area colours at a similar lightness and saturation so they read as one family, and check that `accentText` on white reaches 4.5:1 contrast. Everything must stay inside the output folder: Safari refuses fonts and stylesheets from outside it.
5. **Scan.** Run `node $SKILL/scripts/scan.mjs`. It prints counts and any `COVERAGE PROBLEM`. If boxes look wrong (missing functions, odd names), check the language notes in `references/config.md` and adjust `exclude`, `include` or `groupNames`.
6. **Explain, overview first.** Write explanation files in `code-atlas/explain/` (format: `references/explain-format.md`; how to write them: `references/writing.md`). Start with every area, group and file, then the main functions: entry points, the busiest functions, and anything the user asked about. Leave the rest. They show "needs explanation", and the user can ask for a section later ("explain the billing area"). On a large repo, tell the user roughly how much is explained and offer to continue.
7. **Beginner layer and stories.** Add takes-in / gives-back text and wire labels for the explained boxes, hand-written Play steps for each area, and a hand-written overview story. Every other level gets a story built automatically from that data. Hand-write stories only where the generated one reads flat.
8. **Stamp and check.** Run `node $SKILL/scripts/scan.mjs --stamp` to record a fingerprint of the code each explanation describes. Then open `code-atlas/index.html` and check it: with Playwright if available (every level draws, no console errors, Play and Story run), otherwise ask the user to open it.
9. **Keep it fresh (ask first).** Offer `node $SKILL/scripts/install-hook.mjs`, a local git post-commit hook that rescans after every commit. New or changed functions then show "needs explanation" or "code changed", and the user asks you to "refresh the code atlas" (see `references/refresh.md`).

## What good looks like

- **True:** every explanation comes from reading that code, not from its name. If you are unsure what something does, read its callers. If you still can't tell, say so in the text rather than guess. Label made-up examples as made up.
- **Plain:** write for someone who has never coded. Use short sentences, explain each technical word in the same sentence or add it to the glossary, and give one concrete example per box where it helps ("'70B' becomes 70 and 'B'").
- **Readable on screen:** the scanner groups folders so no screen has more than about a dozen boxes. If a level is still crowded, add `groupNames` or split the area.
- **Honest about guesses:** wires the scanner only guessed by name are marked approximate. When an important wire is missing (code that loads things by name at run time), add it under `edges` in `config.json`.

## Files

- `scripts/init.mjs`: setup, brand detection and starter config.
- `scripts/scan.mjs`: reads code in any language and writes `data.js`, theme CSS and fonts, plus `graph.json` and `graph.graphml` (nodes, and edges of kind calls, imports, runs, reads, opens, shows, uses and contains).
- `scripts/install-hook.mjs`: optional post-commit rescan.
- `assets/viewer.html`: the website, copied to `code-atlas/index.html`.
- `references/config.md`: `config.json` and `theme.json` fields, and per-language notes.
- `references/explain-format.md`: explanation, tour, glossary, beginner and story file formats.
- `references/writing.md`: how to write explanations, Play steps and stories that a beginner can follow.
- `references/refresh.md`: updating after code changes.
- `examples/explain-example.json`: a small made-up example of every section.
