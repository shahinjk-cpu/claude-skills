---
name: audio-intelligence-suite
description: >
  Voice and audio processing suite: OpenAI Whisper transcription, ElevenLabs text-to-speech, Sherpa-ONNX offline TTS, meeting audio to structured Obsidian notes, spectrogram analysis, and sound effects synthesis.
category: content_media
version: "2.0.0"
role: consolidated_suite
triggers: audio-intelligence-suite, master audio, speech & voice intelligence suite, audio-studio-mcp, earshot, meeting-documenter, openai-whisper-api, openai-whisper, real-sound, sag, sherpa-onnx-tts, songsee
---

# 🎙️ Master Audio, Speech & Voice Intelligence Suite

Voice and audio processing suite: OpenAI Whisper transcription, ElevenLabs text-to-speech, Sherpa-ONNX offline TTS, meeting audio to structured Obsidian notes, spectrogram analysis, and sound effects synthesis.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (9 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`audio-studio-mcp`**: Local AI music and sound effects generator MCP for Claude Code and coding agents. Generates background music, instrument loops, sound effects using Stable Audio 3 locally without cloud API fees.
  - *Reference File:* `references/audio-studio-mcp.md`
- **`earshot`**: Listen with earshot whenever you must judge, choose, trim, verify or compare sound you cannot hear - picking a sound effect, music or ambience from candidates, finding the cleanest moment in a recording, checking whether audio reads as a real recording or as code-synthesized, reviewing a soundtrack or a video's audio (what happens when, sync to picture, loudness, mix), A/B-ing a mix change, making a sound in code and improving it by listening (earshot forge), or giving a code-made film its sound effects from the shipped bank (earshot sfx / kit). Use it before telling anyone how audio sounds.
  - *Reference File:* `references/earshot.md`
- **`meeting-documenter`**: - Use when the user says "document this meeting", "process this recording", "create meeting notes", or "summarize this meeting"; or provides a path to an audio file (MP3, WAV, OGG, M4A, FLAC, WebM, AAC) or an existing meeting transcript to summarize and integrate into their notes.
  - *Reference File:* `references/meeting-documenter.md`
- **`openai-whisper`**: Local speech-to-text with the Whisper CLI (no API key).
  - *Reference File:* `references/openai-whisper.md`
- **`openai-whisper-api`**: OpenAI Audio Transcriptions API via curl; gpt-4o-transcribe, mini, diarize, or whisper-1.
  - *Reference File:* `references/openai-whisper-api.md`
- **`real-sound`**: Build premium, realistic soundtracks for code-made videos and animations from real licensed recordings - launch films, product and feature videos, UI walkthroughs, logo stings, explainers, trailers and animated shorts made with Remotion, HyperFrames, three.js, GSAP or any renderer. Use this whenever a video or animation needs sound design, SFX, foley, ambience, music, a soundtrack, a score, UI click / whoosh / riser / impact / logo-sting sounds, or a music edit to picture; whenever a synthesized or "random" sounding soundtrack must be replaced with real recordings; or when the user asks to source, license, credit, mix, master, critique or mux audio for a film. It covers cue lists from the picture, sourcing from Freesound / Mixkit / composer libraries with licence checks, a music edit at bar lines, a JSON sound design rendered by a deterministic mixer, measured QA (clicks, masking, harshness, sync, loudness) plus earshot listening, a multi-agent critique, mastering, credits and the mux.
  - *Reference File:* `references/real-sound.md`
- **`sag`**: ElevenLabs text-to-speech with mac-style say UX.
  - *Reference File:* `references/sag.md`
- **`sherpa-onnx-tts`**: Local text-to-speech via sherpa-onnx (offline, no cloud)
  - *Reference File:* `references/sherpa-onnx-tts.md`
- **`songsee`**: Generate spectrograms and feature-panel visualizations from audio with the songsee CLI.
  - *Reference File:* `references/songsee.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `audio-studio-mcp`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
