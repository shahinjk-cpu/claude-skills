---
id: cutscenes-cinematics
name: "Cutscenes & Camera Choreography"
category: Cutscenes
tagline: "AAA Roblox cutscenes: RenderStep spline cameras, DepthOfField focus pulls, letterbox & skip HUD, actor choreography, and zero camera soft-locks."
enabled: true
mode: auto
builtin: true
---
# AAA Cutscenes & Camera Choreography Playbook

Follow these production patterns whenever creating intro cutscenes, boss reveals, dialogue camera work, victory/ending sequences, or camera flythroughs in Roblox Studio.

## 1. Zero-Softlock Director Architecture
- **Split cleanly:**
  - Build a reusable `ModuleScript` (e.g., `ReplicatedStorage.Modules.CutsceneDirector`) plus a `LocalScript` (in `StarterPlayerScripts` or a dedicated `ScreenGui`) and optional `RemoteEvent` triggers from `ServerScriptService`.
  - **ALWAYS use `multi_edit` (`className: "ModuleScript"` / `"LocalScript"`)** for runtime scripts — never try to run long client camera loops via `execute_luau`!
- **Snapshot & Guaranteed Cleanup (`cleanup()`):**
  - Before changing anything, capture:
    - `prevCameraType = camera.CameraType`
    - `prevSubject = camera.CameraSubject`
    - `prevFOV = camera.FieldOfView`
    - `prevWalkSpeed` / `prevJumpPower` (or `UseJumpPower` / `JumpHeight`)
    - `StarterGui` core states if toggled
  - Bind a single idempotent `cleanup()` function that:
    1. Calls `RunService:UnbindFromRenderStep(BIND_NAME)` inside `pcall`
    2. Restores `CameraType`, `CameraSubject`, `FieldOfView`, and restores/fades out `DepthOfFieldEffect` & letterbox bars
    3. Restores character movement and fires a completion callback/signal
  - Wire cleanup on: normal end, **Skip button click**, `Player.CharacterRemoving`, and active-cutscene cancellation — guaranteeing the player can NEVER get stuck with a frozen camera.

## 2. Cinematic Camera Motion (Never Linear `TweenService` on CFrames Alone)
Raw `TweenService:Create(camera, ..., { CFrame = target })` rotates awkwardly in a straight line and looks robotic. Instead:
- Drive camera updates inside `RunService:BindToRenderStep(BIND_NAME, Enum.RenderPriority.Camera.Value + 1, stepFn)`.
- **Smooth Spline & Orbit Math:**
  - Evaluate **Catmull-Rom splines** (or Cubic Bezier curves) across control waypoints for sweeping crane/dolly arcs, paired with `TweenService:GetValue(alpha, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)` for silky ease-in/ease-out pacing.
  - Interpolate position and look-at target **independently**, building `CFrame.lookAt(camPos, lookTarget)` (with optional smooth roll/dutch tilt `CFrame.Angles(0, 0, roll)`).
  - Layer subtle **handheld / breathing motion** using damped `math.noise(t * 0.7, 1.3)` (`±0.08` studs position / `±0.25°` pitch-yaw) — strongest on tense close-ups, subtle on wide establishing shots.
- **Shot Grammar (Mix 3–4 Distinct Shot Types):**
  1. **Establishing Wide:** Slow crane/sweep, `FOV = 62–70`, shows geography and scale.
  2. **Dolly / Tracking Shot:** Moves parallel to subject/corridor, `FOV = 52–58`.
  3. **Hero Close-Up / Reveal:** Tight `FOV = 36–46` (telephoto compression!) + animated `DepthOfFieldEffect` (`FocusDistance` tracked live to `(camPos - targetPos).Magnitude`, `InFocusRadius = 8–16`, `NearIntensity = 0.25`, `FarIntensity = 0.45`).
  4. **Smooth Return Cut or Blend:** Either crossfade through a quick `0.25s` black fade or ease the camera back behind the player's shoulder before flipping `CameraType = Enum.CameraType.Custom`.

## 3. Cinematic HUD (Letterbox, Fades, Subtitles, Skip)
Create a dedicated `ScreenGui` (`CutsceneGui`, `IgnoreGuiInset = true`, `ResetOnSpawn = false`, `DisplayOrder = 50`):
- **2.35:1 Letterbox Bars:** Top & bottom black frames (`BackgroundColor3 = Color3.new(0,0,0)`), tweened smoothly from `0` to `0.11` screen height (`Quint.Out`, `0.45s`) on start and back out on exit.
- **Full-Screen Fade Curtain:** Black `Frame` (`Size = UDim2.fromScale(1, 1)`, `ZIndex = 10`) for crisp fade-ins (`1 -> 0` transparency) and seamless scene cuts.
- **Subtitle Bar:** Clean centered text near the bottom (`Position = UDim2.fromScale(0.5, 0.85)`, `AnchorPoint = Vector2.new(0.5, 0.5)`) using readable typography (`BuilderSans` / `Montserrat`, subtle `UIStroke` outline for readability over bright terrain), fading in/out per dialogue beat.
- **Skip Affordance:** Unobtrusive bottom-right pill (`Skip [Space]` or clickable button) that fades in after `0.8s` so the user stays in control without cluttering frame 1.

## 4. Beat Timeline, Actor & VFX Synchronization
- Structure cutscenes as a clean **Shot / Beat Table** in Luau:
  ```lua
  {
    duration = 3.2,
    fovStart = 65, fovEnd = 50,
    posPoints = { p0, p1, p2, p3 },
    lookPoints = { l0, l1, l2, l3 },
    easing = Enum.EasingStyle.Sine,
    subtitle = "The ancient gates unlock...",
    onEnter = function() ... end, -- trigger AnimationTrack, ParticleEmitter:Emit(30), Sound:Play()
  }
  ```
- **Animations & Effects:**
  - Load `Animation` tracks onto NPC `Humanoid/Animator` cleanly (`animator:LoadAnimation(anim)`) OR drive procedural `Motor6D.Transform` / model `PivotTo` interpolation for gates, ships, doors, or floating relics.
  - Trigger `Sound` cues (whooshes, swells, footsteps, dialogue chimes) cleanly and fade them down on skip/end rather than cutting abruptly (`TweenService` `Volume -> 0` over `0.25s`).
  - Disable character movement safely during play (`Humanoid.WalkSpeed = 0`, `JumpPower/JumpHeight = 0` or `PlatformStand` where appropriate, restoring exact snapshot values in `cleanup()`).

## 5. Verification Checklist
1. Create any `CutsceneGui` / rig / camera waypoint markers in Edit mode (`execute_luau` or `multi_edit`).
2. Write the `CutsceneDirector` `ModuleScript` and client controller `LocalScript` using `multi_edit`.
3. Verify via `start_stop_play` (`is_start: true`) + `get_console_output` if testing live, checking zero warnings/errors and confirming camera control returns cleanly after playback or skip.

