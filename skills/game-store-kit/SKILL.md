---
name: game-store-kit
description: Play a Capacitor or Unity Android game and produce a premium, fully consistent Google Play kit: full-bleed captioned screenshots, a key-art feature graphic and splash, the 512 app icon and launcher-icon layers. Use when the user runs /game-store-kit or asks for Play Store screenshots, store graphics, an app icon or splash, or to make their game's store listing look premium. Supports Capacitor (web games wrapped for Android) and Unity games, Google Play only.
---

# Game Store Kit

**Scope:** Capacitor games (web games wrapped with Capacitor) and Unity games, Android, **Google Play only**. If `detect.mjs` reports `unsupported`, tell the user and stop.

Run inside a game's folder. You **play the game for real**, capture the best moments, and turn them into a store kit that looks like one art director made every piece.

Scripts live in `~/.claude/skills/game-store-kit/scripts`.

## Output location — hard rule

**Every generated file goes into `<PROJECT>/store-assets/`**, where `<PROJECT>` is the game project the user is working in (the session's working directory; if that is a subfolder, its nearest parent with `.git` / `package.json` / `pubspec.yaml` / `project.godot` / `ProjectSettings` / Gradle settings).

1. At the very start, resolve it once and keep it for the whole run:
   ```bash
   PROJECT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; export GSK_PROJECT="$PROJECT"; mkdir -p "$PROJECT/store-assets"; echo "$PROJECT/store-assets"
   ```
   Tell the user this path in one line before starting. Prefix every script call with `GSK_PROJECT="$PROJECT"` (shell state does not persist between commands) and use absolute paths under `$PROJECT/store-assets` for every file you write.
2. Never write outputs to the home folder, `/tmp`, the scratchpad, the skill's own folder, or any other project. If you `cd` (e.g. into a build dir), outputs still go to `$PROJECT/store-assets`.
3. **Logo work too:** when using the `logo-generator` skill, put its concepts, showcase page and PNG exports in `$PROJECT/store-assets/icon/concepts/` — not in a `logos/` folder or anywhere else.
4. **The skill never modifies the project.** Read the game's files, but never edit, create or delete anything outside `store-assets/`: no copying icons into `android/res`, no `.gitignore` edits, no `npm run build` into `dist/`, no `cap sync`, no Gradle or Unity builds into the project's own folders. If a build is needed to play the game, build a **copy** into `store-assets/work/build/` (Capacitor: `npx vite build --outDir "$PROJECT/store-assets/work/build/web" --emptyOutDir`; Unity: a batch-mode build with its output path under `work/build/`, only with the user's OK). If a build cannot avoid writing into the project (e.g. Android Gradle), ask the user first and say exactly what it will touch.
5. The folder must be **self-contained and movable**: the user moves `store-assets/` out of the project afterwards. All paths inside it are relative to it, and the last step (`pack.mjs`) leaves only what's needed.

Final contents of `store-assets/` (after pack): **only what's needed to publish on Google Play**, the same for Capacitor and Unity:
```
play-store/                        -> Play Console > Store listing
  icon-512.png                     App icon
  feature-graphic-1024x500.png     Feature graphic
  screenshots/phone-01..08.png     Phone screenshots (in order)
  screenshots-7inch/  screenshots-10inch/   Tablet screenshots (when plan.tablet is on; 4+ each to be featured on tablets)
  store-listing.md                 App name, short + full description, release notes, category, tags (paste-ready)
  publish-checklist.md             Publish-readiness report: target SDK, 64-bit/16 KB, version code, permissions, plugins
android-icon/                      1024px launcher-icon layers
  foreground.png  background.png   Android Studio > res > New > Image Asset (Foreground/Background layer -> Path),
                                   or Unity Player Settings > Icon (adaptive)
splash/                            designed key-art splash
  splash-1080x1920.png  splash-1920x1080.png  splash-2732x2732.png
```
Only if the user asks for the `@capacitor/assets` CLI: set `"capacitorAssets": true` in brand.json to also get `capacitor-assets/` (icon-only, icon-foreground, icon-background, splash, splash-dark).
Plus a hidden `.kit/` (invisible in Finder) holding the sources: brand.json, plan.json, icon layers and concepts, logo/sprites/items, the play script, the key-art page, and only the frames the kit uses. That's what makes the next run look exactly the same. During a run, everything lives visibly in `store-assets/` (plus scratch in `work/`). Pack hides the sources and deletes the rest. `pack.mjs --no-kit` drops the sources too (the next run starts from scratch); `--full` keeps everything visible.

**Golden rule — one brand bible, kept across runs.** `store-assets/brand.json` is the single source of truth (palette, fonts, style). Every template reads it, so icon, splash, feature graphic and screenshots share the same colors, type, background system and grain.
**At the start of every run**, if `store-assets/.kit/` exists (detect.mjs says so), first run:
```bash
GSK_PROJECT="$PROJECT" node ~/.claude/skills/game-store-kit/scripts/pack.mjs --restore
```
Then **reuse brand.json, the icon and the key-art page unchanged** unless the user asks for a new look. Re-capture gameplay and update `plan.json` (new frames, new features) only where the game changed. The user should get an update that clearly belongs to the same game, not a redesign.

## 0. Setup (first run only)

```bash
[ -d ~/.claude/skills/game-store-kit/scripts/node_modules ] || (cd ~/.claude/skills/game-store-kit/scripts && npm i --silent)
```
Needs Google Chrome (used headless), Node 18+, Python 3 with Pillow (`pip3 install pillow`). Android capture uses `adb`/`emulator` from `~/Library/Android/sdk`.

## 1. Understand the game (don't skip)

1. `node ~/.claude/skills/game-store-kit/scripts/detect.mjs "$PROJECT"` → engine, name, orientation, package id, web build, APKs, art and fonts.
2. Read the README, the main scene/game loop, input handling and menus. Write down: **controls**, **how to start a run**, **what an exciting moment looks like** (combo, boss, big explosion, level up, full board, near-win), **what progression exists** (levels, upgrades, characters, worlds), and anything you should avoid capturing (debug overlays, dev menus, ads).
3. Look at the hero art (Read the images detect listed): character, key objects, existing logo, fonts. **Beware template placeholders**: Capacitor starter icons and splashes (the blue Capacitor "X") and Unity's default icon are not the game's brand. Ignore them.
4. **Verify orientation** from detect *and* the first captured frame. If the game is letterboxed (capture-web aborts with `⚠ ORIENTATION`), switch `--landscape` on or off. Never build a kit from letterboxed frames.
5. **Find the hooks you'll drive it with.** Look for: an existing demo/attract-mode AI (e.g. `ai()`, `autoplay`, `bot`), debug flags (`?debug`, `window.__debug`), save keys in localStorage, start functions (`startGame(mode, opts)`), and menu actions (`data-act`, button ids). If the game code is wrapped in a closure/IIFE, globals won't be reachable from `page.evaluate`: use the debug hook (`--query debug`) or click its own UI buttons.

## 2. Brand bible → `store-assets/brand.json`

If missing, create it. Pull colors from the game itself, not your imagination:
`python3 ~/.claude/skills/game-store-kit/scripts/palette.py <3-6 key art files or early frames>`

```json
{
  "name": "Neon Drift",
  "engine": "capacitor",
  "tagline": "One thumb. Endless speed.",
  "genre": "arcade racer", "mood": "electric, fast, night-city",
  "orientation": "portrait",
  "colors": { "primary": "#5b21ff", "secondary": "#ff2d95", "accent": "#ffe14d", "dark": "#0a0620", "light": "#ffffff", "text": "#ffffff" },
  "fonts": { "display": "Lilita One", "body": "Nunito" },
  "style": { "corner": 0.06, "grain": 0.07, "upper": true, "blurShot": true,
             "device": "bleed", "floaters": 4 },
  "logo": null,
  "items": ["brand/items/coin.png", "brand/items/gem.png", "brand/items/powerup.png"]
}
```
Rules:
- `engine`: copy it from detect.mjs (`capacitor` or `unity`); used in the hand-off instructions.
- `primary` = the game's dominant saturated hue, `dark` = a deep shade of it (never pure #000), `accent` = the hottest highlight in the game (used for highlighted words, glow, badges), `secondary` = a supporting hue for background blobs. Check contrast: light text on primary/dark must be readable.
- Fonts are Google Fonts family names (or `displayFile`/`bodyFile` paths to the game's own font files, relative to `store-assets/`). Pick a display face that matches the genre: chunky rounded (Lilita One, Luckiest Guy, Titan One, Baloo 2) for casual; condensed/techy (Bebas Neue, Russo One, Orbitron, Chakra Petch) for action/sci-fi; serif display (Cinzel, Cormorant) for fantasy/RPG; pixel (Press Start 2P, Silkscreen) only for pixel-art games. If the game ships a font, prefer it.
- `logo`: path to a transparent wordmark PNG if the game has one; otherwise titles are set in the display font. **If the logo is drawn in the DOM (SVG/HTML title), grab it for real**:
  `GSK_PROJECT="$PROJECT" node ~/.claude/skills/game-store-kit/scripts/grab.mjs --root <webBuild> --selector ".logo svg" --play <play.mjs> --out "$PROJECT"/store-assets/brand/logo.png`
- **Unity art**: Unity games ship their art as files. Start with `unityArt` from detect.mjs (textures already wired as the icon, splash logo or splash background) and `unitySprites` (player, enemies, coins, logo...). **Copy** the PNGs you need into `store-assets/brand/` (`sprites/`, `items/`, `logo.png`); never edit them in place. Pillow can flatten a `.psd` to PNG. Sprite sheets/atlases: crop the single sprite you need. If the in-game look comes from 3D models or shaders, use clean gameplay frames (`droid.mjs shot`) and crop the hero from them.
- **Real character art (Capacitor):** if characters are drawn in code (canvas), render them yourself at high resolution on transparent canvases through `page.evaluate` (call the game's own draw function with a big scale, trim, save as data URL) into `store-assets/brand/sprites/`. Use them for the icon and `decor`.
- Cartoon games with outlined type: set `style.textStroke` (the outline color, usually the game's ink color) and `style.strokeWidth` (≈0.012). If the icon uses a sunburst, set `style.burst` (`{"opacity":0.1,"glow":0.6}`) so the splash, feature graphic and screenshots echo it. `style.headline` (default 0.115 × width) is the one headline size for the whole set.
- `style.device`: **`"bleed"` (default)**: full-bleed gameplay, the style top games use and Google recommends (no device imagery). Other values: `"phone"`, a modern unbranded phone mockup (iPhone-18-like; `deviceFinish`: `black` | `silver` | `desert` | `brand`); Google discourages device frames, which can limit featuring. `"none"`: rounded cards. Use `phone` only if the user asks for it, e.g. for social posts.
- `items`: real collectibles/power-ups/enemies from the game as transparent PNGs (`brand/items/`). They float around the phone at different depths, decorate chips, and bridge between screenshots. **Get them from the game's own draw code**: if the code lives in a closure, make an *instrumented copy* of the web build in `store-assets/work/build/web` (inject `window.__gsk = { drawItem, drawEnemy, ... }` before the closure ends) and render each item at high scale on a transparent canvas, then trim. Never edit the real project build.
- `palette.py` prints `dominant` (often muddy) and `vivid` colors (characters, logo, FX). Brand colors usually come from `vivid` plus the logo.

## 3. Play the game and capture

Aim for **60–200 frames** from real play across different moments. capture-web defaults to a modern phone screen (402×874 @3x = 1206×2622, 19.5:9; landscape 2622×1206), so frames fill the phone mockup exactly.

**Capacitor games** (and Unity games that have a WebGL build): play the web build in headless Chrome.
1. Write `store-assets/work/play.mjs` tailored to THIS game from what you learned in step 1:
```js
export async function before({ page }) {                // before load: seed a save so the tutorial is skipped and content is unlocked
  await page.addInitScript(() => localStorage.setItem('<saveKey>', JSON.stringify({ tutorialDone: true /* ... */ })));
}
export async function setup({ page, sleep, shot }) {    // get past title / tutorial; shot('home'), shot('map') of progression screens
  await page.mouse.click(270, 700); await sleep(1500);
}
export default async function step({ page, t, i, sleep, w, h, shot }) {
  // real strategy: dodge, aim, jump on rhythm, merge matching tiles... not random mashing
  // you can call page.evaluate() to read game state (score, enemies) and react to it,
  // or to make the scene more spectacular (spawn more enemies, unlock a later level, give power-ups)
  // call await shot('boss') at peak moments to force a capture
  // return 'stop' to end early (e.g. after the last planned session)
}
```
Best strategy when the game has its own AI: drive it from a `setInterval` in the page (`G.ai(dt)`), keep the run alive (top up lives), and play **one short session per world/era/mode/boss/character** (about 15s each) so the frames cover everything. Turn sound off in the seeded save.
2. Run it (portrait default; add `--landscape` for landscape games; `--url` for a dev server; `--query debug` to append `?debug`; `--selector canvas` to crop to the game canvas):
```bash
GSK_PROJECT="$PROJECT" node ~/.claude/skills/game-store-kit/scripts/capture-web.mjs --root <webBuildDir> --play "$PROJECT"/store-assets/work/play.mjs --out "$PROJECT"/store-assets/work/raw --duration 120 --interval 1200
```
3. If the frames show the game didn't start, died instantly or is stuck on a menu: fix `play.mjs` and re-run. Check `raw/_console.log` for errors. Several short sessions (different levels/modes) beat one long one.

**Unity games** (APK): play the developer's existing APK on the Android emulator with `droid.mjs`. Unity has no JavaScript hooks, so you play by **looking**: take a screenshot, decide, act, repeat. Coordinates are pixels or percentages (`tap 50% 80%`), so they work on any screen size.
```bash
D=~/.claude/skills/game-store-kit/scripts/droid.mjs; RAW="$PROJECT/store-assets/work/raw"
node $D boot --headless                 # start (or reuse) the emulator; prints Android version and screen size
node $D install <path/to/game.apk>      # an .aab can't be installed: ask for an APK
node $D demo on                         # 9:41, full battery, full signal, no notifications
node $D launch <package.id>             # waits past the system splash / "Made with Unity" / loading until the game settles
node $D shot "$RAW/home.png" --view     # Read the .view.png: a small copy with a 10% grid to read coordinates from
node $D step tap 50% 73% --out "$RAW" --frames 2 --gap 500   # act, then capture the result (+ .view.png of the last frame)
```
Loop `step` (look → decide → act) through menus, tutorials and into real gameplay, and to reach specific moments (a boss, a new world, the shop). Once you know the game's rhythm, write `store-assets/work/plan.txt` and let it play while frames are captured in the background:
```
# plan.txt (coordinates in % or px)
repeat 6 {
  tap 50% 50%
  wait 700
}
swipe 30% 70% 70% 70% 200
hold 50% 60% 900
shot boss
```
```bash
node $D play --plan "$PROJECT/store-assets/work/plan.txt" --out "$RAW" --duration 90 --interval 1.2
node $D demo off && node $D stop        # stop only shuts down an emulator droid.mjs started
```
Notes:
- Frames are captured **without** the status and navigation bars (cropped automatically when visible; full-screen games are untouched). `--no-crop` keeps them.
- Frames are the emulator's real resolution (Pixel 9 Pro: 1280×2856 minus bars). The full-bleed screenshot layout zooms them anyway.
- `adb` input has ~100–200 ms latency: for reflex-heavy moments, capture many frames (`play` with a short `--interval`) and let `pick.py` find the good ones, rather than trying to time a single shot.
- `install` explains the common failures: no ARM64 code (Unity: Player Settings > Other Settings > Target Architectures > ARM64, which Google Play requires anyway) and a different signing key already installed.
- Unity WebGL build available? `capture-web.mjs --root <WebGL build folder>` can play it in headless Chrome (the server sends `.br`/`.gz` builds with the right encoding). Not yet tested with a real Unity WebGL build, so check the first frames; if it fails, use the APK.

**Unity project without any build:** ask the developer to build an APK (File > Build Settings > Android > Build). Building it yourself needs Unity in batch mode, and only with their OK, with the output inside `store-assets/work/build/`.

## 4. Choose the hero moments

```bash
python3 ~/.claude/skills/game-store-kit/scripts/pick.py "$PROJECT"/store-assets/work/raw --top 16 --out "$PROJECT"/store-assets/work
```
Read `store-assets/work/contact-sheet.png` (and the full-size candidates you like). The picker favours variety (different scenes or colors), but always check: if one world dominates, build a strip of frames sampled across the whole capture and choose by eye. Choose **5–8 frames** that tell the story in order:
1. The hook — the most spectacular, readable gameplay moment (this is screenshot #1; it decides the install).
2. The core loop clearly visible.
3. Variety — a different level/world/biome/enemy.
4. Progression — upgrades, characters, collection, map.
5. Peak intensity — boss, combo, chaos.
6. (optional) Reward/social/modes.
Reject: transitions, half-loaded scenes, pause/debug/ad overlays, game-over screens, near-duplicates, tiny unreadable HUD-only frames. If no frame is good enough for a slot, go back and play more for it.

## 5. Icon (be creative — use the `logo-generator` skill)

Invoke the **logo-generator** skill for its exploration method (6+ genuinely different concepts, a showcase page, design rationale) but apply these **game-icon rules**, which override its minimal corporate-logo defaults:
- Subject comes from the game: the hero character's face/silhouette, the signature object or power-up, or the core mechanic as a symbol. Never generic clip-art. **If the game has a mascot, compose the icon from its real rendered sprite** (embed the PNG as a data URI `<image>` in the SVG). Use logo-generator-style vector symbols only for games without a character.
- Background must **contrast with the subject** (green dino → warm orange/yellow sunburst, not green on green). Keep the subject's whole head inside the frame, and keep tiny extras (meteors, sparkles) out of the corners: masks cut them off.
- One focal element, big: fills ~70–80% of the square; bold silhouette that reads at 48px; 2–4 colors from `brand.json`; rich lighting (gradients, rim light, soft inner shadow, glow) is welcome — game icons are richer than corporate logos.
- **No text** (at most a single letter if the brand is a letter). No thin strokes.
- Full-bleed square, **no rounded corners, no transparency** (stores mask it). viewBox `0 0 1024 1024`.
- Make 3+ concepts, render each at 1024 and 48px, look at them side by side, pick the strongest yourself (state why), and keep the others in `store-assets/icon/concepts/` so the user can switch later.
- If the user has a Gemini key and wants a painterly/3D icon, the **nanobanana** skill can render one using the chosen SVG + a real game frame as reference; still export the final as the files below.

Write the final as:
- `store-assets/icon/icon.svg` — full icon (background + subject).
- `store-assets/icon/bg.svg` — background only (viewBox 0 0 108 108 or 1024, full-bleed).
- `store-assets/icon/fg.svg` — subject only on transparent, **kept inside the centre 66/108 (61%) circle** for adaptive-icon safe zone; also used as the Android 12 splash icon.
- `store-assets/icon/mono.svg` (optional) — single-color silhouette for Android 13 themed icons.

## 6. Plan the kit → `store-assets/plan.json`

```json
{
  "screenshots": [
    { "image": "work/raw/frame-0031.png", "headline": "Outrun the *T-Rex*", "chips": ["Tap to jump", "Swipe to duck"],
      "focus": { "x": 0.28, "y": 0.62 }, "at": { "x": 0.48, "y": 0.8 }, "zoom": 1.32,
      "bridge": { "src": "brand/items/egg-blue.png", "y": 58, "size": 12 } },
    { "image": "work/raw/frame-0004-nest.png", "headline": "Hatch *6* dinos & 12 hats", "startAt": 0.21, "cropTop": 0.44, "zoom": 1.12, "floaterCount": 0 },
    { "image": "work/raw/frame-0054.png", "headline": "Dodge the *Lava Worm*", "chips": [{ "icon": "brand/items/egg.png", "text": "Volcano Valley" }] },
    { "image": "work/raw/frame-0124.png", "headline": "Grab *power-ups*",
      "chips": [{ "icon": "brand/items/pu-shield.png", "text": "Shield" }, { "icon": "brand/items/pu-magnet.png", "text": "Magnet" }],
      "callout": { "fx": 0.25, "fy": 0.465, "zoom": 3.2, "x": 76, "y": 62, "size": 34, "label": "Shield!" } }
  ],
  "feature": { "template": "work/splash-art.html" },
  "splash": { "template": "work/splash-art.html" }
}
```
Paths are relative to `store-assets/`.

**Tablets:** set `"tablet": true` to also render 7" (1440×2560) and 10" (2160×3840) sets, landscape swapped, all within Play's 1080–7680 px range. Google features a game on tablets only with **at least 4** tablet screenshots, so plan 4–8 shots. By default the phone frames are reused. If the game's layout changes on tablets (wider HUD, more of the level visible), capture on a tablet emulator (Android Studio > Device Manager > a Pixel Tablet AVD, then `droid.mjs boot --avd <name>`) and set `"tabletImage": "work/raw/..."` per shot.

**Make every screenshot feel full and premium, never empty** (each one combines these):
- **Headline** (2–5 words) and optionally **chips**: 1–3 glass pills with a real item icon ("Volcano Valley", "3 giant bosses", "Shield · Magnet · Rocket"). Use them on about half the shots.
- **Full-bleed gameplay (default)**: the frame fills the whole canvas, zoomed (`zoom`, ~1.3 in portrait) so the characters are big. `focus` = the point of the action in the frame (0–1), `at` = where it lands on the canvas (0–1). The HUD is pushed off the top (`hudCrop`, default 0.13 of the frame) and the headline sits on calm sky over a soft gradient. Aim for action in the lower 2/3, little empty ground, nothing important under the caption.
- **Menu or UI screens** (collection, map, upgrades): set `startAt` (≈0.21, the image starts below the caption with a soft fade) + `cropTop` (start at a clean section such as a card header, never half a button) + `zoom` ≈1.1 centred, `floaterCount: 0`. Check that nothing is cut at the sides and there's no empty strip at the bottom.
- (`device: "phone"` only) the phone with the real frame, alternating straight and tilted, rising off the bottom edge.
- **Floating real items** from `brand.items`. In full-bleed they stay in the corners (one far item at the top, at most one blurred foreground item at the bottom) and **never cover the action**. In phone mode they surround the phone at three depths. Override per shot with `floaters: [...]` / `floaterCount`.
- **`callout`**: a zoom bubble on a small but exciting detail (a power-up, a combo counter, a rare item). `fx`/`fy` = focus point in the frame (0–1), `zoom` = how many bubble-widths the frame spans, `x`/`y` = bubble centre (% of canvas), `size` = % of the short side, `label` = short pill text. Use it on 1–2 shots.
- **`bridge`**: an item straddling the right edge (enemy, meteor, egg). It continues on the next screenshot, so the set reads as one panorama in the store carousel. Use it on every other shot.
- **`decor`**: a hero character popping out over the phone edge (0–1 per shot, at most 2 per set).
- Bokeh, sunburst and grain come from `brand.style`.

Caption craft:
- Verb-first, benefit or emotion, not features ("Outsmart 100 bosses", not "Boss levels included"). Highlight ONE word with `*word*`. Same voice across the set. Screenshot #1 headline = the game's core promise.
- Hyphenated words ("T-Rex") never break across lines.

**Splash and feature graphic = designed key art, never "logo on a gameplay frame".** Write `store-assets/work/splash-art.html`. It loads `kit/_base.css`, `kit/_base.js` and `kit/scene.js` (build copies them next to it) and composes a scene with `SCENE`:
`sky(stops)`, `glow(x,y,r,color)`, `rays(x,y,{count,opacity})`, `ridge({y,amp,color,kind:'hills'|'mountains'|'volcano'|'dunes',trees:'palm'|'pine'|'round',blur,highlight,glowColor})`, `comet(x1,y1,x2,y2,{head,width})`, `sprite(src,x,y,size,{rot,flip,glowColor,filter,blur})`, `speed(x,y,{angle,len})`, `particles('embers'|'sparkles'|'snow'|'leaves'|'fireflies',n,{area})`, `vignette()`, `grain()`.
Design process:
1. **Concept first.** Write one line: the game's dramatic promise as a single frozen moment (DinoDash: "Meteor incoming: Rexy leaps clear while the Giant T-Rex charges out of the jungle at dusk"). Think key art or a movie poster, not a menu screen.
2. **Story.** The hero mid-action (jump, swing, drift) + the threat or goal (boss, meteor, finish line) + a hint of reward (coins, gems).
3. **Depth.** At least 3 parallax layers (far range, mid silhouettes, near ground), lighter and hazier far, darker near. Atmospheric light from one dramatic source (meteor, sun, portal, lava). Darken secondary characters (`filter: 'brightness(.72)'`) so the hero pops.
4. **Palette** from the game's worlds, pushed toward dusk/neon drama, still reading as the same game.
5. **Logo** large at the top with a soft glow, part of the scene and not a sticker.
6. **One page, all sizes.** Use `o(portrait, landscape, square, feature)` values so 1080×1920, 1920×1080, 2732² and the 1024×500 feature graphic each get their own composition. Keep key elements away from the outer ~8% (crops and masks).
7. Render, look at all four, fix overlaps, empty areas and tangents, and repeat until it looks like a poster.

## 6b. Store listing text → `store-assets/listing.json`

Write it from what you learned playing (real features, real names: worlds, bosses, characters, modes). Never invent features.
```json
{ "language": "en-US",
  "title": "Dino Dash: Jurassic Run",
  "short": "Outrun the T-Rex, dodge meteors and hatch dinos across 6 prehistoric eras.",
  "full": "A meteor is coming and only the fastest dinosaur survives. Tap to jump, swipe to duck...\n\nRUN THROUGH 6 ERAS\n...",
  "releaseNotes": "New: the Meteor Storm era and the Mega Pterodactyl boss.",
  "category": "Arcade", "tags": ["Runner", "Dinosaur", "Casual"] }
```
- **title** ≤30: the game's name, optionally with a short descriptive subtitle. No "best", "#1", "free", "new", emojis or ALL CAPS: these are errors.
- **short** ≤80: one sentence promising the core fun (verb-first, concrete).
- **full** ≤4000: the first 167 characters (shown before "more") are a complete hook sentence. Then 4–6 short sections with UPPERCASE headings (worlds/levels, bosses, characters/collection, power-ups/progression, modes), 1–2 sentences each. No keyword stuffing, no testimonials, no ranking claims, no URLs.
- **releaseNotes** ≤500: only for updates, what actually changed.
- **category**: one Play game category (Action, Adventure, Arcade, Board, Card, Casual, Puzzle, Racing, Role Playing, Simulation, Sports, Strategy, Word...). **tags**: up to 5.
`build.mjs` runs `listing.mjs`, which checks Play's limits and metadata policy, also flags buzzwords inside screenshot/feature-graphic text, and writes `play-store/store-listing.md`, ready to paste into Play Console. Fix every ✗ error; review the ⚠ warnings.

## 7. Build everything

```bash
GSK_PROJECT="$PROJECT" node ~/.claude/skills/game-store-kit/scripts/build.mjs            # or --only icons,shots,feature,splash
```
Produces:
```
store-assets/
  play-store/icon-512.png  feature-graphic-1024x500.png  screenshots/phone-01..08.png (tablet-* if enabled)
  android/res/mipmap-*/ic_launcher{,_round,_foreground,_background,_monochrome}.png
  android/res/mipmap-anydpi-v26/ic_launcher.xml   android/res/drawable-nodpi/splash_icon.png
  splash/splash-1080x1920.png  splash-1920x1080.png  splash-2732x2732.png
  android-icon/foreground.png  background.png
  preview.html            (gallery + spec check)
```
It flattens alpha where stores forbid it and validates Play specs (icon 512² ≤1MB; feature 1024×500; 2–8 screenshots, aspect ≤2:1, ≤8MB).

## 8. Art-direct your own output (mandatory)

Read every rendered PNG. Fix and rebuild until all are true:
- [ ] Headlines fully visible, not overlapping the game frame or HUD, same size rhythm across the set.
- [ ] The set reads as one panorama: same background system, colors, type, corner radius, shadows.
- [ ] Screenshot #1 is the strongest image; no two consecutive shots feel the same.
- [ ] Game frames are sharp (no upscaled blur) and show real gameplay.
- [ ] Icon reads at 48px; matches splash and feature graphic colors.
- [ ] Feature graphic: title/logo readable at thumbnail size, nothing important in the outer 10% edges.
- [ ] Every screenshot feels full: headline + big gameplay + chips, callout or bridge on alternating shots. No HUD under the caption, no big empty ground or sky band, no item covering the action, no character cut at an edge.
- [ ] Menu shots start at a clean section (no half buttons or headers under the fade), centred, no empty strip at the bottom.
- [ ] Bridges line up across neighbouring screenshots (same y and size).
- [ ] Splash and feature graphic are composed key art (concept, story, depth, light), not a logo on a frame; they work at every size.
- [ ] Spec check in `preview.html` passes.

Tweak `brand.json` (colors/style) or `plan.json` (captions/frames/crops/layout), never hand-edit PNGs.

## 9. Check, show, then pack

1. Confirm nothing outside `store-assets/` changed (must print nothing unless the user approved a build):
```bash
find "$PROJECT" -newer "$PROJECT/store-assets/brand.json" -not -path "$PROJECT/store-assets/*" -not -path "*/node_modules/*" -type f | head
```
2. Publish-readiness report (read-only; pass the developer's APK/AAB when there is one):
```bash
node ~/.claude/skills/game-store-kit/scripts/readiness.mjs "$PROJECT" [--apk <app.apk|app.aab>] --out "$PROJECT"/store-assets/play-store/publish-checklist.md
```
It checks what Play enforces at upload (target API 36 since 2026-08-31, 64-bit native code, 16 KB alignment, version code) and what slows review (sensitive permissions, unused Capacitor plugins, debuggable builds, template app IDs, Unity Mono/ARMv7-only builds, missing release keystore). Tell the user about every ✗ and ⚠ in plain words and how to fix it. Never fix the project yourself.
3. Show the user the result (send the screenshots, feature graphic and icon, or open `preview.html`) and say which icon concept you chose and why. Make the changes they ask for now (later changes need `pack.mjs --restore` first).
4. Pack. The Play Store files, the Image Asset sources and the splash stay visible; the sources move into the hidden `.kit/` for the next run:
```bash
GSK_PROJECT="$PROJECT" node ~/.claude/skills/game-store-kit/scripts/pack.mjs
```
5. Tell the user where each file goes (the table above). Do **not** copy anything into the project, and don't run these commands yourself: the developer runs them when they choose.
   - **Icon (both engines)**: Android Studio > app > res > New > Image Asset: Foreground layer > Path = `android-icon/foreground.png`, Background layer > Path = `android-icon/background.png` (the subject already sits inside the safe zone, so keep the default resize).
   - **Splash, Capacitor**: on **Android 12+ (most devices)** Android shows its own system splash: the app icon (from Image Asset) centred on a background colour. That's what players see (tested on an API 36 emulator); Capacitor's `splash.png` only appears on Android 11 and older. So:
     - background colour: one line in the launch theme (`AppTheme.NoActionBarLaunch` in `res/values/styles.xml`): `<item name="windowSplashScreenBackground">#xxxxxx</item>` with the brand's `dark` or `primary` colour.
     - older devices (optional): put `splash/splash-2732x2732.png` in `res/drawable-nodpi/splash.png` and delete the old `splash.png` files in `drawable`, `drawable-port-*` and `drawable-land-*`. Use `drawable-nodpi`, never plain `drawable`, or Android scales the image up to 4× on high-density phones (tested: no crash with nodpi).
     - the key art can still be seen by everyone as the game's own loading/title screen, but only if the developer adds it to their game code. Mention it; don't do it.
     (If the user asked for `capacitorAssets`: `npx @capacitor/assets generate --android --assetPath store-assets/capacitor-assets`, then `find android/app/src/main/res -name "ic_launcher*.webp" -delete`, because the tool writes each launcher icon as both `.png` and `.webp` and Android rejects the duplicates.)
   - **Unity** (import the PNGs into `Assets/` first, e.g. `Assets/StoreKit/`):
     - Icon: Edit > Project Settings > Player > Android tab > Icon > **Adaptive**: Foreground = `android-icon/foreground.png`, Background = `android-icon/background.png`. **Round** and **Legacy**: `play-store/icon-512.png`. Unity resizes the textures for each slot.
     - Splash: Player > Splash Image. Set the splash images' Texture Type to **Sprite (2D and UI)**, then **Background** = `splash/splash-1920x1080.png` and **Alternate Portrait** = `splash/splash-1080x1920.png` (portrait games: the portrait one is what most players see). Unity shows this after Android's own system splash, so every player sees the key art. On Unity versions before Unity 6, the free plan also adds the "Made with Unity" logo.
