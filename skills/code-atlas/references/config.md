# config.json and theme.json

Both live in the output folder (default `<repo>/code-atlas/`). `init.mjs` writes starters; edit them by hand, then rerun `scan.mjs`.

## config.json

```json
{
 "title": "shop",
 "areas": [
  { "id": "api", "name": "Order API", "sub": "answers the shop's web requests", "match": ["^api/"], "color": "#60A5FA", "icon": "server", "place": "Market Street" }
 ],
 "content": [
  { "id": "content:migrations", "area": "api", "name": "Database changes", "match": ["^api/migrations/"], "what": "One file per change to the database, applied in order." }
 ],
 "include": ["^vercel\\.json$"],
 "exclude": ["^docs/generated/"],
 "groupNames": { "web/src/components": "Screen pieces" },
 "edges": [{ "from": "web/src/router.ts#loadPage", "to": "web/src/pages/Home.vue", "kind": "opens" }],
 "lanes": [["Shared", "used by everything", ["lib"]], ["Apps", "what people use", ["web", "api"]]],
 "world": { "town": "Town", "neighbourhood": "neighbourhood", "building": "building", "person": "person" },
 "maxFileKB": 300, "maxFiles": 4000, "groupAt": 12
}
```

- **areas:** the top level of the map, in priority order. A file belongs to the first area whose `match` regular expression matches its path (paths use `/`, relative to the repo root). Files no area claims go to an automatic "Everything else" area; add an area for them if there are many.
  - `icon` is one of: box, code, book, server, database, globe, cog, image, film, video, wrench, upload, palette, user, test, mobile, chart.
  - `place` is the area's name in the story world.
  - `color` is a hex colour; keep all areas at a similar lightness.
- **content:** groups of non-code files (posts, data, fixtures) shown as one box. Matched files are removed from the code boxes.
- **include / exclude:** extra regular expressions. `include` turns non-code files (settings, schemas) into file boxes. Secrets, dependencies, builds, lockfiles and minified files are always excluded.
- **groupNames:** friendly names for automatic folder groups, keyed by folder path.
- **edges:** wires the scanner cannot see, such as code that loads a page by a name built at run time. Ids are box ids (see below). `kind` is one of calls, imports, runs, reads, opens, shows or uses.
- **lanes:** the overview's columns, read left to right. Omit it to show all areas in one column.
- **world:** nouns for the Story view.
- **Limits:** `maxFileKB` (larger files are skipped), `maxFiles`, and `groupAt` (a container with more files than this gets folder groups, repeatedly).

**Box ids:**
- Areas are `area:<id>`.
- Folder groups are `group:<folder path>`.
- Files are their path.
- Functions are `<file path>#<name>`. Methods use `Class › method`. Unnamed code that runs by itself is `(runs on load)`. Astro frontmatter is `(build-time setup)`. Script blocks in Vue, Svelte, Astro and HTML are `(script 1)`, `(script 2)` and so on, numbered in order. A name that repeats in one file gets ` (2)`.
- Content boxes use the `id` you give them.

## theme.json

```json
{
 "accent": "#E11D48",
 "onAccent": "#FFFFFF",
 "fonts": { "head": "'Nunito', sans-serif", "body": "'Inter', sans-serif", "mono": "'Fira Code', monospace" },
 "fontFiles": [{ "family": "Nunito", "weight": "400 800", "path": "web/public/fonts/nunito.woff2" }],
 "light": { "bg": "#FFFFFF", "text": "#111111", "accentText": "#BE123C" },
 "dark": { "bg": "#0F0F10" }
}
```

- `accent` is the brand colour used for selection, progress and highlights.
- `accentText` is the accent used as text. Make sure it reads on the background (at least 4.5:1 contrast).
- `fontFiles` are copied into `code-atlas/assets/fonts/`. With no font files, the named fonts are used only if the computer has them; otherwise system fonts.
- Other optional colours, in both `light` and `dark`: bg, s1, s2, s3 (surfaces), border, text, copy, muted, dim.
- Nothing is loaded from the internet.

## How languages are read

- **JS/TS/JSX/TSX:** exact with the TypeScript compiler when it can be found (the project's `node_modules` or a global install). Otherwise plain text: function declarations, arrow functions, methods and classes.
- **Vue / Svelte / Astro / HTML:** `<script>` blocks and Astro frontmatter as code. Capitalised tags in the template show which components a file uses.
- **Python:** exact with `python3`'s `ast`. Otherwise plain text by indentation.
- **Plain text, by brace matching:** Go, Rust, Java, C#, C/C++, Kotlin, Swift, Scala, Dart, PHP, Groovy, R.
- **Plain text, by indentation and `end`:** Ruby, Lua and Elixir (and Julia, read as Ruby).
- **Shell:** functions, plus the code that runs.
- **Makefile and package.json scripts:** each target or script is a box.
- **Everything else** (SQL, CSS, config): file boxes only.

**Calls:**
- Calls are matched by name inside a file first.
- Then through imports.
- Last, by a name that only one function in the whole repo has. These wires are marked approximate.
- Calls made through variables, reflection or dependency injection are invisible. Add the important ones as `edges`.

**Imports:** resolved by path, including Python dotted names, Java and Go package paths, and PHP and Rust `use`.

**Scripts that start other scripts:** found where a file name appears on a line that runs something (shell lines, `subprocess`, `exec`, `spawn`).

**Changing reader:** if the TypeScript or Python reader appears or disappears between scans, fingerprints change and many boxes show "code changed". `scan.mjs` warns when this happens. Use the same setup each time, or `--generic` always.
