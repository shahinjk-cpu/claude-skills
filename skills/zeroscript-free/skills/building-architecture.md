---
id: building-architecture
name: "3D Building & World Architecture"
category: Building
tagline: "AAA Roblox environment craft: 3-layer silhouette detailing, flush CFrame math, hybrid mesh+kitbashing, PBR palettes, and Future lighting."
enabled: true
mode: auto
builtin: true
---
# AAA 3D Building & World Architecture Playbook

Follow these engineering and art-direction rules whenever building structures, maps, props, interiors, lobbies, or terrain environments in Roblox Studio.

## 1. The 3-Layer Detail Rule (No Boxy "Block + Part" Builds)
Every hero building or landmark MUST have all three structural tiers:
1. **Primary Massing (Silhouette):** Varied footprint (L-shape, stepped wings, towers, overhangs, pitched or gabled roofs — never a bare single rectangle).
2. **Secondary Architecture (Rhythm & Depth):** Plinth/foundation base (`+0.5` to `+1.5` studs proud of walls), vertical pilasters/columns at corners and intervals, window frames with **recessed glass** (`0.25–0.5` studs inset behind trim + sill), door reveals/frames, roof eaves, fascia trim, and cornices.
3. **Tertiary Storytelling (Life & Scale):** Lanterns/sconces, vents, pipes, trims, banners, crates, benches, foliage, railings, and wear variation so the space feels lived-in at player eye level (`~5` studs camera height).

## 2. Exact CFrame & Flush-Alignment Math (Zero Gaps, Zero Z-Fighting)
- **ALWAYS wrap builds in a `Model` with an explicit `PrimaryPart`** (usually a grounded floor slab or footprint center part) and position the build with `model:PivotTo(targetCFrame)`.
- **Build in local space relative to an `originCF`** using `originCF * CFrame.new(x, y, z) * CFrame.Angles(rx, ry, rz)` so every sub-part rotates and translates together cleanly.
- **Prevent Z-fighting and floating seams mathematically:**
  - When stacking part `B` on top of part `A`:
    `B_y = A_y + (A_sizeY * 0.5) + (B_sizeY * 0.5)`
  - When placing trim/wall `B` flush against face `+Z` of `A` (proud by `p` studs):
    `B_z = A_z + (A_sizeZ * 0.5) + (B_sizeZ * 0.5) - embed` (use `embed = 0` or `0.02` when completely proud; never share exact coplanar faces with overlapping surfaces).
  - When framing a recessed window: split the wall around the opening (left pier, right pier, header above, sill below) OR inset the frame proud/flush without overlapping coplanar glass!
- **Part Hygiene:**
  - Set `Anchored = true` on all static architecture.
  - Set `TopSurface = Enum.SurfaceType.Smooth` and `BottomSurface = Enum.SurfaceType.Smooth` on parts (or use a helper `makePart(props)` that defaults `Anchored = true` and `Smooth` surfaces).
  - Disable `CanCollide = false` on tiny decorative trims/foliage/glass lights that shouldn't snag player movement, while keeping walls/floors/stairs solid (`CanCollide = true`).
  - For curved stairs/arches/columns, generate smoothly stepped `WedgePart` / `Cylinder` / `Part` segments via deterministic loops (`for i = 0, steps - 1 do ...`).

## 3. Hybrid Generation Strategy (Know When to Generate vs Kitbash)
- **Use `generate_mesh` or `generate_procedural_model`** for organic, sculpted, or complex hero assets (trees, rocks, statues, vehicles, ornate furniture, foliage, creatures) rather than stacking awkward spheres/cylinders by hand.
  - Remember: `generate_mesh` yields and returns the finished asset; `generate_procedural_model` returns a `generationId` immediately and inserts asynchronously (call `wait_job_finished` if you need to reposition/color/parent the finished asset right away).
- **Use `execute_luau` builders** for crisp architectural structures, modular rooms, roads, bridges, obbies, trims, interiors, and exact spatial layouts where clean dimensions, collision, and alignment matter.

## 4. Color, Material & Tonal Discipline
- **60 / 30 / 10 Palette Rule:**
  - 60% Primary structural material (stone, concrete, plaster, wood siding — low-to-medium saturation).
  - 30% Secondary contrast material (slate roof, dark timber framing, brushed metal beams).
  - 10% Accent / Emissive focal points (`Neon` warm amber/cyan windows, glowing crystals, signage — keep `Neon` subtle or dimmed with dark-warm colors so Bloom doesn't blow out the scene).
- **Avoid "Plastic Monotone":**
  - Pair realistic `Material` enums (`Slate`, `Cobblestone`, `Brick`, `WoodPlanks`, `Concrete`, `Metal`, `SmoothPlastic`, `Fabric`, `Glass`) deliberately.
  - Vary adjacent stone bricks or wooden planks by tiny HSV/RGB jitter (`±4–8` per channel) so tiled walls look handcrafted instead of flat.

## 5. Lighting & Atmosphere Finish
Unless the user explicitly asks to preserve existing lighting untouched, elevate scene presentation by tuning `game:GetService("Lighting")`:
- `Lighting.Technology = Enum.LightingTechnology.Future` (for rich shadows & practical lights).
- `Lighting.GlobalShadows = true`, balanced `ClockTime` (`6.5` golden hour / `14.5` crisp daylight / `20.5` moody evening), subtle warm/cool `OutdoorAmbient` + `Ambient` (never pure black `(0,0,0)` shadows unless horror).
- Add tuned post-processing (updating existing instances if present rather than duplicating):
  - `Atmosphere` (`Density = 0.25–0.38`, soft `Haze`, complementary `Color`/`Decay`)
  - `BloomEffect` (`Intensity = 0.2–0.35`, `Size = 18–24`, `Threshold = 1.1–1.5`)
  - `ColorCorrectionEffect` (`Contrast = 0.05–0.12`, `Saturation = 0.05–0.15`)
- Add practical `PointLight` / `SpotLight` (`Shadows = true`, `Range = 16–32`, warm `255, 195, 130` for lanterns/interiors, cool `120, 200, 255` for sci-fi) inside fixtures.

## 6. Clean Hierarchy & Verification
- Group parts cleanly under named sub-models (`Structure`, `Trim`, `Windows`, `Props`, `Lighting`) inside the parent `Model` in `Workspace`.
- Keep `execute_luau` calls modular (~150–300 lines per chunk if building a huge compound) so Studio's parser never rejects an oversized payload.
- Inspect final bounding box (`model:GetBoundingBox()`) and key child counts before wrapping up.

