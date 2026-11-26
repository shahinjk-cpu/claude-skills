---
id: camera-movement-physics
name: "AAA Movement, Parkour & Camera Feel"
category: Gameplay
tagline: "Coyote time, jump buffering, dashes with i-frames, momentum slides, wall-run/vault raycasts, dynamic FOV kicks, and spring-damped custom cameras."
enabled: true
mode: auto
builtin: true
---
# AAA Movement, Parkour & Camera Feel Playbook

Use this playbook whenever building character controllers, movement tech (dash, double-jump, slide, wall-run, vault, grapple), or custom cameras (over-the-shoulder, shift-lock, lock-on, FPS, top-down) so controls feel crisp and responsive.

## 1. Responsive Platforming & Movement Tech
- **Coyote Time (`0.12s`) & Jump Buffering (`0.12s`):** Track `lastGroundedAt = os.clock()` and `jumpPressedAt = os.clock()` so jumps near ledges or slightly before touching ground ALWAYS register.
- **Crisp Dash (`LinearVelocity`):**
  - Use a temporary `Attachment` + `LinearVelocity` (`VelocityConstraintMode = Enum.VelocityConstraintMode.Vector`, `ForceLimitMode = Enum.ForceLimitMode.PerAxis`, `MaxAxesForce = Vector3.new(1e5, 0, 1e5)` so gravity stays natural) for `0.16s–0.24s` rather than `BodyVelocity` (deprecated).
  - Support 4-way directional dashes relative to camera (`W/A/S/D` or forward fallback), grant short i-frames (`Character:SetAttribute("Invulnerable", true)`), emit dust burst + trail, and clean up via `Debris` / `task.delay`.
- **Momentum Slide & Crouch:** Trigger on `C`/`LeftControl` while sprinting (`speed > 18`), lower `HipHeight` smoothly, boost forward velocity decaying via friction curve, and kick camera offset down by `-1.3` studs.
- **Wall-Run & Vault Raycasts:** Cast short forward + side `Workspace:Raycast` checks (`3.5` studs) with `RaycastParams` filtering out the character; align character tangent to wall normal (`wallNormal:Cross(Vector3.yAxis)`).

## 2. Camera Choreography & Feel
- **Dynamic Speed FOV:** Smoothly spring-lerp `camera.FieldOfView` from `70` (walk) → `80` (sprint) → `86` (dash) and return cleanly on stop (`RunService:BindToRenderStep("ZSCamera", Enum.RenderPriority.Camera.Value + 1, ...)`).
- **Over-the-Shoulder / Shift-Lock Combat Camera:** Offset camera smoothly (`CFrame.new(1.8, 0.4, 0)`), clamp pitch `[-70°, 75°]`, and run a spherecast/raycast wall-clip check so the camera never clips inside walls.
- **Target Lock-On:** Find nearest visible enemy in cone, smoothly slerp camera look toward midpoint `(playerPos + targetPos * 0.65)`, and display a world-space `BillboardGui` reticle that scales on lock.
- **Trauma Shake & Recoil:** Use squared trauma (`shake = trauma^2`) with smooth decay (`trauma = math.max(0, trauma - dt * 2.4)`) so explosions, parries, and gunshots punch cleanly without motion sickness.

