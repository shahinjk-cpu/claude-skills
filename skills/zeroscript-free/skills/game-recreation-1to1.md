---
id: game-recreation-1to1
name: "1:1 Game Recreation & Clone Architect"
category: Game Cloning
tagline: "Deconstruct any reference game into a 1:1 playable vertical slice: exact core loop, feel math, map scale, HUD language, and playtest verification."
enabled: true
mode: auto
builtin: true
---
# 1:1 Game Recreation & Clone Architect Playbook

Follow this engineering blueprint whenever the user asks to recreate, clone, or build a "1:1" version of an existing Roblox or non-Roblox game (e.g., Battlegrounds, Doors, Brookhaven, BedWars, Tower Defense, Blox Fruits, Obby, FPS, Pet Simulator, Horror, Tycoon).

## 1. The 6-Layer 1:1 Deconstruction Protocol
Before writing a single line of code, map the target game across **all six fidelity layers** so nothing feels generic or half-baked:
1. **Core Loop & State Machine:** Exact round/match/progression lifecycle (`Lobby -> Intermission -> Active -> SuddenDeath/Boss -> Results -> Reset`), win/loss triggers, and respawn rules.
2. **Exact Feel Numbers:** WalkSpeed, JumpPower/JumpHeight, dash distance & i-frame duration, M1 combo timings (`0.28s–0.42s`), ability cooldowns, recoil/spread, and knockback impulses.
3. **Camera & Perspective:** Exact FOV (`70`–`82`), camera offset (`Vector3.new(1.8, 0.5, 0)` for OTS, shift-lock vs top-down vs FPS viewmodel), sprint FOV kick, and trauma shake.
4. **Iconic Map & Landmarks:** Exact spatial scale (`5.5` stud character height), signature color palette, lighting mood (`ClockTime`, `Atmosphere`, `Bloom`, `ColorCorrection`), and recognizable centerpiece geometry.
5. **1:1 UI & Visual Language:** Match the target game's HUD layout (hotbar slots, health/stamina bar geometry, killfeed, round timer pill, shop modal), typography (`GothamBold`/`BuilderSans`), corner radii, stroke accents, and tween pop.
6. **Audio/VFX Juice:** Hitstop (`0.04s–0.07s`), burst particles, trails, sound pitch jitter (`0.95–1.05`), and clear visual telegraphs.

## 2. Clean Modular Architecture (Zero Spaghetti, Zero Stubs)
Always scaffold a real, complete multi-script architecture using `multi_edit`:
- `ReplicatedStorage.Shared.Config` — single source of truth for game constants, weapon/ability stats, wave/shop tables, and palette tokens.
- `ReplicatedStorage.Shared.Remotes` (created cleanly once) — typed `RemoteEvent` / `RemoteFunction` contracts with server validation.
- `ServerScriptService.Systems.*` — authoritative GameManager, Combat/HitboxService, Economy/DataService, RoundService, and Map/SpawnerService.
- `StarterPlayer.StarterPlayerScripts.Controllers.*` — responsive InputController, CameraController, ProceduralAnimController, VFXController, and HUDController.
- `StarterGui.*` — built directly in Edit mode with `execute_luau` first (or cleanly hydrated), never left with dead buttons or `-- TODO` placeholders.

## 3. Complete Vertical-Slice Rule (No Fake Features)
- **Never ship UI-only shells:** Every button (Play, Shop, Equip, Ability 1–4, Dash, Block, Skip) MUST connect end-to-end to real gameplay logic and server state.
- **Read complementary playbooks automatically:** When a 1:1 clone includes custom rigs/attacks, also read `animations-rigging-procedural` and `combat-vfx-gamefeel`; for maps, read `maps-biomes-atmosphere`; for custom movement/cameras, read `camera-movement-physics`; for HUDs, read `ui-craftsmanship`.
- **Clean Reset & Memory Safety:** Track every `RBXScriptConnection` and spawned VFX/NPC in a cleanup table (`Janitor`/array) so round resets and player respawns never leak memory or duplicate listeners.

## 4. Mandatory 1:1 Visual & Playtest Verification Gate
1. Call `screen_capture` on the built map & HUD in Edit mode to verify lighting, scale, colors, and UI alignment (fix any overlap or flat lighting immediately).
2. Run `start_stop_play {"is_start": true}`, test core inputs or inspect live state via `###LUA:Server###` / `###LUA:Client###`, check `get_console_output` for **zero runtime errors/warnings**, then stop playtesting cleanly (`start_stop_play {"is_start": false}`).

