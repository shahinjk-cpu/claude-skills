# game-store-kit

A [Claude Code](https://claude.com/claude-code) skill that **plays your game** and turns the best moments into a premium, consistent Google Play kit. You get only what you need to publish:

```
store-assets/
  play-store/
    icon-512.png                   -> Play Console: App icon
    feature-graphic-1024x500.png   -> Play Console: Feature graphic
    screenshots/phone-01..08.png   -> Play Console: Phone screenshots
    screenshots-7inch/ screenshots-10inch/ -> Play Console: Tablet screenshots (optional)
    store-listing.md               -> Play Console: app name, short + full description, release notes (checked against Play's limits and policy)
    publish-checklist.md           -> what Play checks at upload: target API 36, 64-bit + 16 KB native code, version code, permissions, unused plugins
  android-icon/
    foreground.png  background.png -> Android Studio: res > New > Image Asset (or Unity Player Settings > Icon)
  splash/
    splash-1080x1920 / 1920x1080 / 2732x2732 -> designed key-art splash
```
The same output for Capacitor and Unity. Nothing is copied into your project; you apply the icon and splash the way you normally do.

> **Splash on Android 12+:** Android shows its own system splash (your app icon on a background colour) before the game. In Unity the key-art splash then appears as Unity's splash image. In Capacitor, `splash.png` only shows on Android 11 and older, so set the system splash background colour in your launch theme and, if you like, use the key art as your game's own loading screen. (Capacitor users who prefer the `@capacitor/assets` CLI can ask for its source folder too.)

- **Screenshots** are full-bleed real gameplay (the style Google recommends): zoomed so the action is big, HUD hidden, outlined headlines on the sky, glass feature chips, zoom callouts on key details, and the game's own items bridging from one screenshot into the next. A modern phone-mockup style is available as an option.
- **Splash and feature graphic** are designed key art: a story moment with the hero, the threat, layered landscapes and dramatic light, built from the game's real characters. Not a logo pasted on a gameplay frame.
- Everything shares one look (palette, fonts, outlines, light) taken from your game's own logo and characters.

## Scope
**Capacitor** games (web games wrapped with Capacitor) and **Unity** games, **Android**, **Google Play** only. Narrow on purpose, so every step is tested and works.

## How it works
1. **Understands the game**: detects Capacitor or Unity, orientation, controls, bosses, worlds and progression.
2. **Plays it for real**: headless Chrome for Capacitor web builds; the Android emulator for Unity APKs, where Claude plays by looking at the screen and tapping, or with a scripted plan. Claude writes a play script for your specific game, and uses the game's own demo AI or debug hooks when it has them.
3. **Picks hero moments**: scores the frames, drops duplicates and favours variety across worlds and modes.
4. **Takes real art from the game**: grabs your in-game logo and renders your characters at high resolution, then designs the icon around your mascot.
5. **Renders and checks everything** with HTML templates, reviews its own output and fixes problems.
6. **Packs**: keeps only the Play Store files, the Image Asset sources and the splash, plus a hidden `.kit/` with the sources, so the next run (e.g. for an update) has exactly the same look.

**It never modifies your project.** Everything goes into `<project>/store-assets/`, which you can move anywhere afterwards.

## Install
```bash
git clone https://github.com/mbelouar/game-store-kit ~/.claude/skills/game-store-kit
cd ~/.claude/skills/game-store-kit/scripts && npm i
```
Requirements: Google Chrome, Node 18+, Python 3 with Pillow (`pip3 install pillow`). For Android capture you also need the Android SDK (`adb`, `emulator`) with at least one AVD.

Optional: the [logo-generator](https://github.com/op7418/logo-generator-skill) skill, for broader icon exploration on games without a mascot.

## Use
Open Claude Code in your game's folder and run:
```
/game-store-kit
```
Ask for changes (captions, frames, icon concept) before it packs. To keep the sources for later rebuilds, ask it to pack with `--full`.

## Scripts
| Script | What it does |
|---|---|
| `detect.mjs` | Engine, name, orientation, package id, web build, art |
| `capture-web.mjs` | Plays a web build in headless Chrome with a per-game `play.mjs`, capturing frames |
| `droid.mjs` | Plays an APK (Unity) on the Android emulator: boot, install, launch (waits for the game to settle), screenshots with a % grid for vision-driven play, tap/swipe/hold in % or px, scripted plans with background capture, clean status bar, system bars cropped |
| `pick.py` | Scores frames, removes duplicates, picks for variety, makes a contact sheet |
| `palette.py` | Dominant and vivid colors from game art |
| `grab.mjs` | Captures a DOM element (such as the in-game logo) as a transparent PNG |
| `render.mjs` / `build.mjs` | Renders every asset at exact store sizes from `brand.json` and `plan.json` |
| `finalize.py` | Flattens transparency where stores require it, checks specs, writes `preview.html` |
| `listing.mjs` | Checks the store listing text and screenshot captions against Play's limits and metadata policy; writes the paste-ready `store-listing.md` |
| `readiness.mjs` | Read-only publish-readiness report for Capacitor and Unity projects (and a built APK/AAB): target SDK, version code, app ID, permissions, unused plugins, debuggable, IL2CPP/ARM64, keystore, 64-bit and 16 KB native code |
| `pack.mjs` | Keeps only the Play Store files, Image Asset sources and splash + hidden `.kit/` sources; `--restore` brings them back for the next run |
| `templates/scene.js` | Key-art toolkit: sky, glow, rays, procedural ridges/volcanoes/trees, comets, particles, speed lines |

## License
MIT
