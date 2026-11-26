# The 7 choices (the style board)

For every choice show 3 options (A, B, C) of the same scene in this brand, changing only that one thing. Mark one as recommended. Colors, fonts and tone come from `brands/<brand>/brand.json`. Pick options that fit the brand's `style` field; do not offer a look the brand forbids.

| # | Choice | What it decides | Option examples | How to show it (cheap first) | Built with |
|---|---|---|---|---|---|
| 1 | **Style** | Overall look | A clean UI / product, B paper collage, C kinetic type or a named film style | 3 stills | `lemo-opuscar` styles, `motion-prompt` ids, `motionvideo` references, collage tools |
| 2 | **Color** | Palette and contrast | A brand main on dark, B brand on light, C high-contrast accent | 3 stills | brand colors; check contrast on a phone-size frame |
| 3 | **Layout** | Framing, safe areas, cover | A centered, B left-aligned block, C full-bleed image with a text strip | 3 stills with the safe-area guide | 1080x1920, keep out the top 150 px and bottom 250 px; cover from `tools/thumbnail` |
| 4 | **Text** | How words appear | A big headline, B kinetic word by word, C caption rail | 3 stills | `captions-overlay`; Kurdish right-to-left check on every sample |
| 5 | **Animation** | How things enter, move and leave | A spring pop, B slide with a held pause, C zoom-through or waterfall entry | 3 loops of about 2 s | `motion-doctrine`, `cut-the-curve`, `seam-craft`, `oversized-cursor`, `lottie` |
| 6 | **Speed** | Pacing and cut rhythm | A calm (longer holds), B normal, C fast (short beats) | 3 short previews or timeline strips | beat sheet (`scripts/beat_sheet.py`) |
| 7 | **Sound** | Music mood and effects, voice or not | A quiet minimal music, B click and whoosh effects, C voiceover | 3 short audio clips | free sounds first (`templates/video/AUDIO.md`); ElevenLabs `sound-effects`, `music`, `text-to-speech` only after the owner OKs the credit use |

## Order
Show them in this order, because later choices depend on earlier ones: Style, Color, Layout, Text, Animation, Speed, Sound. The owner may answer all at once ("all your picks" is valid).

## Sample rules
- Same scene, same copy, same size in every sample; only the chosen variable changes.
- Use the brand's real words (the hook line from `studio-script`), not placeholder text.
- Label samples A, B, C and write one line under each ("calm, long holds").
- Samples are a preview, not the final render. Say so.
- Keep a record of what was offered so a changed mind does not mean re-rendering everything.

## Style-board tool
`tools/styleboard/make.mjs` renders these 7 choices for a brand in about 15 seconds (stills with Chrome, loops with ffmpeg, local sound files) and writes `board.html` + `board.json`. See `tools/styleboard/README.md`. Per-brand settings live in `brands/<brand>/styleboard.json`.

## Not built yet
A style-board picker in the console's Create tab that saves the picks as a Request (today the owner copies the picks line from `board.html`).
