# Keeping the map fresh

When the user says "refresh the code atlas" (or "update the explanations", "explain the new code"):

1. `node $SKILL/scripts/scan.mjs`. Read the summary:
   - "need an explanation" means new boxes.
   - "changed since explained" means the code changed under an existing explanation.
   - Warnings about missing boxes mean something was renamed or deleted. `scan.mjs` already moves explanations whose code did not change.
2. List what needs work:
   `node -e "global.window={};require('./code-atlas/data.js');for(const n of window.MAP.nodes.filter(n=>n.status!=='ok'))console.log(n.status,n.id)"`
3. For each one, read the current code, then rewrite its entry, or add it, in the matching `explain/*.json` file. For a changed box, delete its old `hash`, and check its `beginner.io`, Play steps and any story scenes that mention it.
4. Delete entries for boxes that no longer exist (the warnings name them), and fix tours and plays that point at them.
5. `node $SKILL/scripts/scan.mjs --stamp`, then reopen `code-atlas/index.html`.

## The automatic rescan (optional)

`node $SKILL/scripts/install-hook.mjs` adds a git post-commit hook that runs the scan after each commit. Ask the user before installing it. It:
- writes the full Node path into the hook, so it works from GUI git apps;
- never blocks a commit;
- writes its output to `code-atlas/scan.log`;
- adds to an existing post-commit hook instead of replacing it.

Remove it with `node $SKILL/scripts/install-hook.mjs --remove`.

## Upgrading the viewer

`node $SKILL/scripts/init.mjs` again copies the latest `viewer.html` to `code-atlas/index.html`. It never overwrites `config.json`, `theme.json` or `explain/` unless you pass `--force`.
