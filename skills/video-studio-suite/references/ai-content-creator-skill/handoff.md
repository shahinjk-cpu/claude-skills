# Engine choice and handoff

## Decision table

| Topic shape | Recommended engine | Why | Alternative |
|---|---|---|---|
| Voice-driven original story, joke, twist, or everyday mystery | `cartoon-audio-short` | Built for a fixed voiceover: picture is timed to the audio, finished 1080×1920/30 fps, fastest path | `lemo-opuscar` in a cartoon style |
| Explainer, process, data, "how it works", tech teardown, news-style brief | `lemo-opuscar` | 99 art styles include blueprint, exploded teardown, satellite briefing, data maps, documentary | `cartoon-audio-short` if there is a spoken character story |
| Visual spectacle or a distinctive look is the hook (oil painting, ukiyo-e, watercolor, paper-cut) | `lemo-opuscar` | Style is the product; the library supplies the grammar | `cartoon-audio-short` for a simple flat-cartoon version |
| Non-English narration | `lemo-opuscar` | Its language flow is explicit and it has a voice tier; cartoon `timing.py` assumes English syllables | `cartoon-audio-short` with a Whisper `words.json` |
| User has a recorded voice file and wants it unchanged | either; prefer `cartoon-audio-short` | Both keep the voice intact; cartoon has the most deterministic timing | `lemo-opuscar` for a stylized look |
| User wants TTS instead of their own voice | `lemo-opuscar` | Voice tier is available there | Ask the user to record for cartoon |

If both fit, pick `cartoon-audio-short` for story/joke and `lemo-opuscar` for explainer/spectacle. Always name the alternative and one reason for the choice. User preference overrides the table.

## Script file discipline

Pass `work/script.txt` (spoken words only) to the engine for timing and word count. The user records from `work/script_elevenlabs.txt` (`[ ]` emotion tags, no `[[[ ]]]` notes). `work/script_full.txt` carries the `[[[ ]]]` character/prop/setting notes and is for the director and shot plan only — never feed it to TTS or timing. Character names in those notes can seed the cartoon cast or the lemo treatment, but the spoken words must stay identical across all three files. Audio may be user-recorded or produced by the auto-voice helper; either way both engines receive the same `voice.mp3` plus the clean script. Choose the engine by need from the decision table, not by who made the audio.

## Handoff A — cartoon-audio-short

1. Find the kit. Its base directory is the one reported when that skill loads (typically `<cartoon-audio-short skill>/kit`). If missing, read `reference/engine-gotchas.md` § "Rebuilding the kit" in that skill before proceeding.
2. From Git Bash (PowerShell: `cmd.exe /d /c "bash ..."`), run:
   - `bash "<kit>/tools/setup.sh" ~/shorts/<slug>`
   - `cd ~/shorts/<slug> && bash tools/doctor.sh` — fix anything marked MISSING first.
3. Copy the verified audio to `~/shorts/<slug>/voice.mp3`. Ensure `work/script.txt` holds the exact final narration text.
4. `bash tools/buildstory.sh`.
5. Load the skill with the `skill` tool (`id: cartoon-audio-short`).
6. Tell it explicitly: "Intake is already resolved: script and voiceover are ready. Start at Stage 4. Project: <absolute path>. Do not re-ask Stages 1–3." Include the word count and chosen length.
7. From that point follow its instructions: timing, shot plan in `work/PLAN.md`, projection and frame checks, contact sheet + **wait for the user's go** before the long render, detached render, finish, QA, deliver.

## Handoff B — lemo-opuscar

1. Recommend 2–3 fitting styles from `~/lemo-opuscar/styles/README.md` and pick one (or use the user's choice). Avoid styles marked ✦ unless an image generator is available — check `python3 core/image/gen_image.py --check` from the library root first.
2. Load the skill with the `skill` tool (`id: lemo-opuscar`).
3. Tell it: "Start with the brief already filled. Project folder: <absolute path to ~/shorts/<slug>> (do not create a new folder in the current working directory). Topic: <research topic>. Language: <language>. Style: <exact gallery name>. Voiceover: <audio path>. Script: <absolute path to work/script.txt>. Length: <seconds>. Storyboard review: <yes/no>."
4. Its Workflow step 1 (brief) is pre-answered; go to the treatment, then look, production, and delivery. Do not ask its language or style questions again.
5. If the user's audio is a WAV and the voice tier expects another format, follow that skill's TECHNIQUE.md; never speed-change the voice.

## After either handoff

Stop orchestrating. The loaded skill's rules now take precedence, including its contact-sheet approval gate and its audio mix rules. Do not start a second film engine, do not duplicate renders, and do not write another script. The final message to the user contains the absolute path of the finished MP4, the duration, and the QA sheet path.
