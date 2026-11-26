---
id: combat-vfx-gamefeel
name: Combat Systems, VFX & Game Feel
category: Combat & VFX
tagline: "Responsive melee & ranged combat: client prediction + server validation, Workspace:GetPartBoundsInBox hitboxes, hitstop, camera trauma shake, and VFX pools."
enabled: true
mode: auto
builtin: true
---
# AAA Combat Systems, VFX & Game Feel Playbook

Follow these production rules whenever building weapons, abilities, melee combos, projectiles, hitboxes, or combat VFX in Roblox Studio.

## 1. Zero-Lag Client Prediction + Server Authority
- **NEVER run hit visuals from the server only:** Clients see sluggish, laggy swings when SFX/VFX wait for a server round-trip.
  - **Client:** Play swing animation, trail, whoosh SFX, and anticipation flash immediately on input (`LocalScript`), while respecting client-side cooldown hints.
  - **Server (`Script`):** Perform authoritative cooldown checks, stamina/resource checks, target range/angle sanity validation (anti-exploit!), damage math, knockback, and broadcast cosmetic hit confirmations (`HitConfirmed` / `VFXEvent`) to nearby players via `FireAllClients`.
- **Rate-limit remotes:** Track `lastActionAt[player]` with `os.clock()` on the server and discard spam packets (`< cooldown - latencyGrace`) cleanly.

## 2. Clean Spatial Hitboxes (Never Raw `Touched` Alone for Melee)
- Avoid `BasePart.Touched` for sword/punch combos — it misses fast swings, double-fires per limb, and hits dead parts.
- Use **shapecast / spatial query** (`Workspace:GetPartBoundsInBox(hitboxCFrame, hitboxSize, overlapParams)` or `Workspace:Spherecast`) sampled over the active swing frames or along swept arc steps:
  - Build `OverlapParams` with `FilterType = Enum.RaycastFilterType.Exclude` excluding the attacker's character and `VFX` folder.
  - Deduplicate hits per swing by keying on the target `Model`/`Humanoid` (`if hitHumanoids[hum] then continue end`) so multi-limb hits apply damage ONCE.
  - Check `hum.Health > 0` and verify line-of-sight (`Workspace:Raycast`) if walls should block slashes.

## 3. Game Feel & Impact Juice (Hitstop, Knockback, Camera Shake)
Every landed strike should feel weighty without freezing the server:
- **Hitstop (Client / Target):** Briefly freeze swing animation speed (`track:AdjustSpeed(0.05)`) for `0.04–0.07s` on heavy crits (`task.delay(0.055, ...)` restore to `1.0`) while sparks & slash burst play.
- **Trauma-Based Camera Shake (`LocalScript`):** Drive damped rotational + positional offset inside `RunService:BindToRenderStep` using `shake = trauma * trauma` and `math.noise(...)`, decaying `trauma` smoothly over time (never harsh linear offsets).
- **Deterministic Knockback:** Apply brief `LinearVelocity` (`RelativeTo = World`, `MaxForce = math.huge` or scaled by `AssemblyMass * 120`) for `0.14–0.22s` on `HumanoidRootPart`, and destroy/pool cleanly via `Debris` or `task.delay`. Never leave persistent body movers attached!
- **Floating Damage Indicators (`BillboardGui`):** Spawn compact upward-drifting, easing damage numbers (`24`, `CRIT 68!`) client-side with `AlwaysOnTop = false` or subtle `MaxDistance = 80` so fights stay legible without HUD clutter.

## 4. Particle & Projectile Hygiene
- **Emit bursts deliberately:** Use `ParticleEmitter.Rate = 0` for impact sparks/blood/shockwaves and trigger crisp bursts via `emitter:Emit(count)` on a short-lived anchored attachment inside `Workspace.VFX`, cleaned up after `ParticleEmitter.Lifetime.Max`.
- **Mesh/Part Projectiles:** Simulate fast bolts/fireballs with per-frame stepped raycasts (`prevPos -> nextPos` on `RunService.Heartbeat`) instead of relying on unstable physics velocity, firing impact VFX at `rayResult.Position` aligned with `CFrame.lookAt(pos, pos + rayResult.Normal)`.
- **Combo Windows & Input Buffering:** Support `M1` 3–4 hit chains with clear combo reset timers (`~0.9s`), subtle escalation on the final finisher (`1.4x` damage + wider arc + stronger knockback), and an input buffer (`0.15s`) so slightly early clicks chain smoothly.

## 5. Build & Verification Checklist
1. Create hitboxes/VFX template assets and `RemoteEvent`s (`ReplicatedStorage.Remotes.Combat`) cleanly in Edit mode via `execute_luau`.
2. Author modular server handler + client controller scripts via `multi_edit` (`WaitForChild(..., 5)` on all required remotes/folders).
3. Verify cooldown enforcement, zero duplicate hit-table leaks (`PlayerRemoving` cleanup!), and clean Play-mode console output.
