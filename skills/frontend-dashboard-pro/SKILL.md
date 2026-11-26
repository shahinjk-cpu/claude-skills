---
name: frontend-dashboard-pro
description: >-
  Designs and builds high-craft websites, landing pages, web apps, and interactive
  analytics dashboards without generic "AI slop" aesthetics. Integrates Taste Skill (Anti-Slop design contract)
  and React Bits animated UI components. Use when creating or styling websites, UI/UX layouts, admin panels,
  BI dashboards, charts, data tables, React/Next.js/Tailwind/Flutter web interfaces, or converting designs into code.
---

# Frontend Design, Interactive Dashboard & Taste Pro

Inspired by **`Leonxlnx/taste-skill`** (Anti-Slop Design Framework), **`DavidHDev/react-bits`** (`reactbits.dev`), `shadcn/ui`, and modern BI analytics platforms.

---

## 1. Taste Anti-"AI Slop" Design Contract

AI agents frequently produce generic, template-looking landing pages (centered heroes, purple-blue gradient blobs, plain Inter font, identical 3-column cards). Enforce the **Taste Design Contract** on every frontend build:

### A. Layout & Spatial Architecture
- **Ban the Centered Hero Cliché**: Break monotony with asymmetric layouts, editorial grid offsets, split-screen hero sections, or full-bleed interactive previews.
- **Bento Grids with Variance**: Never create 3 identical square cards. Vary aspect ratios ($2\times1$, $1\times2$, large focal card alongside compact metric tiles).
- **Surface Elevation via Subtle Borders**: Never rely on heavy, fuzzy drop shadows. Use 1px crisp borders (`border border-white/10` in dark mode, `border border-black/[0.08]` in light mode) combined with slight background elevation (`bg-zinc-950 -> bg-zinc-900/50`).

### B. Typography & Letter-Spacing System
- **Display Contrasts**: Pair an expressive display typeface (`Space Grotesk`, `Plus Jakarta Sans`, `Instrument Serif`, `Clash Display`, `Outfit`) with a neutral body font (`Geist`, `Inter`, `DM Sans`).
- **Strict Letter-Spacing**:
  - Tighten headings: `tracking-tighter` or `tracking-tight` on all large headings (`text-4xl` to `text-7xl`).
  - Loosen small uppercase labels: `text-xs font-semibold uppercase tracking-widest text-muted-foreground`.
- **Tabular Numerics**: Always apply `font-variant-numeric: tabular-nums` (`tabular-nums font-mono`) to dashboard statistics, pricing tables, timers, and financial figures so numbers align cleanly.

### C. Physical Motion & Micro-Interactions (Framer Motion)
- **Spring Physics Over Linear Easing**: Always use spring animations (`type: "spring", stiffness: 350, damping: 30`) instead of robotic `ease-in-out`.
- **Active & Hover States**: Every interactive button, pill, or card must provide instant visual feedback (subtle scale `hover:scale-[1.02] active:scale-[0.98]`, brightness highlight, or border illumination).

---

## 2. React Bits (`reactbits.dev`) Component Primitives

Incorporate production-tested animated primitives from React Bits for maximum aesthetic polish:

### A. Interactive Animated Backgrounds
- **Spotlight Background**: Radial spotlight tracking the cursor across a dark grid canvas.
- **Aurora Gradient**: Subtle, slow-shifting organic color waves beneath transparent glassmorphic cards.
- **Particles / Hyperspeed**: Dynamic canvas background for tech, gaming, or high-velocity SaaS heroes.

### B. Expressive Text Animations
- **Decrypted / Scramble Text**: Cyberpunk / terminal reveal effect for headlines or technical metrics.
- **Split / Blur-in Text**: Staggered character or word reveal using Framer Motion springs upon page load.
- **Shiny / Metallic Text**: Gradient sweep animation (`bg-clip-text text-transparent bg-gradient-to-r animate-shimmer`) for premium badges.

### C. 3D & Tactile Components
- **Tilted Parallax Card**: 3D card rotating slightly toward mouse position using CSS 3D transforms (`perspective: 1000px, rotateX, rotateY`).
- **Magnetic Button**: Interactive CTA button physically attracted toward cursor coordinates on hover.
- **Glassmorphic Surface**: `backdrop-blur-xl bg-white/[0.04] border border-white/10 shadow-2xl`.

---

## 3. Analytics & Admin Dashboard Architecture

When building a dashboard, structure the layout into 4 clear zones:

1. **Top Command Bar & Global Filters**:
   - Breadcrumbs, date-range picker (Today, 7D, 30D, Custom), environment/segment filter, and quick search (`Ctrl+K`).
2. **KPI Summary Strip (3–4 Cards Max per Row)**:
   - Each KPI card shows: **Metric Label**, **Primary Value** (large, tabular-nums), **Delta Badge** (`+14.2% vs last period` with semantic green/red/amber color), and an optional micro-sparkline.
3. **Primary Visual Analytics Grid**:
   - Match chart type to data intent:
     - *Time-series trend* -> Area or Line chart with custom tooltip and crosshair.
     - *Category comparison* -> Horizontal Bar chart (easier to read labels than vertical bars).
     - *Part-to-whole* -> Stacked bar or compact Donut chart with center total (max 5 slices).
     - *Funnel / Pipeline* -> Step conversion bar with drop-off percentages.
4. **Actionable Data Table / Detail View**:
   - Include search, status badge filters, column sorting, pagination, empty states, loading skeletons, and row-level quick actions.

---

## 4. Responsive & Accessibility Checklist
- Test layout at `375px` (Mobile), `768px` (Tablet), and `1440px` (Desktop).
- Collapse sidebars into a drawer on mobile (`<768px`) and convert wide tables into responsive cards or horizontal scroll containers with sticky first columns.
- Ensure WCAG AA contrast ratios (`4.5:1` for normal text) and full keyboard navigation.
