---
name: video-editing
description: Edit and produce videos with an editable Blender VSE timeline plus a local AI/ffmpeg toolkit (VSEKit) — YouTube long-form, Shorts/TikTok/Reels, devlogs, trailers, montages, talking-head cuts. Use this skill whenever the user wants to cut, assemble, caption, subtitle, transcribe, voice-over, denoise, upscale, beat-sync, render or loudness-normalise a video; analyse or download a YouTube video (yt-dlp) to study its editing; record game footage (Unity Recorder); make thumbnails, chapters or SRT files; or work in Blender's Video Sequencer — even if they just say "смонтируй", "ролик", "видос", "шортс", "субтитры", "озвучка", "сделай нарезку", or drop a video file and ask what to do with it.
---

# Video editing with VSEKit + Blender VSE

The user wants to **see and tweak a real timeline**, not receive an opaque mp4. So every edit is produced
as a Python-built `.blend` (named channels, strips, keyframes, compositor node groups) that renders to the
final file. The user can open it, nudge things by hand, and you can read their changes back through the
Blender MCP. Generated-only pipelines (pure ffmpeg) are the fallback for throwaway A/B clips.

## Where VSEKit is

This skill lives inside the VSEKit repo at `<VSEKIT>/skill/video-editing` and is linked (junction) into
`~/.claude/skills/video-editing`. Resolve `<VSEKIT>` as: the `VSEKIT_ROOT` env var → else two folders up
from this skill's real path → else `~/Documents/VSEKit`. Below, every path is relative to `<VSEKIT>`.
`<VSEKIT>/README.md` describes layout and setup; `vsekit/env.py` discovers every tool (never hard-code).

## Step 0 — check the environment (new machine, new session after updates, or anything fails)

Run `.venv\Scripts\python.exe tools\doctor.py` (any Python works if `.venv` doesn't exist yet). It prints
OK/MISSING/WARN per component and exits 1 when something required is missing.
- **VSEKit folder missing** → it isn't on this machine: clone https://github.com/o-otruta/VSEKit (ask the user first) and run setup.ps1 — don't
  rebuild the toolkit from memory.
- **Required component missing** → offer to run `powershell -ExecutionPolicy Bypass -File setup.ps1`
  (installs winget tools, both venvs, Real-ESRGAN, Blender modules, the skill link; idempotent). It
  downloads several GB, so ask first. `-SkipML` gives a light install (no torch/whisper/kokoro/DeepFilterNet).
- **Optional component missing (WARN)** → carry on, pick the fallback (e.g. no NVENC → libx264,
  no DeepFilterNet → ffmpeg voice chain) and tell the user what quality they lose.
- Blender MCP and Unity MCP are installed manually (not by setup); doctor only reports the Blender one.

## Interpreters — use the right one

| What | Interpreter |
|---|---|
| Everything **inside Blender** (`vsekit.vse`, `fx`, `three_d`, `preview.py`, build scripts) | `python -m vsekit.env blender` gives the exe → `blender -b --factory-startup --python build.py`; or MCP `execute_blender_code` |
| Whisper, librosa, PySceneDetect, Kokoro, OTIO, yt-dlp, Pillow, edge-tts, analysis, prepare scripts | `.venv\Scripts\python.exe` (Python 3.12) |
| DeepFilterNet only (old numpy/torch) | `.venv-df` — always through `vsekit.denoise.deepfilter()` |
| Real-ESRGAN | `tools\realesrgan\…exe` via `vsekit.upscale` |
| ffmpeg/ffprobe, deno (yt-dlp's JS runtime) | `vsekit.env.FFMPEG` / `FFPROBE`; `env.tool_env()` puts ffmpeg + deno on PATH |

Scripts outside the repo need `sys.path.insert(0, <VSEKIT>)` (or `PYTHONPATH=<VSEKIT>`) to import `vsekit`.
Set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to silence Hugging Face noise.

## Workflow

1. **Pin down the deliverable** before touching media: platform + aspect (16:9 1920×1080 / 9:16 1080×1920),
   target length, language of on-screen text, voice (user's own recording, TTS, none), music source and its
   licence. If the user gave a detailed brief, follow it but flag contradictions (e.g. "15–18 s" vs content
   that sums to 19 s) instead of silently violating one side. Platform specs: `references/platforms.md`.
2. **Gather media**: user files; `vsekit.download` (yt-dlp) for references and licensed material; Unity
   Recorder for game footage (`references/unity_capture.md`); `media.probe()` everything (fps, size, audio).
3. **Analyse** (cached next to the media as `*.whisper.json`, `*.beats.json`, `*.scenes_*.json`):
   `transcribe.transcribe()` → words with timings; `beats.analyze()` → tempo/beats/downbeats/energy;
   `scenes.detect()` → shot list. Look at frames yourself: `media.contact_sheet()` / `media.frame_at()` and
   Read the PNG — never place overlays or pick freeze frames blind.
4. **Prepare assets** (`prepare.py`, outside Blender): Pillow graphics (`gfx`: captions with active-word
   highlight, pills, cards, phone mockup, lower thirds, gradients, glow), TTS (`tts`), cleaned voice
   (`denoise`), upscaled stills (`upscale`), music/SFX (`audio` synth or licensed tracks). Fonts:
   `env.FONT_TITLE` / `env.FONT_BODY` (OFL, in `assets/fonts`). Write a `manifest.json` the build reads.
5. **Build the timeline** (`build.py`, inside Blender) with `vsekit.vse`: one storyboard `config.py`,
   named channels, every effect as a strip/keyframe/node group so it stays editable. Template:
   `projects/projectb_devlog/` (config → prepare → build → make.sh); smaller examples in `demos/d*.py`.
6. **Preview before rendering**: `blender -b file.blend --python vsekit/preview.py -- <out> 25 6 <frames…>`
   and Read the sheet. Fix layout issues now — a full render costs minutes, a preview seconds.
7. **Render** (`blender -b file.blend -a`, run in background), then **finalize**: `media.finalize()`
   (loudnorm to −14 LUFS, video stream copied), `media.probe()` + `media.loudness()` to verify, and a
   contact sheet of the final file to confirm nothing broke.
8. **Hand over**: final mp4, the `.blend`, plus whatever fits — `.srt` (`transcribe.to_srt`), chapters
   (`transcribe.chapters`), thumbnail, `.otio` (`wm.otio_export`, see API notes) for DaVinci Resolve.
   Say what you verified (frames, levels) and what you did not (you cannot listen to audio).

Where outputs go: user projects → their own folder (ask if unclear); experiments → `<VSEKIT>/media`
or `demos/` (media there is gitignored). Don't drop renders into unrelated code repos.

**Rebuilding overwrites manual edits.** Iterate with scripts while structure changes; once the user starts
polishing in Blender, edit the open file through MCP instead (check `bpy.data.is_dirty` first — never
reload a file with unsaved user changes; ask).

## Recipes (pick, then adapt)

- **Talking head / YouTube long-form**: whisper → `cut_list(min_gap≈0.3)` jump cuts → `vse.clip()` per kept
  range on alternating A/B channels → punch-in (scale 1.1–1.15) on every other cut to hide jumps →
  karaoke captions → SRT + chapters. Example: `demos/d2_jumpcuts.py`.
- **Shorts/TikTok hook edit**: 9:16, hook text in first 2 s, captions in the safe zone (y≈1250 of 1920),
  punch-ins/flashes on strong beats (`beats.strongest`), speed ramp via retiming, progress bar, −14 LUFS.
  Examples: `demos/d1_gameplay_short.py`, `projects/projectb_devlog`.
- **Trailer / music montage**: `scenes.detect` → pick usable shots → cut on beats (every 2 beats, then every
  beat for the climax) inside `beats.loudest_section()` → flashes on downbeats → title/end cards with
  attribution. Example: `demos/d6_auto_trailer.py`.
- **Reference breakdown** ("how is this video edited?"): `python -m vsekit.analyze <url|file>` → report.md
  with cuts/min, shot lengths, wpm, talk ratio, loudness, hook, chapters, contact sheet. Use it to set pace
  targets for the user's own edit.
- **Voice-over**: user's own voice beats any TTS; otherwise Kokoro (local) or edge-tts (online), then
  `tts.align()` (whisper) for caption timing when the engine gives none.
- **Bad audio**: `denoise.deepfilter()` (+ `voice_chain` without afftdn for EQ/compression). The ffmpeg-only
  chain is fine for light hiss, useless for heavy noise.
- **Low-res stills/UI**: `upscale(kind="anime"|"video2")` for UI/flat art; `"photo"` invents fake letters on text.
- **Game footage** (Unity): `tools/unity/record_bot_gameplay.cs` → JPEG frames → `media.assemble_sequence()`.

## What actually works (measured on the author's machine, RTX 3080)

| Tool | Verdict |
|---|---|
| faster-whisper large-v3-turbo | Excellent. 2 min of speech in ~15 s incl. load; accurate words + timings. Drops "um/uh" by default, so filler removal needs `initial_prompt` with disfluencies or audio-based detection. |
| Kokoro (am_michael, af_heart) | Best TTS here: natural, local, 12 s of audio in 0.2 s. English only without extra phonemizers. |
| edge-tts | Natural, has word timings, but online (text goes to Microsoft) and slow (~15 s per line). |
| Windows SAPI | Robotic. Only as an offline last resort. |
| DeepFilterNet | Removes heavy fan/hum/clicks convincingly; ~9 s CPU per 8 s audio. |
| ffmpeg voice chain (afftdn+EQ+comp) | Polish only; cannot rescue noisy recordings. |
| Real-ESRGAN anime / animevideo-x2 | Best for game UI screenshots, 1–2 s per image. x4plus is sharp but deforms text. |
| PySceneDetect (threshold 27) | Reliable shot lists (88 shots / 3:20 NASA video). |
| librosa beats | Good beat grid; tempo may come out at half/double (83 vs 167 BPM) — harmless for cutting, but check before quoting BPM. |
| NVENC | h264_nvenc 2× faster than x264 (larger files); hevc_nvenc fastest + small. No AV1 encode on RTX 30. |
| Unity Recorder + BalanceBot | Real 1080×1920 60 fps footage. **Record a JPEG sequence (~28 fps capture), never the MP4 movie recorder** — Unity's Media Foundation MP4 encoder stalls ~1 s per frame after ~100–200 frames. Details: `references/unity_capture.md`. |
| yt-dlp | Works with deno available (`env.tool_env()`); `--download-sections` for excerpts. |

## Blender 5.3 VSE pitfalls (cost real time before)

Read `references/blender_vse_api.md` before writing new build code. The short list:
`new_movie(..., fit_method='FIT')` explicitly (scripts default to original size); meta strips need
`frame_final_end` set after `move_to_meta`, and effect strips travel with their inputs; menu sockets on
compositor nodes take display names (`'Bloom'`, `'Repeat'`); retiming keys don't shift later keys;
`wm.otio_export` needs `workspace.sequencer_scene` in background mode; `frame_final_start/end` are
deprecated (removal in 6.0); summed VO+music+SFX clips — set `scene.audio_volume≈0.6` and normalise after.

## Growing VSEKit (do this as part of the job, not as an afterthought)

VSEKit is the user's long-lived toolbox and a git repo; anything reusable you write belongs there, so the
next video (and the next machine) starts further ahead.
- **Where code goes**: reusable helper → a function in the matching `vsekit/<module>.py` (or a new module
  + a line in `vsekit/__init__.py`); a concrete video → `projects/<name>/` (config/prepare/build);
  a tool test or showcase → `demos/`; Unity/Blender editor scripts → `tools/`. Not the scratchpad, not the
  user's game repo.
- **Adding a tool** means all of: install step in `setup.ps1` (idempotent, skip if present), pinned version in
  `requirements.txt` (or a separate venv + `requirements-<x>.txt` if it conflicts), discovery in
  `vsekit/env.py` (env-var override → PATH → usual locations), a check in `tools/doctor.py`, a row in the
  README tools table, and — after you have actually tried it — a verdict row in the table above.
- **No machine paths in code**: use `vsekit.env`; project-specific roots via env vars with defaults
  (e.g. `PROJECTB_ROOT`). Generated media, venvs and downloaded binaries stay gitignored.
- **Learned a gotcha?** Put it in the relevant `references/*.md` (or the pitfall list) right away.
- **Commits**: run `tools/doctor.py` (and the touched script) first, then propose a Conventional Commit
  (`feat(transcribe): add filler-word prompt`, `fix(vse): fit movie strips`, `docs(skill): …`) and commit
  only after the user approves; push only when asked. Commit to `main` unless told otherwise.

## Rights and privacy

- Downloaded videos are for analysis/reference. Reuse only what is licensed for it (CC-BY with visible
  attribution, public domain, the user's own uploads); say so when picking sources.
- edge-tts sends text to Microsoft; whisper, Kokoro, DeepFilterNet, Real-ESRGAN run locally — prefer local
  for anything private.
- Don't recreate a specific existing creator's branded video/thumbnail as if it were theirs.

## Reference files

- `references/blender_vse_api.md` — VSE/compositor API notes, snippets, gotchas.
- `references/platforms.md` — YouTube / Shorts / TikTok specs, safe zones, loudness, thumbnails, chapters.
- `references/unity_capture.md` — recording gameplay from a Unity project (Recorder + bot + traps).
