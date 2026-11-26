---
name: editorial-page-layout-guidelines
description: >-
  Operational layout formulas, typographic hierarchy, and modular grid archetypes for high-density,
  publication-grade institutional reports (Letter portrait) and executive slide decks (16:9 widescreen).
  Enforces vertical fill budgeting (85-92% Letter, 72-88% 16:9), asymmetric grids, hairline scaffolding,
  and zero empty-page voids.
---

# Editorial Page Layout & Modular Grid Guidelines

This skill codifies the grid mathematics, vertical fill budgets, and typographic architecture used by institutional publications (World Economic Forum, IPCC, McKinsey Global Institute, Stripe Press, and *The Economist*) across both **Letter portrait reports (`612×792 pt`)** and **16:9 widescreen executive decks (`960×540 pt`)**.

---

## 1. The 4 Fundamental Layout Laws

### Law 1: The Vertical Fill Budget
- **Letter Portrait Report (`612 × 792 pt`, `54 pt` margins):**
  - Live canvas: `504 pt` wide × `684 pt` tall.
  - **Target Fill:** **`85%–92%` (`580–630 pt`)** on every page (minimum QA gate `82%`).
  - Pages terminating in the upper 30–50% read like accidental page spills or unfinished drafts. Never issue a hard `PageBreak()` after short copy without pairing secondary structural anchors (asymmetric marginalia, Tufte tables, or 3-column KPI ribbons).
- **16:9 Widescreen Slide Deck (`960 × 540 pt`, `42 pt` L/R, `38 pt` top, `34 pt` bottom):**
  - Live canvas: `876 pt` wide × `468 pt` tall.
  - **Target Fill:** **`72%–88%` (`337–412 pt`)** per slide (minimum QA gate `72%`).
  - Slides require more breathing room than print pages while still anchoring top-to-bottom rhythm with an action title, primary exhibit, and structured synthesis rail.

### Law 2: Asymmetric Grid Discipline (Letter Reports)
Single-column prose spanning the full `504 pt` width produces 85–100+ character lines, inducing reading fatigue.
- **The Golden Split (`310 + 14 + 180 = 504 pt`):**
  - **Primary Narrative Column:** `310 pt` (~61.5%) → optimal 55–65 characters per line.
  - **Gutter:** `14 pt` pure whitespace.
  - **Companion Marginalia / Sidebar:** `180 pt` (~35.7%) → methodological notes, pull quotes, accounting audits, or key metric spreads, anchored with a `1.2 pt` top accent hairline and subtle tonal tint (`#f1f5f9` light / `#111827` dark).

### Law 3: Hairline Scaffolding (No Boxed Dashboard Cards)
- Never trap KPIs, narrative paragraphs, or tables inside heavy rectangular `BOX` strokes, rounded web cards, or drop shadows.
- Structure groupings through **typographic proximity**, **generous column gutters (`12–16 pt`)**, **hairline rules (`0.25–1.2 pt`)**, and subtle borderless tonal bands.
- **Tufte Ledgers:** `1.0 pt` top/bottom booktabs rules, `0.75 pt` header underline, `0.25–0.35 pt` horizontal row hairlines, zero vertical grid lines, zero outer frame.

### Law 4: Bold Tracked Small-Caps Lead-ins (No Drop-Cap Tables)
Two-cell table drop caps frequently duplicate letters, misalign baselines, or collide in programmatic PDF compilers. Lead every major narrative section with inline bold uppercase small-caps:

```html
<font color="#0284c7"><b>ATMOSPHERIC ACCUMULATION HAS ACCELERATED THREEFOLD</b></font> since systematic instrumental measurements began...
```

---

## 2. Five Letter Portrait Page Archetypes (`612 × 792 pt`)

| Archetype | Structure | Target Fill |
| :--- | :--- | :--- |
| **A. Hero Cover & Executive Opener** | Kicker (`8 pt`) + Action Headline (`19.5–22 pt`) + Italic Deck + 3-col floating KPI ribbon + Lead visual + Asymmetric `310/180` opening brief | `88%–96%` |
| **B. Asymmetric Narrative & Marginalia** | Section opener + `310 pt` investigative copy with small-caps lead-in / `180 pt` tinted sidebar (methodology, glossary, pull quote) + Bottom 3-col stat ribbon | `86%–92%` |
| **C. Data & Analysis Exhibit Spread** | Section opener + Full-width `504 pt` 300-DPI chart (`190–225 pt` tall) + Source/N caption + Asymmetric `310/180` forensic synthesis | `88%–95%` |
| **D. Analytical Tufte Ledger Spread** | Section opener + Framing copy + Full-width Tufte table (with optional inline sparklines & explicit `[N/A]` cells) + Lower synthesis | `85%–92%` |
| **E. Sovereign Provenance Colophon** | Pull quote + Cryptographic SHA-256 raw-source manifest table + 2-column audit certification & open-data attribution | `88%–92%` |

---

## 3. Four 16:9 Widescreen Slide Archetypes (`960 × 540 pt`)

Keep slide headlines to **one single crisp assertive line** (avoid 1–2 word widow wraps):

1. **Slide Archetype 1 — Cover Hero:** Top `4 pt` accent bar + Kicker + `27 pt` Title + `12 pt` Deck + 4-column tonal KPI strip (`1.2 pt` top accent rule) + 3-column Executive Thesis strip + bottom Provenance Receipt ledger (`~80–85%` fill).
2. **Slide Archetype 2 — Dual-Panel Visual + 3-Column Synthesis:** Kicker + single-line `15 pt` Action Title + full-width (`876 × 315 pt`) side-by-side chart exhibit + 3-column structured synthesis rail below hairline (`~85–91%` fill).
3. **Slide Archetype 3 — Executive Tufte Ledger Slide:** Kicker + Action Title + full-width Tufte table (`10` columns with inline sparklines and explicit amber `[N/A]` cells) + Rule 5 methodological caption + 3-column bottom insight strip (`~85–90%` fill).
4. **Slide Archetype 4 — Visual + Cryptographic Audit Close:** Kicker + Action Title + compact full-width exhibit (`876 × 238 pt`, e.g. Stephen Few bullet graphs) + bottom 2-column split: SHA-256 raw file manifest (left) and 5-Phase Audit Receipt (right) (`~84–89%` fill).
5. **Slide Archetype 5 — Consulting Flagship Polarity Sequence (WeasyPrint + SVG):** Alternate `#051C2C` Dark Midnight Cover & Executive Summary → `48%/52%` Split Chapter Divider (`120 pt` white serif numeral) → Pure `#FFFFFF` Exhibit Slides featuring a `19.5 pt` bold serif action title above a `1.1 pt` navy rule, optional `#EFEFEF` right-hand implications sidebar with a straddling circular `#051C2C` `»` badge, and a bottom-right `#9AE6FF` section progress pill.

---

## 3B. Six Full-Bleed Photo Magazine Archetypes (`612 × 792 pt`, `>= 50%` Photography)

For photography-first editorial magazines (*Kinfolk* × *Cereal* × *Condé Nast Traveler* × *National Geographic*), never repeat the same bleed geometry on two consecutive pages. Every page must touch `>= 2` trim edges and pass an exact clip-aware visible photo coverage gate of **`>= 50%`** (typically `60%–100%`):

| Archetype | Structure & Bleed Edges | Visible Photo % |
| :--- | :--- | :--- |
| **M1. Full-Bleed Iconic Cover** | `BLRT` bleed (`3:4` hero) + wide-tracked centered `Didot` masthead (`62 pt`) in quiet upper sky + bottom-left coverline + bottom-right hairline miniature TOC | `~99%` |
| **M2. Top Bleed Feature + 2-Col Essay** | `LRT` top full-bleed (`484 pt`) with rotated marginal credit + warm `#FAF8F5` lower editorial bed (`308 pt`) with 3-line drop cap, 2-col reportage, italic pull quote, oversized serif folio | `~61%` |
| **M3. Asymmetric 65/35 Right Vertical Bleed** | `BRT` right bleed (`396×792 pt`) + narrow left `#FAF8F5` anchor column (`216 pt`, `display: block` for clean drop cap) with stacked display title, italic deck, tight `34–38` char measure, bottom caption | `~65%` |
| **M4. Full-Bleed Photo Essay Plate** | `BLRT` full-bleed vertical plate + display serif headline set directly into matte shadow negative space (zero box) + lower-edge translucent dark editorial band | `~99%` |
| **M5. Panorama + Inset Diptych** | `LRT` panoramic top (`364 pt`) + `4 pt` white print gutter + bottom-left essay (`268 pt`) + `BR` full-bleed inset (`340×424 pt`) | `~76%` |
| **M6. Inverted Calm Top / Contact-Sheet Triptych / Closing Dusk Colophon** | Alternate top-header + `BLR` bottom bleed (`~68%`), `LRT` 3-photo asymmetric triptych with `4 pt` white gutters + 3-col numbered micro-caption strip (`~77%`), and `BLRT` closing plate with SHA-256 colophon ledger in the shadowed lower 38% (`~99%`) | `68%–99%` |

---

## 3C. Scientific Monograph × Learning Magazine Crossover Archetypes (`612 × 792 pt`)

Choreographed across true facing spreads (`[2|3]`, `[4|5]`, `[6|7]`, `[8|9]`, verified via `render_spreads.py` and `audit_contrast.py`), pairing full-bleed botanical/scientific photography with live audited vector exhibits and learning scaffolding (`demos/botanica-veridica/`):

- **S1. Evolutionary & Telemetry Facing Opener (`[2|3]`):** Left page pairs a live phylogenetic cladogram (parsed from OpenTree Newick) + *DK*-style 6-column comparative morphology silhouette strip + *NatGeo*-style logarithmic scale lineup; right page pairs a live equirectangular GBIF world dot-map + herbarium-vs-citizen-science ratio bars + 12-month flowering phenology matrix. Keep both facing page display headlines on matching single lines.
- **S2. Studio Specimen + 90° SVG Anatomy Spread (`[4]`, `[8]`):** Top `~56%` edge-to-edge studio specimen plate on `#F7F3E8` archival ground overlaid with pure-vector SVG 90° elbow callouts and a metric scale bar; lower `~44%` `#FBF9F4` monograph bed containing italic binomial + Roman authority, IUCN status badge, clickable registry link, drop-cap essay or numbered 1-2-3 mechanism steps, live monthly sparkline chart, and a tinted `#F1ECE1` **"Field Check"** learning box.
- **S3. Habitat Bleed + Circular Magnifying-Lens Medallion (`[5]`, `[6]`, `[7]`, `[9]`):** Alternate right-column (`61%` bleed), top-bleed with a `134 pt` circular macro zoom medallion (`border: 2.5pt solid #FBF9F4`), overhead structural truss anatomy pills, and inverted calm-top / bottom-bleed spreads so opposing pages always contrast visually.
- **S4. Dichotomous Field Key & Rule 9 Verification Close (`[10]`):** Top half houses an interactive pure-vector branching dichotomous identification key (binary observable traits linking directly to species plates); bottom half holds the Rule 9 live taxonomy reconciliation Tufte ledger and SHA-256 cryptographic & photographic colophon.

---

## 4. Typographic Hierarchy Scale (`Inter` with `Helvetica` Fallback)

| Token | Size / Leading | Weight | Light Mode | Dark Mode | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Kicker` | `8.0 / 10.5 pt` | Bold | `#0284c7` | `#38bdf8` | Section / slide classification |
| `CoverTitle` | `27.0 / 33.0 pt` | Bold | `#0f172a` | `#f8fafc` | 16:9 cover display headline |
| `Headline` | `19.5 / 23.5 pt` | Bold | `#0f172a` | `#f8fafc` | Letter cover / primary claim |
| `ActionTitle` | `14.5–15.0 / 19.0 pt` | Bold | `#0f172a` | `#f8fafc` | Minto Pyramid slide/section claim |
| `Deck` | `9.8–12.0 / 14–17 pt` | Italic / Reg | `#334155` | `#cbd5e1` | Executive subtitle |
| `Body` | `8.5–9.0 / 13.0 pt` | Regular | `#334155` | `#cbd5e1` | Narrative prose (ragged right) |
| `PullQuote` | `10.8–13.0 / 15–18 pt` | Bold Italic | `#0f2b48` | `#f8fafc` | Floating synthesis anchor |
| `KpiNumber` | `21.0–23.0 / 24–26 pt` | Bold | `#0f2b48` | `#f8fafc` | Primary audited metric |
| `KpiLabel` | `7.2–7.5 / 9.5 pt` | Bold | `#0284c7` | `#38bdf8` | Uppercase KPI header |
| `TableHeader` | `7.0–7.5 / 9.5 pt` | Bold | `#0f2b48` | `#38bdf8` | Tufte ledger header |
| `TableCell` | `7.5–8.0 / 10.5 pt` | Regular | `#0f172a` | `#f8fafc` | Tabular data (right-aligned nums) |
| `Caption` | `7.3 / 10.0 pt` | Italic | `#64748b` | `#94a3b8` | Source, sample size (`N`), & Rule 5 notes |

### Micro-Typography Guardrails
- Always use non-breaking spaces (`&nbsp;`) before compact units (`6.94&nbsp;t`, `429.98&nbsp;ppm`) inside narrow sidebars so units never orphan onto a new line.
- Keep `>= 4–5 pt` breathing room between a ledger's bottom rule and its footnote caption.
