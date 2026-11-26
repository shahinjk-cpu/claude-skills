---
id: pets-quests-lobbies
name: "Pets, Quests, Dialogue & Matchmaking Lobbies"
category: Gameplay
tagline: "Server-owned pet inventories with spring-smoothed visual followers, data-driven quests/dialogue, and reserved-server party lobbies."
enabled: true
mode: auto
builtin: true
---
# Pets, Quests, Dialogue & Matchmaking Lobbies Playbook

Apply this architecture when building pet/egg systems, NPC quest givers, branching dialogue trees, or multiplayer party/matchmaking queues.

## 1. Pet Systems & Visual Followers
- **Server Owns Stats, Client Owns Visuals:** Replicate only the compact equipped pet list (IDs, traits, equip slots) to clients via attributes/snapshots; NEVER simulate floating pet Parts on the server with Physics ownership or heavy server Heartbeat loops.
- **Smooth Formation & Motion:** Pull `Formation`, `CriticalSpring`, and `CleanupScope` via `get_luau_module`.
  - Compute stable arc/grid target offsets behind the owner's `HumanoidRootPart` using `Formation.slotOffset(...)`.
  - Step visual pet position/bob with `CriticalSpring` + gentle ground raycast (`ScopedRay`) and reset/snap on large teleports.
  - Track every spawned pet model + connection in a `CleanupScope` keyed per player and clean immediately on unequip, respawn, or leave.
- **Egg Hatching & Rarity Drops:** Resolve weighted rolls server-side (`WeightedChoice`), enforce inventory capacity and currency deduction atomically before firing the hatch animation event to clients, and support Skip/Multi-hatch cleanly.

## 2. Data-Driven Quests & Branching Dialogue
- **Declarative Quest Catalog (`ReplicatedStorage.Shared.Quests`):** Define each quest ID with objectives (`{type, target, required}`), prerequisite quests, and server-side rewards.
- **Server Objective Progression:** Gameplay services (CombatService, GatherService, ZoneService) call `QuestService:AddProgress(player, metric, amount)` — clients NEVER self-report quest completions.
- **Idempotent Reward Claims:** Use `RevisionGate` or explicit `"claimed"` state flags checked BEFORE granting rewards so spam-clicking Claim cannot double-reward.
- **Non-Blocking Dialogue UI:** Drive NPC conversations via `ProximityPrompt` + declarative dialogue node graphs (`text`, `speaker`, `choices[]`, optional `condition` / `questHook`). Always preserve character control cancellation (Esc/walk-away closes cleanly) and animate typewriter text without yielding blocking loops.

## 3. Party Queues & Reserved-Server Matchmaking
- **Lobby Pad / Queue Zone State Machine:** Track party members in a server dictionary (`Waiting -> CountingDown(5s) -> Teleporting -> Cleanup`). Validate walk-out cancellation cleanly without leaving ghost slots.
- **Safe Teleportation (`TeleportService`):**
  - Use `TeleportService:ReserveServer(targetPlaceId)` + `TeleportService:TeleportAsync(targetPlaceId, partyPlayers, options)` wrapped in retry/backoff + Studio guard (`if game:GetService("RunService"):IsStudio() then ... end` so Studio playtests simulate match start cleanly instead of failing on TeleportService).
  - Pass only non-sensitive metadata via `TeleportOptions:SetTeleportData(...)` and verify player counts/roles inside the destination server (`MatchService`).

