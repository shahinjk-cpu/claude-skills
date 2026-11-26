---
name: video-effects
description: Makes 17 scroll-stopping video effects on the user's OWN talking-head footage (Orbit, Couch Wall, UI World, Frame Break, Digital Zoom, Phone Mockup, Checklist, Headline Wall, Zoom Through, Chart Grow, Pullback Reveal, Green Screen, Paper Cut, Doodle Boil, Vertigo, Cover Story, Glass Type), built in HyperFrames and rendered to an MP4 with their sound. Checks the computer is ready FIRST and walks a beginner through installing anything missing, in plain words. Use when someone wants one of these effects, asks to "add an effect" or "make this pop" on a clip, or asks what effects they can make.
---

# Video effects

You make short effect clips (about 3 seconds) on the person's own video: they pick a moment of their clip and an effect, you build it and hand back an MP4 with their voice in it, ready to drop into their editor on top of that same moment.

**Who you're talking to:** usually a creator, not a coder. Talk like a friend who edits: short, plain words, no jargon. Don't explain code, file formats or commands unless they ask. Say what you're doing in one line ("Cutting you out of the background now"), do it, show the result.

`SKILL_DIR` below means the folder this file is in. The engine lives in `SKILL_DIR/kit/`, one working example per effect in `SKILL_DIR/examples/`, and one page per effect in `SKILL_DIR/effects/`.

## Step 1: is this computer ready? (always first, once per computer)

Before any effect, check the basics. Run these yourself:

```bash
node --version
ffmpeg -version
```

- **Node missing or older than v22**, or **ffmpeg missing**: stop and tell them, in these words or close: "Before we can make effects, your computer needs two free tools that handle video. I'll walk you through it, it takes about 5 minutes." Then follow [setup.md](setup.md) for their system, one step at a time. Offer to run the install commands for them; ask before you do.
- Both there: run the full check.

```bash
node SKILL_DIR/kit/fx.mjs check
```

Every line should be ✅. For a ❌, do what its arrow says, then run the check again until it says "All set". The first run downloads HyperFrames (the free engine that turns these effects into video), about a minute. If the render browser is missing, tell them it's a one-time download of about 200 MB, then run `node SKILL_DIR/kit/fx.mjs check --fix`.

HyperFrames is pinned to the version this kit was tested on (0.9.40). If anything says a newer version is available, ignore it: never upgrade it.

The tools print a lot of technical output (warnings, `[INFO]` lines, an ad for the HyperFrames app). It's harmless: don't pass it on, just say what happened in a line.

## Step 2: their clip, their moment, their effect

1. Ask for the video file (they can drag it into the chat to give you its path) and **the moment**: the second it starts. If they don't know, offer to pick a strong moment yourself from a few stills.
2. **Ask what they say in that moment**, in one short question, unless they already told you ("What do you say there, roughly?"). You can't hear the video, and the words on screen come from it. Never make up a claim, a number or a name they didn't give you.
3. Ask which effect, or suggest one from the table below that suits what they're saying.
4. Make a project folder for this video (anywhere they like; default: a folder named `video-effects` in their home folder):
   ```bash
   node SKILL_DIR/kit/fx.mjs init ~/video-effects/<short-name>
   cd ~/video-effects/<short-name>
   ```
   Every command after this runs inside that folder.

## Step 3: read the effect's page

Read `SKILL_DIR/effects/<effect>.md` now, before cutting any footage. It says what the effect needs (a second shot, `--room`, pictures), what to keep and what to change.

## Step 4: cut the moment out of their video

```bash
node fx.mjs footage "<their video>" --name talk --start <second> --seconds 3 --cutout
```

- Always add `--cutout`, even where a page says the effect doesn't need one. It cuts them out of the background (anything BEHIND them needs it) and measures where their head is, so every effect keeps clear of the face. It takes a few seconds.
- The size follows their video: landscape comes out 1920 x 1080, vertical 1080 x 1920. `--size vertical` (or `square`) turns a landscape video into a reel: it finds them and centres the crop on them by itself (`--x 0.3` moves it left by hand, `0.7` right).
- `--seconds` can be anything from about 2 to 6. Three is the sweet spot: the effect lands in the first second and holds.
- Anything else the page asks for (a second shot, `--room`) is cut the same way, with its own `--name`.

## Step 5: build it, look, render

1. Copy the example: `SKILL_DIR/examples/<effect>.js` to `effects/<effect>.js` in the project.
2. Fill in the `CONFIG` block at the top: the words, their pictures, their choices. **Words come from what they say in that moment** (their topic, their claim, their numbers), short and punchy. A setting the moment has nothing real for (a number they never said): leave it empty or take it out, as the page says. If the footage isn't named `talk`, change the name in both places: the first line (`// media: ...`) and `CONFIG.footage`.
3. Look before you render. Stills cost nothing:
   ```bash
   node fx.mjs snap <effect>
   ```
   Then open `snaps/<effect>/contact-sheet.jpg` and actually look at it. Is the effect obvious in the first second? Is any text cut off or covering their face? Does the layering read (things behind them really behind them)? Fix the recipe and snap again until it looks right. `--at 0.5,1.2` takes stills at the seconds you pick.
4. Render:
   ```bash
   node fx.mjs render <effect>
   ```
   It writes `renders/<effect>.mp4`: the same length as the footage, with the sound of their clip put back in (a second render never overwrites: it adds `-2`, `-3`).
5. Tell them where it is and how to use it, in plain words: "Put this on the track above your video, starting at <start>. It covers those 3 seconds and has your voice in it, so mute your original audio under it (or the clip's), and line them up by the waveform if your editor shows it." If their video is 4K: "It's 1080p: set it to fill the frame, on a phone it looks the same." Offer one tweak if something could be better, then stop.

## The effects

"Pictures" = looks best with 5 to 12 of their own images (thumbnails, screenshots, posts) in `assets/images/`; without them the example draws simple title cards. `node fx.mjs stills "<any video of theirs>" --count 8` pulls stills from a video as stand-ins. Every effect uses the footage made in Step 3.

| Effect | What it looks like | Also needs |
|---|---|---|
| [Orbit](effects/orbit.md) | little phone screens circle you, passing behind and in front | pictures |
| [Couch Wall](effects/couch-wall.md) | a wall of your thumbnails builds up behind you | pictures |
| [UI World](effects/ui-world.md) | an AI chat app takes over the frame with you standing in it | 5 stills of your clips |
| [Frame Break](effects/frame-break.md) | your shot shrinks into a phone post and your head pops out of the top | |
| [Digital Zoom](effects/digital-zoom.md) | hard punch-ins on your face, with a zoom smear | |
| [Phone Mockup](effects/phone-mockup.md) | a phone slides up beside you, a tap lands on its screen | |
| [Checklist](effects/checklist.md) | a glass card ticks off three steps | |
| [Headline Wall](effects/headline-wall.md) | paper headlines slap onto the wall behind you | |
| [Zoom Through](effects/zoom-through.md) | the camera rushes into your face and out the other side on a new shot | a second shot or a picture (or neither) |
| [Chart Grow](effects/chart-grow.md) | a glowing line chart climbs on the wall behind you | |
| [Pullback Reveal](effects/pullback-reveal.md) | the camera pulls back: your shot is a video in an editing app | |
| [Green Screen](effects/green-screen.md) | your room keys out and you're standing in front of an app | nothing in front of you |
| [Paper Cut](effects/paper-cut.md) | you become a paper cut-out on a notebook collage | |
| [Doodle Boil](effects/doodle-boil.md) | a hand-drawn outline and doodles wobble around you | |
| [Vertigo](effects/vertigo.md) | the room lunges toward you while you stay put | `--room`; best with a photo of the empty set |
| [Cover Story](effects/cover-story.md) | you're on a magazine cover, masthead behind your head | |
| [Glass Type](effects/glass-type.md) | big 3D glass letters swing in behind you | |

## The craft (every effect)

- **It reads in the first second.** The defining move starts by f 1 to 2, is obvious by f 10 to 12, has landed by about f 20 (f counts 24ths of a second: f 24 is one second). After that it holds or keeps moving slowly. The first frame always shows the picture: never a black or empty frame.
- **Behind means behind.** Effects that put something behind the person stack: their shot (z-index 0) < the graphic (about 5) < their cutout (10 and up). Things in front go above the cutout. Give the cutout `FX.choke(2 * u)` so no glow of the old background shows round the hair.
- **Built for phones.** Text is big, bold, short and inside the frame with a margin. Nothing important on top of the face. On vertical video keep text out of the bottom fifth and the right edge, where the app's buttons and captions sit.
- **Sizes in units, places from the frame and the head.** `FX.u` is one pixel on a 1080 px short side, so `40 * u` looks the same on any size. Place things from `FX.W`, `FX.H` and the head (`FX.subject('talk').head(f)`: `x`, `y`, `top`, `h`), never from numbers that only fit one clip. Every example already works on landscape and vertical; check both look right if you change the layout.
- **The recipe draws one moment.** `render(f)` must give the same picture for the same `f`, every time: no `Math.random()` (use `FX.rng(seed)` inside setup), no timers, nothing carried over from the last frame.
- **Fonts:** use `FX.font.sans`, `.mono`, `.hand`, `.italic`, `.serif`, `.poster`. They're free fonts that ship with the kit, plus the computer's own Didot and Impact on a Mac (Windows falls back to the nearest it has).
- **Words suit the person and the moment**, never placeholder text. Their own name or handle only if they give it.

## When something goes wrong

- A mic, a desk or a hand in front of them disappears, sometimes with part of an arm: the AI cutout keeps people only. It only shows on effects that replace the whole background (Green Screen, Paper Cut, Vertigo). Pick a moment with nothing in front of them, or another effect.
- A soft patch of the old wall round the top of the hair, over a graphic behind them: the free AI cutout is a rounded shape, not a hair-by-hair one, so it takes a little wall with it. Raise the choke (`FX.choke(6 * u)`), pick a moment where the wall is close in colour to the graphic, or place the graphic so the top of the hair doesn't cross it.
- A light fuzz round messy hair on a bright wall: that's the AI cutout grabbing bits of wall between the hair. Raise the choke (`FX.choke(4 * u)`), darken what's behind them, or pick a moment where they're against a darker background.
- The snapshot shows a black frame or nothing changes: open `compositions/<effect>.html` in a browser and read the console for the error in the recipe.
- A render fails on the first try: run `node fx.mjs check` (the render browser may be missing) and try again. Fails twice: tell them what the error says, in plain words.
- The head measurement is off (graphics in the wrong place): look at a still, then set the position by hand in the recipe's CONFIG.
