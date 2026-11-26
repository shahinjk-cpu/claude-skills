---
name: web-app-asset-generator
description: >-
  Generates and optimizes web and mobile application assets including SVG icons,
  complete favicon suites, splash screens, social share og:images, and UI graphics.
  Inspired by alonw0/web-asset-generator and canvas-design. Use when preparing
  assets for a website, game, or mobile app launch.
---

# Web, Mobile & Game Asset Generator

Inspired by `alonw0/web-asset-generator` and `anthropics/canvas-design`.

## 1. Asset Suite Checklist
When preparing a website or app for launch, produce the full asset suite:
1. **Favicon Suite**:
   - `favicon.ico` (multi-resolution 16x16, 32x32, 48x48).
   - `favicon.svg` (crisp scalable vector favicon with dark/light mode `prefers-color-scheme`).
   - `apple-touch-icon.png` (180x180 with 15% safe padding).
   - `site.webmanifest` with `icon-192.png` and `icon-512.png`.
2. **Social Share (Open Graph & Twitter)**:
   - `og:image` dimensions: `1200x630px` (aspect ratio 1.91:1).
   - Clean, high-contrast title, subtitle, logo, and product preview badge.
3. **Mobile & Game Sprites / App Icons**:
   - Square `1024x1024px` base master icon with 0 corner radius (stores add rounded corners automatically).
   - Responsive vector SVG icons with scalable stroke widths.
