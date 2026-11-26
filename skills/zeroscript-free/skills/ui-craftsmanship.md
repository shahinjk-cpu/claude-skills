---
id: ui-craftsmanship
name: "UI & HUD Craftsmanship"
category: UI
tagline: "AAA Roblox UI: obsidian/glass design tokens, responsive Scale layouts, typography hierarchy, and TweenService micro-interactions."
enabled: true
mode: auto
builtin: true
---
# AAA Roblox UI & HUD Craftsmanship Playbook

Follow these production engineering rules whenever building or upgrading any Roblox `ScreenGui`, HUD, shop, inventory, dialog, notification, or menu.

## 1. Anti-Default Discipline (Never Ship Amateur UI)
- NEVER ship flat `Color3.fromRGB(163, 162, 165)` / `(45, 45, 45)` unstyled boxes with raw borders (`BorderSizePixel = 1`). Always set `BorderSizePixel = 0` and build elevation through layered corners, hairline strokes, gradients, and padding.
- NEVER place raw pixel `Offset` positions that break on mobile, console, or ultrawide displays. Use `UDim2.fromScale` + `UIAspectRatioConstraint` + `UISizeConstraint` + `UIPadding` + `UIListLayout`/`UIGridLayout`.
- NEVER use raw `TextScaled = true` alone on mismatched text blocks (it produces inconsistent, giant or microscopic text). Use intentional `TextSize` with `UITextSizeConstraint` (`MinTextSize`/`MaxTextSize`) or crisp scale typography paired with `AutomaticSize` where appropriate.
- ALWAYS configure the root `ScreenGui` properly:
  - `ResetOnSpawn = false` (unless explicitly death-scoped)
  - `ZIndexBehavior = Enum.ZIndexBehavior.Sibling`
  - `IgnoreGuiInset = true` for full-screen overlays, dimmed backdrops, or top-bar aligned HUDs (respecting safe topbar height `~58px` / `0.08` scale when placing interactive widgets at top-left/top-center).

## 2. Cohesive Design Tokens & Surface Tiers
Choose ONE cohesive theme matching the game's genre (or ask/infer cleanly) and reuse consistent tokens across every panel:
- **Obsidian / Tactical Dark (default for modern RPG/Simulator/Sci-Fi):**
  - Canvas backdrop: `Color3.fromRGB(10, 11, 15)` (`BackgroundTransparency = 0.08–0.18`)
  - Elevated card surface: `Color3.fromRGB(18, 20, 26)`
  - Interactive pill/slot: `Color3.fromRGB(28, 31, 40)`
  - Hairline stroke: `UIStroke` with `Color = Color3.fromRGB(255, 255, 255)`, `Thickness = 1`, `Transparency = 0.86`, `ApplyStrokeMode = Enum.ApplyStrokeMode.Border`
  - Text primary: `Color3.fromRGB(244, 245, 248)`, secondary: `Color3.fromRGB(154, 160, 175)`
  - Single vibrant accent (e.g., Cyan `#38BDF8`, Emerald `#34D399`, Amber `#FBBF24`, or Indigo `#818CF8`) reserved strictly for CTAs, active tabs, progress bars, and highlights.
- **Depth & Polish Helpers:**
  - Add subtle vertical `UIGradient` (`Rotation = 90`, slight brightness shift `0.95 -> 1.05` or `Transparency` ramp) on buttons, headers, and progress fills so surfaces look lit rather than dead flat.
  - Use `UICorner` with consistent radii (`UDim.new(0, 14)` outer cards, `UDim.new(0, 10)` inner cards/buttons, `UDim.new(1, 0)` pills/badges).
  - Add a subtle soft drop shadow frame behind floating modals (`ImageLabel` 9-slice or layered low-opacity dark backplate) to separate foreground from world geometry.

## 3. Typography & Visual Hierarchy
- Explicitly set `FontFace` (never leave `Legacy` or default `SourceSans` everywhere):
  - Clean Modern / Sci-Fi / Tactical: `Font.fromEnum(Enum.Font.BuilderSans)` or `Montserrat` / `GothamSSm` with distinct `Enum.FontWeight.Bold` (headers), `SemiBold` (buttons/labels), `Medium` (body), and `RobotoMono` for live numbers, currencies, timers, and keybind chips.
  - Stylized / Cartoon / Tycoon: `FredokaOne` / `LuckiestGuy` / `GothamSSm` with clean `UIStroke` (`Thickness = 1.5–2`, dark tint) for readable contrast over bright scenes.
- Always pad text containers (`UIPadding` 10–18px or `0.04` scale) so letters never touch rounded borders.
- Format numbers cleanly (`1,250`, `12.4K`, `02:15`) inside HUD counters and add `TextTruncate = Enum.TextTruncate.AtEnd` on dynamic names.

## 4. Responsive Layout Patterns
- Prefer container-driven flow:
  - Header bar + scrollable `ScrollingFrame` body (`AutomaticCanvasSize = Enum.AutomaticSize.Y`, `CanvasSize = UDim2.new(0, 0, 0, 0)`, `ScrollBarThickness = 4`, `ScrollBarImageTransparency = 0.5`).
  - Use `UIListLayout` / `UIGridLayout` with `Padding = UDim.new(0, 10)` and `SortOrder = Enum.SortOrder.LayoutOrder`, assigning deterministic `LayoutOrder` integers (`1, 2, 3...`) so ordering never jumbles.
  - Keep touch/click targets comfortable (`>= 40px` height or `>= 0.06` screen height) and never stack clickable buttons near Roblox's top-left menu icon or mobile thumbstick zones.

## 5. Juice & Micro-Interactions (Mandatory for Interactive UI)
When creating interactive panels, wire a clean `LocalScript` (built AFTER creating the GUI hierarchy in `Edit` mode, using `:WaitForChild(..., 5)`):
- **CanvasGroup Fade + Scale Pop on Open/Close:**
  - Wrap modals in a `CanvasGroup` (when compatible) or tween container `Position`/`UIScale.Scale` (`0.94 -> 1.0`) with `TweenInfo.new(0.24, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)` while fading `GroupTransparency` `1 -> 0`.
- **Hover & Press Feedback on Every Interactive Button:**
  - `AutoButtonColor = false` so Roblox's ugly default darken doesn't fight custom tweens.
  - On `MouseEnter`: tween `UIScale` to `1.03` and brighten stroke/fill (`TweenInfo.new(0.14, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)`).
  - On `MouseLeave`: tween back to `1.0`.
  - On `MouseButton1Down`: quick squash to `0.96` (`0.08s`); bounce back on `MouseButton1Up`.
- **Smooth Progress Bars & Rolling Counters:**
  - Tween bar `Size` (`UDim2.fromScale(math.clamp(pct, 0, 1), 1)`) smoothly and flash highlight color briefly on gain/damage.

## 6. Build Order & Verification Workflow
1. **Build instances first** cleanly in `StarterGui` using `execute_luau` (helper factory functions for `makeCorner`, `makeStroke`, `makePadding`, `makeGradient`, `makeButton`). Set `Enabled = false` on toggleable modals (keep main HUD `Enabled = true`) or verify visibility in Edit mode cleanly.
2. **Script second** using `multi_edit` (`className: "LocalScript"` inside the `ScreenGui` or `StarterPlayerScripts`) using `WaitForChild(name, 5)`. Never embed long client logic directly in `execute_luau`.
3. **Verify** via `inspect_instance` / `execute_luau` checking that there are zero overlap bugs, valid `LayoutOrder`, `ResetOnSpawn = false`, and clean runtime error-free Play testing if requested.

