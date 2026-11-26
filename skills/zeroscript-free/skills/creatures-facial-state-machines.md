---
id: creatures-facial-state-machines
name: "Creature Gaits, Facial Rigs & Anim State Machines"
category: Animations
tagline: "Priority-tiered Animator state machines, contact-first quadruped/winged creature gaits, RigMap bone binding & Dynamic Head FaceControls."
enabled: true
mode: auto
builtin: true
---
# Creature Gaits, Facial Rigs & Anim State Machines Playbook

Use this playbook alongside `animations-rigging-procedural` when building clean Animator state machines, quadruped/winged/tailed monster rigs, or Dynamic Head facial expressions directly in Roblox Studio.

## 1. Explicit Animation State Machine Design
Never scatter disconnected `track:Play()` calls across scripts. Build a dedicated `AnimStateController` backed by `CleanupScope` and `RigMap` (available via `get_luau_module`):
- **State Table & Priorities:**
  1. `Locomotion` (`Enum.AnimationPriority.Core` / `Movement`): `Idle`, `Walk`, `Run`, `Jump`, `Fall`, `Swim`, `Climb`.
  2. `Overlay` (`Enum.AnimationPriority.Action`): Upper-body aim, block hold, shield raise, reload (leave lower-body joints unkeyed or procedurally blended so legs keep running).
  3. `CommittedAction` (`Enum.AnimationPriority.Action2`–`Action3`): Attacks, dashes, emotes, skills — sets lock/cancel guards and listens to `KeyframeReached` / `GetMarkerReachedSignal` (cosmetic VFX/SFX only; server owns hit timing via `AttackWindow`).
  4. `Override` (`Enum.AnimationPriority.Action4`): Stun, hit-react, knockback, death — cleanly fades out active `Action` tracks on entry.
- **No Track Accumulation & Cleanup:** Cache `AnimationTrack` instances once per `Animator`, stop obsolete tracks cleanly instead of leaving zero-weight loops playing, disconnect marker signals with track lifetime (`CleanupScope`), and rebuild cleanly on `CharacterAdded`.

## 2. Contact-First Creature & Monster Animation
- **Joint & Anatomy Resolution:** Always resolve custom creature bones (`Root`, `Spine1..N`, `Neck`, `Head`, `FrontLeftShoulder/Knee/Paw`, `BackLeftHip/Knee/Paw`, `WingLeft/Right`, `Tail1..N`) through `RigMap` rather than assuming R15 names.
- **Anti-Foot-Slide Stride Rule:** Sync limb cycle frequency and stride length to actual `AssemblyLinearVelocity` magnitude (`cycleSpeed = clamp(horizSpeed / strideLength, minRate, maxRate)`). When a limb enters its stance phase, hold planted rotation until push-off so paws/claws never skate across the floor.
- **Creature Secondary Motion:** Drive tail whip lag, spine S-curve sway on turns, neck look-at, and wingtip follow-through procedurally with `CriticalSpring` on `Motor6D.Transform` so creatures feel organic even on uneven terrain and sharp turns.

## 3. Dynamic Head Facial Rigging (`FaceControls`)
- **Capability Check First:** Inspect `head:FindFirstChildOfClass("FaceControls")` before driving facial properties — fall back gracefully to decal/UI eye swaps on classic block heads without errors.
- **Subtle Expression Layering:** Drive natural blink pulses (`LeftEyeClosed` / `RightEyeClosed` ~120ms close, randomized `2.8s–5.5s` interval) plus state expressions (battle grimace, happy smile, dialogue mouth beats) smoothly via `CriticalSpring` or short `TweenService` blends rather than snapping 0→1 instantly.
- Never override critical combat readability silhouettes or clip eyes/jaws through head geometry.

