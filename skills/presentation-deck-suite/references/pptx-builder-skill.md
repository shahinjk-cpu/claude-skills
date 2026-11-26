---
name: pptx-builder
description: Use this skill to create professional, fully-editable PowerPoint (.pptx) decks. Design each slide as HTML/CSS (preview it as an Artifact to iterate visually with the user), then run the included Playwright + python-pptx pipeline to convert the HTML into native, editable PowerPoint objects (rectangles, text boxes, images, icons, tables, lines) at pixel-accurate positions — not a screenshot dump. Trigger on "make a powerpoint", "build a pptx", "create slides", "presentation deck", "slide design".
---

# PPTX Builder

Two-stage workflow: **design in HTML** (fast to iterate, easy to preview), then
**compile to native PPTX** (fully editable in PowerPoint — real shapes, real
text, real tables, not an image).

## Stage 0 — Pick a style (palette + shape language)

Before writing any slide HTML, settle on a visual identity so every slide in
the deck stays consistent instead of improvising colors/corners per slide.

1. Publish `templates/style-gallery.html` as an **Artifact**. It shows 12
   named presets (A–L), each pairing a color palette with a distinct shape
   language — sharp squares, softly rounded cards, pill badges, small circle
   accents tucked in the corners, decorative blobs, etc. A–F are general
   purpose; G–L lean into more specific deck genres (consulting, creative
   agency, finance/governance, keynote-style minimal, SaaS product, warm
   editorial). Ask the user to pick a letter, or to describe a tweak to one
   (e.g. "D but with teal instead of gold").
2. **If the user already has a brand or template to match** — an existing
   .pptx, a brand guideline, a logo, or just a list of hex colors — skip the
   gallery and use that instead. Get the exact colors, fonts, and
   corner-radius convention from what they give you (open an existing .pptx
   directly, or run `python scripts/extract.py` on it, to sample real
   values rather than guessing).
3. Whichever path was used, write down the resolved palette (hex values)
   and shape convention (corner radius, accent motif) before starting
   Stage 1 — `reference/style-presets.md` has the exact values for each
   lettered preset. Reuse those exact values in the shared `:root { --... }`
   CSS block across every slide (see the tip in `reference/conventions.md`).

If the user explicitly says they don't care and to just use sensible
defaults, skip straight to Stage 1 with preset A (Corporate Blue).

## Stage 1 — Design the deck in HTML

Write one HTML file containing every slide as:

```html
<section class="slide" style="width:1280px;height:720px;position:relative;overflow:hidden;">
  ...
</section>
```

1280×720px = a standard 16:9 slide at 96dpi. Stack multiple `.slide` sections
in the same file (with a visual gap between them, e.g. `margin-bottom:40px`)
so the whole deck can be eyeballed at once.

**Every element that should become a distinct PowerPoint object must carry a
`data-pptx="..."` attribute.** Elements without it are pure layout scaffolding
(flexbox/grid wrappers) and are ignored by the extractor — only tag the things
that should actually exist as shapes in PowerPoint.

Read `reference/conventions.md` before writing HTML — it documents the exact
`data-pptx` types, which CSS properties are honored, and common pitfalls.
Copy `templates/slide-template.html` as a starting point; it demonstrates a
title slide, a KPI-card row, a bullet/icon list, an image slide and a table
slide.

**Use small icons by default** on KPI/stat blocks, category cards, bullet
lists, and contact/detail rows — a bare number or a bare "Téléphone" label
reads as an unfinished draft next to the same content with a glyph beside
it. `reference/icons.md` has a large, ready-made, visually consistent icon
library — people/org, growth/activity, communication, tech/data,
documents/workflow, trust/values, logistics/finance, plus generic
social-platform marks for a "suivez-nous" row — to copy from, so every deck
this skill produces shares the same icon language instead of each deck
improvising its own. Only skip icons where the chosen style is deliberately
bare-minimalist (e.g. preset B/Minimal Mono, which relies on hairline rules
instead).

If the user supplied a logo, check whether it has a transparent background
and whether its ink colors have enough contrast against the deck's
background before placing it directly (sample a few pixel colors — don't
assume). A logo designed for a white background dropped straight onto a
dark slide is a common failure mode: dark text on transparent PNG becomes
unreadable on a dark bg. When contrast is insufficient, place the logo on a
small light "plate" (a rounded-rect card in a light neutral) rather than
recoloring the logo — that stays true to the brand's actual logo file.

Publish the HTML as an **Artifact** and iterate with the user until the
design is approved — do not run the conversion pipeline on unapproved
designs.

## Stage 2 — Compile to native .pptx

Once the HTML is approved, from this skill's directory run:

```bash
python scripts/extract.py <slides.html> <work>/slides.json <work>/images
python scripts/build_pptx.py <work>/slides.json <output>.pptx
```

- `extract.py` opens the HTML in headless Chromium, measures every
  `[data-pptx]` element's exact position/size/computed style, and rasterizes
  `data-pptx="icon"` elements to transparent PNGs. Output: `slides.json` +
  an `images/` folder.
- `build_pptx.py` reads that JSON and creates a real `python-pptx`
  presentation: autoshapes with fill/border/gradient/shadow, text boxes with
  per-run bold/italic/color/font, native tables, pictures, and connector
  lines — all positioned in EMU converted from the measured pixels.

Both scripts print warnings (not silent failures) for anything they had to
skip — read stderr after each run and fix the HTML rather than ignoring
warnings.

## Stage 3 — Verify (never skip this)

A pptx can be silently broken in two ways that nothing in Stage 2 will warn
you about, because python-pptx and a well-formed-XML check are both too
lenient to catch them — they've each happened for real, once, on a generated
deck that looked fine right up until the user opened it:

1. **Structural corruption** — invalid-per-schema XML (e.g. a duplicated
   element the schema only allows once) that PowerPoint silently "repairs" by
   dropping the offending content, with zero error anywhere in the pipeline.
2. **Shifted/misplaced content** — the file opens perfectly and looks
   structurally valid, but elements on some slide are offset from where the
   HTML placed them (this specific case was a Playwright viewport-scroll bug,
   now fixed in `extract.py`, but treat it as a class of bug, not a one-off).

Run both checks after every `build_pptx.py`, before telling the user the deck
is ready:

```bash
python scripts/verify_pptx.py <output>.pptx
python scripts/render_preview.py <output>.pptx <work>/preview
```

`verify_pptx.py` catches case 1 (zip/XML integrity, duplicate schema-singleton
elements, illegal characters, dangling image relationships, a python-pptx
open check) and exits non-zero with a specific list if anything is wrong.

`render_preview.py` catches case 2 — it converts the pptx to PDF via
LibreOffice and rasterizes every page to PNG. **Actually open each PNG with
the Read tool and look at it** — comparing against the approved HTML design —
before reporting success. Requires LibreOffice (`winget install
TheDocumentFoundation.LibreOffice`) and `pip install pymupdf`, both one-time
installs.

Do not report a deck as done on the strength of "the scripts ran without
warnings" alone — that was true both times this pipeline actually produced a
broken or visually corrupted file. Only `verify_pptx.py` passing *and* an
actual look at every rendered slide count as done.

## Known limits (design around these, don't fight them)

- Borders are read from `border-top` only — use uniform 4-side borders.
- Gradients: 2-stop `linear-gradient` only, angle + first/last color.
- Shadows: any non-`none` `box-shadow` becomes one fixed soft drop shadow —
  CSS shadow tuning (blur/spread/offset) is not preserved.
- Fonts must be installed on the machine that later *opens* the .pptx, or
  PowerPoint will substitute — stick to common fonts (Arial, Calibri,
  Segoe UI, Georgia) unless the user confirms the target machine has the
  custom font.
- Stacking order follows DOM order, not `z-index` — write background
  elements first, foreground elements last in the HTML.
- `data-pptx="icon"` elements are rasterized (screenshot), so they're
  pictures, not editable shapes — use this only for actual icons/logos/SVG
  art, never as a shortcut for text or simple rectangles.
