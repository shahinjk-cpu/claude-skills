---
id: luau-architecture-networking
name: "Luau Architecture, Networking & DataStore"
category: Scripting
tagline: "Clean typed Luau services, strict client-server trust boundaries, exponential DataStore retries with session safety, and zero memory leaks."
enabled: true
mode: auto
builtin: true
---
# AAA Luau Architecture, Networking & DataStore Playbook

Follow these production engineering rules whenever architecting game systems, ModuleScripts, RemoteEvents/Functions, or player persistence in Roblox Studio.

## 1. Strict `--!strict` Modular Architecture
- Start new scripts and `ModuleScript`s with `--!strict` (or `--!nonstrict` when dynamic tables genuinely require it) and explicit parameter/return type annotations (`export type PlayerProfile = { Coins: number, ... }`).
- **Clear folder separation:**
  - `ReplicatedStorage.Shared`: Shared configs, item/weapon tables, math utilities, typed signal/trove helpers (never secret server logic!).
  - `ReplicatedStorage.Remotes`: `RemoteEvent` / `RemoteFunction` / `UnreliableRemoteEvent` instances created cleanly in Edit mode or at boot.
  - `ServerScriptService.Services`: Single-responsibility server `ModuleScript`s (`DataService`, `CombatService`, `ShopService`) orchestrated by a deterministic `ServerInit` `Script`.
  - `StarterPlayerScripts.Controllers`: Client controllers consuming remotes cleanly with `WaitForChild(..., 5)` timeouts.
- **Avoid `_G` and `shared`:** Require `ModuleScript`s explicitly so dependencies are visible, reloadable, and type-checked.

## 2. Zero-Trust Networking & Remote Safety
- **NEVER trust client values for rewards, damage, prices, or ownership:**
  - Client sends `"BuyItem"`, `{ itemId = "IronSword" }` — server looks up `Catalog[itemId].Price`, verifies `typeof(itemId) == "string"`, checks `coins >= price`, deducts atomically, grants item, and replicates state.
  - Validate every incoming `OnServerEvent` argument with runtime type guards (`typeof`, `math.isfinite`, finite number bounds, `NaN` checks: `if value ~= value or value == math.huge then return end`) before touching game state.
- **Use `UnreliableRemoteEvent` for high-frequency cosmetic streams** (aim direction, footsteps, continuous lean angles) so packet loss never stalls reliable gameplay remotes.
- **Avoid `RemoteFunction:InvokeClient()` from server:** A stalling or disconnecting client can hang server coroutines forever. Prefer `RemoteEvent:FireClient` with timeouts if server asks client.

## 3. Bulletproof DataStore Persistence
Whenever saving player data:
- **Clone & Merge Defaults:** Deep-clone a `DEFAULT_DATA` table for new players and reconcile missing keys on load (`migrateProfile(raw)`) so future schema updates never nil-index old saves.
- **Retries + Backoff + BindToClose:**
  - Wrap `GetAsync` / `UpdateAsync` (prefer `UpdateAsync` over `SetAsync` to preserve atomic ordering and version metadata!) inside a `pcall` retry loop (`attempts = 4`, backoff `1s, 2s, 4s`).
  - Save on `PlayerRemoving`, optional periodic autosave (`~120s`, staggered per player to stay well below budget!), AND inside `game:BindToClose()` waiting until all in-flight saves finish (`RunService:IsStudio()` check for quick local shutdown tolerance).
  - Guard against saving corrupt/unloaded data (`if not loadedFlags[player] then return end`) so a failed `GetAsync` on join NEVER overwrites a player's rich save with empty defaults!

## 4. Connection & Memory Leak Hygiene
- Track per-player runtime state and `RBXScriptConnection`s cleanly (`trove` / cleanup array) and disconnect/release EVERYTHING in `Players.PlayerRemoving`.
- Never bind `RunService.Heartbeat` per-object when one central system loop iterating an array/registry handles hundreds of objects in a fraction of the CPU budget.
- Replace deprecated globals (`wait()`, `spawn()`, `delay()`, `Vector3.new` legacy physics constraints) with `task.wait()`, `task.spawn()`, `task.delay()`, and modern constraints (`LinearVelocity`, `AlignPosition`, `AlignOrientation`).

