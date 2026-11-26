---
name: roblox-studio-suite
description: >
  Roblox platform game development: Luau scripting, DataStores persistence, client-server networking replication, character rigging, custom physics, simulator economies, and Studio UI design.
category: game_3d
version: "2.0.0"
role: consolidated_suite
triggers: roblox-studio-suite, roblox studio & luau development suite, roblox, roblox-characters, roblox-datastores, roblox-luau, roblox-networking, roblox-physics, roblox-simulator-economy, roblox-studio-workflow, roblox-ui
---

# 🧱 Roblox Studio & Luau Development Suite

Roblox platform game development: Luau scripting, DataStores persistence, client-server networking replication, character rigging, custom physics, simulator economies, and Studio UI design.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (8 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`roblox-characters`**: Build respawn-safe Roblox character systems around Players, CharacterAdded/CharacterRemoving, Humanoid, HumanoidRootPart, Animator, R6/R15 rigs, movement, animations and markers, death, tools, accessories, ownership, and custom characters. Use when character scripts break after respawn, cache stale Humanoids, control movement or velocity, load AnimationTracks, handle death, equip Tools, modify avatars, or support custom player rigs.
  - *Reference File:* `references/roblox-characters.md`
- **`roblox-datastores`**: Persist player data in Roblox with DataStoreService: GetDataStore, GetAsync/ SetAsync/UpdateAsync/IncrementAsync wrapped in pcall, load-on-join and save-on-leave plus BindToClose, retries, and OrderedDataStore leaderboards. Use when saving or loading persistent data in a Roblox experience — when the user mentions DataStore, DataStoreService, GetAsync, SetAsync, UpdateAsync, save player data, or leaderboards. For general Luau scripting use roblox-luau.
  - *Reference File:* `references/roblox-datastores.md`
- **`roblox-luau`**: Script a Roblox experience in Luau: get services, create and parent Instances, connect events, run server Scripts vs client LocalScripts, and communicate across the client/server boundary with RemoteEvents/RemoteFunctions (server-authoritative). Use when building or debugging Roblox Studio scripts — when the user mentions Roblox, Luau, services, RemoteEvent, Instance.new, PlayerAdded, or client vs server. For saving player data use roblox-datastores.
  - *Reference File:* `references/roblox-luau.md`
- **`roblox-networking`**: Design and harden Roblox client/server networking with RemoteEvent, RemoteFunction, and UnreliableRemoteEvent; server authority, argument and Instance validation, rate limits, proximity/ownership checks, targeted replication, streaming, lifecycle, prediction, and reconciliation. Use for Roblox remotes, exploits, request spam, multiplayer replication, network ownership, high-frequency cosmetic updates, or server/client desynchronization.
  - *Reference File:* `references/roblox-networking.md`
- **`roblox-physics`**: Implement Roblox physical simulation and queries with assemblies, anchoring, constraints, collision groups, CanCollide/CanTouch/CanQuery, raycasts and overlap queries, mass, impulses, forces, velocity, moving assemblies, cleanup, and network ownership. Use for Roblox collisions, hit detection, RaycastParams, PhysicsService, projectiles, vehicles, knockback, constraints, deprecated BodyMovers, unstable motion, or client-owned physics exploits.
  - *Reference File:* `references/roblox-physics.md`
- **`roblox-simulator-economy`**: Design, balance, and implement the economy of a Roblox simulator, tycoon, clicker, or idle game in Luau: upgrade cost curves, buy max, income per second, rebirth/prestige requirements and multipliers, offline earnings, big-number display (1.5K, 3.4M, 2.0Qa), server-authoritative purchases, repairing tampered or old save data, and odds disclosure for paid random items such as eggs, crates, and spins. Includes a Lune pacing calculator. Use when choosing or checking baseCost/costGrowth/rebirth numbers, writing upgrade/currency/rebirth/offline code, or when progress stalls, a rebirth takes far longer than the last, numbers display as 1000K, offline earnings pay too much, or players gain currency they did not earn.
  - *Reference File:* `references/roblox-simulator-economy.md`
- **`roblox-studio-workflow`**: Modify living Roblox Studio projects safely: inspect Explorer and execution locations, preserve existing structure, reuse modules/remotes, create meaningful Instances, apply Attributes and CollectionService tags, test server/client and multiple devices, inspect Output, and remove experiments/debug objects. Use when an agent edits a place or rbxl/rbxlx/Rojo project, operates in Studio, adds Scripts/LocalScripts/ModuleScripts, or must verify a Roblox change in context.
  - *Reference File:* `references/roblox-studio-workflow.md`
- **`roblox-ui`**: Build production Roblox interfaces with ScreenGui/PlayerGui lifecycle, responsive UDim2 layouts, safe insets, reusable editable Instances, cross-device input and selection, restrained motion, cleanup, and multi-viewport verification. Use for Roblox HUDs, inventories, shops, settings, ability bars, ScrollingFrames, AutomaticSize, GuiService, gamepad focus, touch UI, or UI that clips, resets on respawn, looks generic, or was generated as one giant LocalScript.
  - *Reference File:* `references/roblox-ui.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `roblox-characters`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
