---
id: maps-biomes-atmosphere
name: "1:1 Map Design, Landmarks & Biomes"
category: Building
tagline: "Human-scale stud ratios, landmark-first sightlines, 3-lane combat flow, Terrain+Part blending, and signature biome lighting recipes."
enabled: true
mode: auto
builtin: true
---
# 1:1 Map Design, Landmarks & Biomes Playbook

Use this playbook alongside `building-architecture` whenever recreating an iconic game map 1:1 or designing playable arenas, hubs, horror corridors, cities, or multi-biome worlds.

## 1. Exact Roblox Stud Scale Ratios (Never Guess Proportions!)
- **Default R15/R6 Character:** `~5.5` studs tall, `~2` studs wide.
- **Doorways & Corridors:** Doorways `6–8` studs wide × `8–10` studs tall; interior hallways `10–14` studs wide × `12–16` studs tall so the third-person camera never feels cramped.
- **Stairs & Cover:** Step rise `0.6–1.0` studs, step depth `1.5–2.0` studs; waist cover `3.5–4.2` studs tall; full cover `6.5–8.0` studs tall.
- **Arena & Sightline Scale:** Duel/battlegrounds courtyard `160–280` studs across; city block `120×120` studs; parkour/obby jump gaps `10–16` studs horizontal, `4–6` studs vertical.

## 2. Landmark-First Sightlines & Navigation Flow
- **Hero Centerpiece First:** Place a tall, unmistakable focal landmark visible immediately from `SpawnLocation` (e.g., shattered monument, neon tower, giant tree, clocktower, sunken shrine) so players always know where they are.
- **3-Lane & Elevation Readability:** Avoid flat empty rectangles — carve height tiers (bridges, sunken pits, rooftops, stairs/ramps), clear choke points, and flanking routes with distinct color/material cues per zone.
- **Environmental Storytelling:** Place grounded prop clusters (crates, streetlamps, ruined pillars, cables, benches, glowing runes, signage) at corners and wall bases, never floating in mid-air (`GetBoundingBox()` bottom flush with floor Y).

## 3. Biome & Atmosphere Presets (Lighting + Terrain)
- **Golden Sunset / City Horizon:** `ClockTime = 17.6`, warm `ColorShift_Top = (255, 196, 140)`, `Atmosphere.Density = 0.28`, `Haze = 2.2`, `Glare = 0.35`, `Bloom.Intensity = 0.25`.
- **Anime Battlegrounds Daylight:** `ClockTime = 14.5`, crisp `Future` shadows, vibrant `ColorCorrection.Saturation = 0.14`, `Atmosphere.Density = 0.22`, subtle rim sun shafts.
- **Doors / Horror Corridor:** `ClockTime = 0`, `Brightness = 0.4`, `Ambient = (18, 20, 28)`, `Atmosphere.Density = 0.55`, `Haze = 4`, warm flickering sconce `PointLight` pools (`Range = 18`).
- **Cyberpunk / Sci-Fi Neon:** `ClockTime = 21.5`, deep navy `Fog/Atmosphere`, wet-look `Reflectance = 0.25` asphalt/metal floors, controlled cyan/magenta `Neon` trim (`Threshold = 1.25`).

