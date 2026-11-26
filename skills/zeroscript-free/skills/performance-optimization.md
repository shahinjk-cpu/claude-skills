---
id: performance-optimization
name: "Performance, Replication & Mobile Optimization"
category: Optimization
tagline: "Target 60 FPS everywhere: StreamEnabled, Instance/Part pooling, RenderFidelity & CollisionFidelity tuning, central Heartbeat loops, and bandwidth discipline."
enabled: true
mode: auto
builtin: true
---
# AAA Performance, Replication & Mobile Optimization Playbook

Follow these profiling and optimization rules whenever building large worlds, bullet/particle systems, tycoons, or cross-platform Roblox experiences targeting mobile, console, and PC.

## 1. Draw Calls, Collisions & Physics Hygiene
- **Anchor static parts (`Anchored = true`):** Unanchored props wake the physics solver every frame and kill framerate + network bandwidth.
- **Disable unneeded `CanCollide`, `CanTouch`, and `CanQuery`:**
  - Set `CanCollide = false`, `CanTouch = false`, `CanQuery = false` on foliage, trim moldings, neon strips, distant skyline silhouettes, and VFX parts so spatial queries (`Raycast`, `GetPartBoundsInBox`) and character collision broadphases skip them completely!
- **Set `CastShadow = false`** on tiny interior trims, grass blades, glass panes, and small props that add shadow-map pass cost without visible grounding benefit.
- **Mesh Optimization:**
  - Prefer `CollisionFidelity = Enum.CollisionFidelity.Box` or `Hull` on complex meshes (`PreciseConvexDecomposition` only when players must walk INSIDE concave geometry!).
  - Use `RenderFidelity = Enum.RenderFidelity.Automatic` on detailed environmental props so distant models simplify smoothly.

## 2. Streaming, Pooling & Render-Only Effects
- **Enable `Workspace.StreamingEnabled = true`** cleanly on large open worlds, pairing critical spawn/objective anchors with `Model.ModelStreamingMode = Enum.ModelStreamingMode.Persistent` when scripts depend on them immediately, and always guard streamed client lookups with `:WaitForChild(..., timeout)` or `CollectionService:GetInstanceAddedSignal()`.
- **Object Pooling (Zero GC Spikes):**
  - NEVER rapidly `Instance.new` + `:Destroy()` hundreds of bullets, footprints, casings, or damage popups per minute in tight combat.
  - Pool reusable templates inside an off-screen/parked cache (`CFrame = CFrame.new(0, -1e4, 0)`), toggling `Enabled = false` on `ParticleEmitter`s/`Trail`s cleanly across recycles.
- **Keep pure eye-candy client-side:** Server NEVER needs to create visual sparks, shockwave rings, spinning coin animations, or swaying trees — replicate a lightweight event (`effectId`, `cframe`) and render smoothly on each nearby client!

## 3. Central Loops & Script CPU Discipline
- **Single-Loop Entity Systems:** Replace `N` per-coin / per-turret `while task.wait() do` threads with ONE manager table updated in a single `RunService.Heartbeat` (server) or `RunService.RenderStepped` (camera/UI only).
- **Avoid per-frame `GetDescendants()`, `FindFirstChild`, or regex scans:** Cache references once on spawn/`CollectionService` tag add, and store dirty flags cleanly.
- **Tween / UI Optimization:**
  - Avoid animating `UIGradient` / layout-shifting properties on huge nested `ScrollingFrame` hierarchies every frame; prefer moving `Position`/`Scale` transforms (`UIScale`, `CanvasGroup.GroupTransparency`) where Roblox caches geometry cleanly.
  - Cap `TextLabel.MaxVisibleGraphemes` typewriter updates instead of reallocating string slices every frame.

## 4. Network & Memory Leak Checklist
- Group replicated updates (send `{ coins = 500, xp = 120 }` in one delta/attribute pass rather than firing 8 remotes per tick).
- Use `buffer` or compact numeric IDs (`1, 2, 3`) instead of repeating massive dictionary keys in high-frequency snapshots.
- Verify cleanup hooks on `PlayerRemoving`, `CharacterRemoving`, and destroyed models so memory (`Stats:GetTotalMemoryUsageMb()`) stays rock-steady during Play tests.

