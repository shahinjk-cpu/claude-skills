---
name: react-bits
description: Production-grade animated, interactive, and customizable React & Next.js components library (215+ components: Text Animations, Backgrounds, Cursor Effects, Cards, Interactive UI). Use when creating animated web interfaces, hero sections, interactive cards, particle backgrounds, and micro-interactions in React/Next.js with Tailwind or pure CSS.
---

# React Bits Component Library Skill

`react-bits` is the largest open-source library of animated, interactive, and customizable components for React and Next.js, built for human developers and AI coding agents.

## Core Capabilities & Categories

### 1. Text Animations
- **SplitText**: Word and character split animations with GSAP/Framer Motion.
- **BlurText**: Progressive blur and letter-by-letter reveal.
- **ShinyText**: Shimmering reflective gradient text effect.
- **DecryptedText**: Cyberpunk / matrix style character decoding effect.
- **TrueFocus**: Interactive focus magnification on hover/words.
- **VariableProximity**: Variable font weight / optical size shifts based on cursor proximity.
- **CircularText**: Rotating curved typography around an axis.
- **CountUp**: Smooth statistical number incrementation.

### 2. Backgrounds & Canvas Shaders
- **Aurora**: Fluid Northern Lights color wave gradient.
- **LiquidChrome**: Raymarched metallic fluid reflective shader.
- **Hyperspeed**: Star-wars style lightspeed road/particle tunnel.
- **Particles**: Interactive physics-enabled floating particle canvas.
- **Waves**: 3D geometric wave grid with noise algorithms.
- **Iridescence**: Holographic, pearlescent color shift shader.
- **Ballpit**: Matter.js / physics-driven bouncing spheres in 3D canvas.
- **GridDistortion**: Cursor-reactive warping grid matrix.
- **Threads**: Silky flowing sinuous ribbons.

### 3. Components & Cards
- **TiltedCard**: 3D gyroscope/cursor parallax tilt with specular sheen.
- **SpotlightCard**: Radial light beam tracing the cursor perimeter.
- **FlowingMenu**: Expanding editorial marquee navigation strip.
- **ElasticSlider**: Physics-based rubber-band drag slider.
- **RollingGallery**: 3D cylindrical carousel rotation.
- **DecayCard**: Grunge/burn peel-away interactive card.

### 4. Cursor & Micro-Interactions
- **SplashCursor**: Fluid simulation following mouse movements with dye injection.
- **BlobCursor**: Gooey SVG filter trail tracking the pointer.
- **Magnet**: Elastic magnetic snap to buttons and interactive targets.
- **StarBorder**: Moving stellar border trail encircling buttons.

## Implementation Guidelines

1. **Framework Flavors**:
   - Every component is available in **TypeScript** (`ts-tailwind` / `ts-default`) and **JavaScript** (`tailwind` / `css`).
   - Prefer Tailwind CSS classes (`@tailwindcss/vite` or Tailwind v4/v3) where possible.
2. **Dependencies**:
   - Many effects use lightweight libraries: `framer-motion` (or `motion`), `three`, `@react-spring/web`, or `gl-matrix`.
   - Always verify and declare any required peer dependencies.
3. **Performance First**:
   - Canvas backgrounds must use `requestAnimationFrame` with delta time.
   - Clean up event listeners (`mousemove`, `resize`, `visibilitychange`) inside `useEffect` return cleanup hooks.
   - Respect `prefers-reduced-motion` media queries.
