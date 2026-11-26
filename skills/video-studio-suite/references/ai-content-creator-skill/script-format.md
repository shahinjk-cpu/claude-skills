# Script format: emotion tags and character notes

Three files are written for every script. Only `work/script.txt` drives timing and word count.

| File | Contains | Used for |
|---|---|---|
| `work/script.txt` | Spoken words only, no brackets | Timing, word count, engine handoff |
| `work/script_elevenlabs.txt` | Spoken words + single `[ ]` emotion tags | Paste into ElevenLabs |
| `work/script_full.txt` | `[[[ ]]]` production notes + the same `[ ]` tags | Director's copy, shot planning, character names |

## Single brackets `[ ]` — ElevenLabs only

- Use one short lowercase delivery word or phrase: `[warm]`, `[curious]`, `[excited]`, `[nervous]`, `[amused]`, `[proud]`, `[sad]`, `[whispers]`, `[pause]`.
- Put the tag at the start of the line it colours, or immediately before the phrase it changes.
- Never use `[ ]` for character names, props, camera directions or scene description — ElevenLabs would try to speak them.
- At most 1–2 tags per line. Over-tagging makes the voice sound mechanical; tag a line only when the delivery changes.

## Triple brackets `[[[ ]]]` — production notes, never spoken

- Use them for: character name + action/pose, prop, setting, lighting, camera move, and the point where a reaction must land.
- Name a character only if they appear on screen or speak. Otherwise leave the line untagged — it is the narrator.
- Keep names short, uppercase and consistent: `[[[IVO]]]`, `[[[JUN]]]`, `[[[PELL]]]`. Define each once at the top with `[[[CAST: ...]]]`.
- Put the note on its own line immediately before the line it describes.
- `[[[ ]]]` notes are stripped from `work/script_elevenlabs.txt` before the user pastes into ElevenLabs. Never let a triple-bracket note reach TTS or timing.

## Worked example

`script_full.txt`:

```
[[[CAST: IVO — old clockmaker | JUN — grandson and narrator]]]
[[[SET: sunlit workshop, a stopped clock on the bench]]]
[[[NARRATOR]]]
[warm] My grandfather could fix anything. Except the one thing I asked him to.
[[[IVO — lifts the caseback, squints through a loupe]]]
[curious] Bring me the tiny screwdriver. The one with the blue handle.
[[[JUN — hands over a hammer instead; both freeze]]]
[amused] I gave him a hammer. He looked at me like I'd invented rain.
```

`script_elevenlabs.txt`:

```
[warm] My grandfather could fix anything. Except the one thing I asked him to.
[curious] Bring me the tiny screwdriver. The one with the blue handle.
[amused] I gave him a hammer. He looked at me like I'd invented rain.
```

`script.txt`:

```
My grandfather could fix anything. Except the one thing I asked him to.
Bring me the tiny screwdriver. The one with the blue handle.
I gave him a hammer. He looked at me like I'd invented rain.
```

## Checks before delivering

- Word count and estimated seconds come from `work/script.txt` only (about 3.7 words/s; slow voices 2.6).
- No `[[[` appears in `work/script_elevenlabs.txt` or `work/script.txt`.
- No `[` appears in `work/script.txt`.
- Every name used in `[[[ ]]]` notes has a `[[[CAST: ...]]]` line.
- The script fits the chosen length. If the user changes dialogue, rewrite all three files before handoff.
