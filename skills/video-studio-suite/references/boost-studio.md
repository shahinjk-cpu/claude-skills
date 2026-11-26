---
name: studio-brief
description: Start a reel or video brief for a brand. Asks and clarifies first (one round of questions), splits the reel into separate choices (style, color, layout, text, animation, speed, sound), shows small sample scenes in the brand for each choice, locks the owner's picks, then builds with approval gates. Use for "/studio-brief <idea>", "make a reel", "make a video about X", "new content for this brand", or any video request that arrives before a script exists.
---

# studio-brief

The text after `/studio-brief` is the idea. If there is none, ask for it, or offer 3 ideas from the brand's `voice.md` and recent posts.

Goal: the owner chooses by looking, not by describing. Nothing is produced until the brief is locked, and nothing is posted without a yes (see `studio-publish` and `/post`).

Read first (from the repo root): `brands/<brand>/brand.json`, `brands/<brand>/voice.md`, and `brands/<brand>/MOTION.md` if it exists (choices saved from earlier reels). Never invent anything marked TODO in a brand file. Every Kurdish line you write is "draft, needs native review".

## Steps (each ends with the owner's go-ahead)


0. **Research (optional, before the intake).** For a new idea or a new niche run `studio-research` (trend scan; any paid lookup only after the owner says yes).md`; the mechanics found feed the hooks in step 2. Say the credit cost first.
1. **Intake, one round only.** Pick questions from `references/question-bank.md`. Skip every question the request or `MOTION.md` already answers. Ask at most 4 in one message, each with a recommended answer so the owner can reply "ok". If a fact is missing (price, proof, offer, date) write `{{proof needed}}`; do not invent it. Do not start production while an answer is missing.
2. **Concept.** Use `studio-script`: three hooks from different formulas, one recommended. The owner picks one. Then plan the story with `studio-retention` (loop, beat map, last-shot CTA) and save it in the brief as "Retention plan". **Gate G1**: have the `retention-checker` agent judge the tagged script (independent of whoever wrote it; it runs the gate and returns PASS / REVISE / FAIL / STOP with fixes; pass it the idea id so the step is logged); do not go to the style board until it passes (a fail goes back to `studio-script`, 2 rounds, then ask the owner).
3. **Style board.** The **Style** choice starts from the brand's lemo style (`brands/<brand>/lemo.json`); show the other 2 samples only as `alt_styles`. If `MOTION.md` has a **Latest board pick**, use it as the recommendation (pass it in `--recommend`) and say "using your last style board pick"; the owner may still change any choice. Split the reel into the 7 choices in `references/dimensions.md`: style, color, layout, text, animation, speed, sound. For each choice show 3 small samples (A, B, C) of the SAME scene in this brand, changing only that one thing, and say which you recommend in one line. Stills first; 2-second loops only for animation and speed; short clips for sound. The owner answers like "color B, animation A, speed B, sound C" or "all your picks". Do not skip this step.
   - **Make the board with the tool** (about 15 seconds, free):
     `node tools/styleboard/make.mjs --brand <brand> --out projects/<name>/styleboard --hook "<chosen hook>" --recommend style=X,color=X,layout=X,text=X,animation=X,speed=X,sound=X --open`
     Use the chosen hook (and a short sub line and CTA if known) as the sample copy; set `--recommend` from your own judgment of the brand and goal (the brand's defaults are in `brands/<brand>/styleboard.json`). If the brand has no `styleboard.json`, copy `brands/_example/styleboard.json` and edit the palette, fonts and wordmark first.
   - Tell the owner where `board.html` is. It must be opened in a normal browser (double-click it, or `--open` does it); an app preview may show no media. The owner picks one option per choice and presses **Copy my picks**, then pastes the line, for example "Style C, Color A, Layout B, Text A, Animation B, Speed B, Sound B". `board.json` lists the options and your recommendation.
   - Use `--only color,animation` to re-show a single choice after a change of mind.
   - Sound C (a voiceover) has no clip because it uses ElevenLabs credits; say the price before generating one. Samples use sample text, not the final reel.
   - If the tool fails (Chrome or ffmpeg missing, no `styleboard.json`), say what is missing and fall back to one hand-made still per option in the brand colors; do not skip the step.
4. **Preview the picks together, then lock.** The owner pastes a picks line (for example "Style B, Color C, Layout B, Text A, Animation C, Speed C, Sound B"). Render one combined preview into the same folder: `node tools/styleboard/make.mjs --brand <brand> --out <same styleboard folder> --picks "<the line>"` (about 5 seconds). It writes `combo.png`, `combo.mp4` (with the chosen sound) and `picks.json`, and leaves the board alone. Show the owner `combo.png` and say what each pick means in one line each. If it looks wrong, change one choice and re-run. Open the board by double-clicking `board.html`. Then lock: save the picks to `projects/<name>/brief.md` (`references/brief-template.md`) and merge reusable ones into `brands/<brand>/MOTION.md`. Read the brief back in 5 lines and get a yes.
5. **Build with gates.** Write `projects/<name>/plan.json` (shots, cuts, events, text, sound) and pass **Gate G2** before the first still; after building pass **G3** (plan rewritten from the real timeline) before the full render. A gate that does not pass sends you back to the step it names. One still first (owner approves the look), then a short preview, then the full render (`studio-video`). Anything that costs money (ElevenLabs credits, paid music, generated images) states the price first and waits. Keep older versions (v2, v3).
6. **Review.** First **Gate G4** on the render: the `retention-checker` agent (`render` stage); not a pass = back to `studio-video`. Then hand the file to the `reel-reviewer` agent (it runs `studio-review` as a stranger: checker, retention gate, earshot, frame sheet); the manual run of `studio-review` (the checker covers size, duration, black frames, freezes, loudness and clipping, and makes a safe-area frame sheet; you then look at the sheet for clipped text and Kurdish right-to-left shaping). Fix and re-run, at most twice. Show the owner only a pass.
7. **Hand off.** Save the file to `outbox/<brand>/` for `/post`. Do not schedule or post without the owner's yes on the exact copy, media and time.
8. **Remember what the owner is happy with.** After a finished reel, or after a batch of several, ask once: "Happy with these? Should I remember the choices?" Only on a yes:
   - For each of the 7 choices, count how many approved reels used each option and record it in `MOTION.md` under **Confirmed** (e.g. `animation: spring pop x3, slide x1`).
   - Promote an option to **Preferred** when the owner approved it in 2 or more reels, or says "always use this". Promote nothing from a single reel unless asked.
   - Move an option to **Avoid** only when the owner rejects it or says to stop using it. A rejected sample is not a ban on that style for other brands.
   - Show the change as 3-5 lines ("Preferred animation: spring pop (was: none)") and get a yes before writing. Never rewrite `MOTION.md` silently, and keep the Log of dated changes.
   - Next brief, say "using your preferred X, Y, Z" and skip those choices unless the owner wants to change them.
9. **Learn from results.** When analytics exist, add one line to the `MOTION.md` Log: what performed, what to drop. Numbers only from real analytics, never guessed.

## Updating the brief later
`/studio-brief update <brand>`: show the current `MOTION.md` (Preferred, Confirmed, Avoid, Log), ask what the owner wants to change, apply it, and show the result. Also use this when the owner says "change my default style to ...", "forget that choice", or "start fresh" (back up the old file as `MOTION.old.md` first, then reset on a yes).

## Rules
- Ask, don't assume: one round of questions, then work. If the owner says "you decide", use your recommendations and say so.
- One variable per sample so the owner can see what changed.
- Reuse before asking: if `MOTION.md` has an answer, say "using X from last time" and move on.
- lemo-opuscar (MIT) is the primary engine (owner decision 2026-11-04) and each brand has its own lemo style in `brands/<brand>/lemo.json` with the brand colours mapped onto it. Use it as the starting **Style** (say "using the Boost risograph style"); the owner may swap to one of its `alt_styles`. Other tools (Remotion, HyperFrames, motion-prompt, motionvideo) are options for special cases; check the license, credit authors, and ask before the first run of any installer.
- Forbidden words, claims and tone come from `brand.json` (`forbidden`, `claims_allowed`).
