---
id: npc-ai-pathfinding
name: NPC AI, Pathfinding & Boss Systems
category: Gameplay
tagline: Smart Finite State Machines, async PathfindingService with Blocked recovery, telegraphed boss attacks, aggro tables, and crisp rig animations.
enabled: true
mode: auto
builtin: true
---
# AAA NPC AI, Pathfinding & Boss Systems Playbook

Follow these production rules whenever building enemies, guards, pets, villagers, zombies, or multi-phase boss encounters in Roblox Studio.

## 1. Finite State Machine (FSM) Architecture
Never cram AI into messy nested `if/elseif` `while true do` loops:
- Structure each NPC/Boss cleanly inside a `ModuleScript` class or central AI manager with explicit states:
  `Idle` / `Patrol` → `Chase` → `Windup` → `Attack` → `Recover` → `Stunned` / `Dead` (plus `Leash` return to spawn if pulled too far).
- Run transitions explicitly via `setState(npc, newState)` so animations, hitbox enables, sounds, and cooldowns start/stop deterministically on entry/exit.

## 2. Lag-Free Pathfinding & Stuck Recovery
- **Use `PathfindingService:CreatePath(agentParams)`** tuned to the rig's real dimensions (`AgentRadius`, `AgentHeight`, `AgentCanJump = true`, optional `Costs` table for hazard avoidance).
- **Direct Chase Shortcut:** When target is within close line-of-sight (`dist < 22` studs and `Workspace:Raycast` finds clear unobstructed floor/line), call `Humanoid:MoveTo(targetPos)` directly instead of rebuilding expensive A* paths every tick!
- **Async Recompute + `Blocked` Handling:**
  - Throttle `ComputeAsync` to `0.35–0.6s` per active chasing NPC (staggered across frames so 30 NPCs never spike one frame).
  - Listen to `path.Blocked:Connect(function(blockedIdx) ...)` and trigger path recompute only if `blockedIdx >= currentWaypointIdx`.
  - Add a progress check: if `HumanoidRootPart.AssemblyLinearVelocity.Magnitude < 1.5` while moving for `> 1.2s`, force a jump/sidestep or recompute path so enemies never hump doorways.
- **Network Ownership:** Call `pcall(function() rootPart:SetNetworkOwner(nil) end)` on anchored/combat NPC roots once parented to `Workspace` so players walking near an NPC cannot hijack physics ownership and teleport/lag it!

## 3. Readable, Fair Combat & Multi-Phase Boss Design
- **Telegraph EVERYTHING:** Every heavy attack or AoE slam MUST have a clear `0.45–1.0s` windup before hitbox activation:
  - Distinct raise animation + glow/tint flash + warning ground decal/ring (`Cylinder` / `BillboardGui` filling inward to timing) + audio cue ("charge up") so skilled players can dodge on reaction.
- **Phase Transitions:** Drive Phase 2 (`<= 55% HP`) / Enrage (`<= 20% HP`) cleanly via threshold flags, granting brief invulnerability during transition animation + shockwave push + escalated moveset weights (weighted random pick avoiding repeating the same attack twice back-to-back).
- **Aggro / Threat Table:** Track damage dealt per player (`threat[player] += dmg`) with gentle distance bonus and decay, switching targets cleanly and removing disconnected/dead players automatically.

## 4. Performance & Rig Checklist
- Keep `Humanoid` state overhead lean on simple horde NPCs (`Humanoid:SetStateEnabled` disabling unused states like `Climbing`, `Swimming`, `Seated` if not needed).
- Cleanup dead NPCs cleanly after ragdoll/dissolve (`task.delay(3.5, destroyFn)`), disconnecting all signals so server memory stays flat across long sessions.
- Verify NPC `PrimaryPart` is `HumanoidRootPart`, `Anchored = false` on limbs (unless scripted tween rig), and non-colliding armor accessories have `CanCollide = false` + `Massless = true`.
