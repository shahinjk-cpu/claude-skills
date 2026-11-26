# Auto-generated voiceover

Used when the user chooses **Auto** instead of supplying a recording. Narration stays in one voice; quoted dialogue is split out and spoken by a mapped character voice.

## Provider selection

`--provider auto` (the default) checks `ELEVENLABS_API_KEY`:

- Key present → ElevenLabs (emotion tags in `[ ]` are passed through and actually work).
- Key absent → offline **Kokoro** through lemo-opuscar's voice tier. No key, no network, no cost.
- `--provider elevenlabs` with no key, or with a missing narrator voice id, falls back to Kokoro with a printed warning.
- `--provider kokoro` forces the free path.

Never write the key into a brief, report, script or project file. It is read only from the environment.

## `work/voices.json`

Written at Stage 2, alongside the three script files. Voice ids are never invented:

```json
{
  "narrator": {"elevenlabs": "ENV:ELEVENLABS_VOICE_ID", "kokoro": "am_adam", "speed": 0.92},
  "characters": {
    "IVO": {"elevenlabs": "ENV:ELEVENLABS_VOICE_ID_IVO", "kokoro": "bm_george", "speed": 0.90},
    "JUN": {"elevenlabs": "ENV:ELEVENLABS_VOICE_ID_JUN", "kokoro": "af_bella", "speed": 1.00},
    "PELL": {"elevenlabs": "ENV:ELEVENLABS_VOICE_ID_PELL", "kokoro": "bf_emma", "speed": 0.95}
  },
  "pronouns": {"he": "IVO", "she": "PELL", "i": "JUN"}
}
```

`ENV:NAME` means "read this environment variable". If the variable is unset, that voice is unavailable and the whole film falls back to Kokoro, so every character always has a voice. Kokoro names such as `af_bella`, `am_adam`, `bm_george`, `bf_emma` are valid; an unknown name makes `tts.py` print the full list. `pronouns` maps the attribution nearest each quote (`he said`, `she whispered`, `I said`) to a character; quotes with no attribution stay in the narrator voice.

## Commands

From the project folder, using the skill's helper:

```
python "<ai-content-creator>/scripts/auto_voice.py" "<absolute project path>" --preview 3
python "<ai-content-creator>/scripts/auto_voice.py" "<absolute project path>"
```

- `--preview N` generates only the first N script lines into `work/preview_voice.mp3`. **Always run the preview first and ask the user to approve it** before the full generation (ElevenLabs spends credits).
- The full run writes `voice.mp3` and `voice.wav` at the project root, `work/voice_segments.json` (speaker/text/provider per segment) and `work/voice_duration.json` (real seconds from `ffprobe`).
- The helper joins per-line clips with 0.06 s between segments of the same line and 0.18 s between lines. It does not change pitch, speed or level.
- If Kokoro's model is missing, install the voice tier first: `sh "<lemo-opuscar skill>/scripts/setup.sh" deps voice` (about 0.55 GB plus a Whisper model on first ASR check). Run it in the background.

## After generation

1. Read `work/voice_duration.json`; use that real duration instead of the rough words/s estimate in `BRIEF.md`.
2. Tell the user: provider used, duration, and where `work/voice_segments.json` is. Fall back to Kokoro silently only after warning them once.
3. Continue to Stage 4. Both engines accept the generated `voice.mp3`; `cartoon-audio-short` times from the clean `work/script.txt`, and `lemo-opuscar` treats the file as a supplied recording.
4. If the user rewrites any dialogue, regenerate the audio and re-run timing before rendering.
