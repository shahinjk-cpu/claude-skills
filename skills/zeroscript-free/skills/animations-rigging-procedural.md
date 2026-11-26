---
id: animations-rigging-procedural
name: "AAA Animations, Motor6D & Procedural Motion"
category: Animations
tagline: "Code-authored KeyframeSequence+Pose animations playable live in Studio, 60fps Motor6D.Transform spring motion, IK, viewmodels, and 4-phase combat choreography."
enabled: true
mode: auto
builtin: true
---
# AAA Animations, Motor6D & Procedural Motion Playbook

Use this playbook whenever the user asks for animations, character movesets, sword/weapon swings, idle/walk/run cycles, FPS viewmodels, custom boss/pet rigs, doors/chests, or smooth procedural character motion in Roblox Studio.

## 1. Live Studio `KeyframeSequence` Authoring (Plays Immediately Without External Uploads!)
Because external `rbxassetid://` animations cannot be uploaded from Luau, author **real `KeyframeSequence` + `Pose` hierarchies** directly inside `ReplicatedStorage.Animations` via `execute_luau` and register them at runtime with `KeyframeSequenceProvider`:

```lua
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")

-- Helper to register and play a KeyframeSequence stored in ReplicatedStorage.Animations
local function playCodeSequence(humanoid: Humanoid, seq: KeyframeSequence, priority: Enum.AnimationPriority, fadeTime: number?)
    local animator = humanoid:FindFirstChildOfClass("Animator") or Instance.new("Animator", humanoid)
    local animId = KeyframeSequenceProvider:RegisterKeyframeSequence(seq)
    local anim = Instance.new("Animation")
    anim.AnimationId = animId
    local track = animator:LoadAnimation(anim)
    track.Priority = priority
    track:Play(fadeTime or 0.1)
    return track
end
```

### Exact `Pose` Tree Rules (R6 vs R15)
- A `KeyframeSequence` contains `Keyframe` children (`.Time = seconds`), and each `Keyframe` contains a root `Pose` named `"HumanoidRootPart"` whose children mirror the rig's `Motor6D.Part1` names!
- **R6 Pose Hierarchy:** `HumanoidRootPart` → `Torso` → (`Head`, `Left Arm`, `Right Arm`, `Left Leg`, `Right Leg`).
- **R15 Pose Hierarchy:** `HumanoidRootPart` → `LowerTorso` → `UpperTorso` → (`Head`, `LeftUpperArm` → `LeftLowerArm` → `LeftHand`, `RightUpperArm` → `RightLowerArm` → `RightHand`) and `LowerTorso` → (`LeftUpperLeg` → `LeftLowerLeg` → `LeftFoot`, `RightUpperLeg` → `RightLowerLeg` → `RightFoot`).
- Set `pose.CFrame = CFrame.Angles(...)`, `pose.EasingStyle = Enum.PoseEasingStyle.Cubic` (or `Quad`/`Back`), `pose.EasingDirection = Enum.PoseEasingDirection.Out`, `pose.Weight = 1`.
- Attach `KeyframeMarker` instances inside hit/step `Keyframe`s and listen via `track:GetMarkerReachedSignal("HitFrame"):Connect(...)` so VFX, sound, and hitboxes fire on the **exact strike frame**!

## 2. 60fps Procedural `Motor6D.Transform` & Critically Damped Springs
For ultra-snappy responsive motion (weapon swings, sprint lean, jump/land squash, hit flinch, head/torso aim tracking, cape/tail lag, viewmodel sway), drive `Motor6D.Transform` in `RunService.Stepped` (the exact physics/animation step before rendering):
- **NEVER overwrite `Motor6D.C0` every frame for character limbs** if default `Animate` is running — layer or drive `motor.Transform` in `RunService.Stepped` (`RunService.RenderStepped` for FPS viewmodels).
- **Use a critically damped Spring module** (`stiffness` `140–280`, `damping` `18–28`):
  ```lua
  -- Spring step: acc = -k * (pos - target) - d * vel
  -- Produces organic overshoot, settle, and zero robotic linear interpolation!
  ```
- **Dynamic Locomotion Layering:**
  - **Sprint Lean:** Tilt `RootJoint` / `LowerTorso` forward `6°–10°` proportional to horizontal speed and bank `±6°` into turns using `rootPart.CFrame.RightVector:Dot(moveDir)`.
  - **Idle Breathing:** Subtle sinusoidal chest rise + shoulder counter-roll (`sin(t * 2.1)`) so characters feel alive when standing still.
  - **Landing Squash:** Detect `Humanoid.StateChanged` (`Landed`), punch vertical spring down and rebound smoothly.
  - **Look/Aim Tracking:** Rotate `Neck` and `Waist` yaw/pitch smoothly toward camera/target look vector clamped to `±35°`.

## 3. The 4-Phase AAA Combat & Action Choreography
Every attack, cast, dash, or interaction MUST follow 4 distinct timing beats (never a flat `0.2s` arm rotation):
1. **Anticipation (`0.08s–0.14s`):** Pull torso back, raise/cock weapon (`EasingStyle.Quad, In`), slight crouch — gives readable telegraphing.
2. **Active Snap (`0.05s–0.09s`):** Fast explosive slash/thrust across torso (`EasingStyle.Cubic, Out` or `Exponential`), fire `HitFrame` marker, spawn trail/slash arc + hitstop (`0.05s` pause via `track:AdjustSpeed(0)` then restore `1`).
3. **Follow-Through (`0.08s–0.14s`):** Slight overshoot past the target angle (`+8°–15°`) while torso twists into the strike.
4. **Recovery Settle (`0.18s–0.28s`):** Smooth blend back to combat idle (`track:Stop(0.22)` or spring return).

## 4. Custom Rigs, `Motor6D` Pivots & `IKControl`
- When rigging custom weapons, tools, chests, doors, or bosses: weld/joint with `Motor6D` (`Part0` = parent/hand, `Part1` = weapon/limb, `C0` = pivot offset on `Part0`, `C1` = pivot offset on `Part1`), disable `CanCollide` and `Anchored = false` on animated child parts (only root/base anchored if static prop).
- For foot planting, reaching, or aiming arms at live targets on R15 rigs, attach an `IKControl` (`Type = Enum.IKControlType.Position` or `Transform`, `ChainRoot`, `EndEffector`, `Target`, `Weight`, `SmoothTime = 0.08`).
- **FPS Viewmodels:** Clone lightweight arms + weapon model under `workspace.CurrentCamera`, update root `CFrame = camera.CFrame * swayOffset * walkBob * recoilSpring * adsLerp` in `RenderStepped`, and drive reload/inspect keyframes cleanly on the viewmodel `Animator`.

