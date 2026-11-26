---
id: ui-reference-accessibility
name: "1:1 Reference UI, Mobile & Gamepad UX"
category: UI
tagline: "Pixel-faithful screenshot/Figma-to-Studio layouts, anti-slop geometry tokens, StudioProbe bounds auditing, mobile safe areas & gamepad focus."
enabled: true
mode: auto
builtin: true
---
# 1:1 Reference UI, Mobile & Gamepad UX Playbook

Follow this blueprint when recreating UI from a screenshot/reference image, matching a specific Roblox genre look, or polishing UI for desktop, phone, and console/gamepad players.

## 1. Measure the Reference & Reject AI Slop
Before building any UI, call `get_style_guide` (pass the target genre or inspect all 12) so every panel uses authentic geometry rather than generic rounded gradient cards:
- **Match Reference Geometry First:** Measure aspect ratios, panel hierarchy, border treatment, corner radii (`0–4px` sharp classic vs `12–18px` simulator/RPG), header rails, and column rhythm from the user's prompt or reference screenshot.
- **Anti-Slop Rules:**
  - Never default to blurry uniform dark pills for a classic, horror, RPG, or pixel interface.
  - Use explicit semantic design tokens in `ReplicatedStorage.Shared.Theme` (palette, stroke thickness, font family, spacing scale, corner radius).
  - Keep ALL text and buttons native, selectable, and localized-safe (`TextLabel`, `TextButton`, `UIListLayout`, `UIGridLayout`, `UIPadding`, `UISizeConstraint`) — never flatten interactive UI into static image blobs.
  - Pair icon families consistently (uniform stroke weight & perspective across all HUD icons).

## 2. Mobile Safe Areas & Zero-Clip Responsive Layout
- **Safe Areas:** Set `ScreenGui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets` (or `DeviceSafeInsets` for HUD edges) and keep critical buttons clear of the top-bar Roblox controls and mobile thumbsticks.
- **Minimum Touch Targets:** Interactive mobile buttons MUST measure at least `44x44` offset pixels at phone viewport resolutions (`640x360`–`844x390`).
- **Text Clipping Prevention:** Never size tight buttons to exact fixed text width; apply `UIPadding` + generous horizontal room or `AutomaticSize = Enum.AutomaticSize.X` (within `UISizeConstraint`), and avoid `TextScaled` everywhere on long paragraphs where `TextWrapped = true` + scrollable `ScrollingFrame` (`AutomaticCanvasSize = Enum.AutomaticSize.Y`) is cleaner.
- **Modal Transitions:** Pull `ModalTransition` + `ViewportFit` + `HealthBinding` via `get_luau_module`. Honor `UserGameSettings.ReducedMotion` or keep modal opens snappy (`0.16s–0.22s`), and destroy/unbind listeners cleanly when screens unmount.

## 3. Gamepad, Keyboard & Live `StudioProbe` Verification
- **Focus & Selection:** Group modal buttons cleanly (`GuiObject.SelectionGroup = true`), wire `GuiService.SelectedObject` when a modal opens, save the previous focus to restore on close, and bind a clear Cancel/Back input (`Enum.KeyCode.ButtonB` / `Escape`) with `ContextActionService` (unbound cleanly on close so underlying world actions never leak through).
- **Live Layout Audit:** Pull `StudioProbe` via `get_luau_module` and run it in `execute_luau` on `StarterGui` (or `LocalPlayer.PlayerGui` during Play) to inspect every `GuiObject`'s `AbsolutePosition`, `AbsoluteSize`, `TextFits`, `TextBounds`, and `ScreenInsets` — fix any `textFits == false` or off-screen frame before declaring UI done.

