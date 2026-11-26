---
id: security-datastore-trading
name: "Zero-Trust Security, DataStores & Trading"
category: Scripting
tagline: "Remote validation, Finite bounds, TokenBucket rate limits, atomic UpdateAsync persistence, ProcessReceipt idempotency & dupe-proof RevisionTrade."
enabled: true
mode: auto
builtin: true
---
# Zero-Trust Security, DataStores & Trading Playbook

Follow this engineering standard whenever building RemoteEvents, RemoteFunctions, DataStore saving, developer product receipts (`ProcessReceipt`), or player-to-player trading.

## 1. Remote Security & Anti-Exploit Rules
- **Clients send INTENT, never outcomes:** Never accept damage numbers, prices, currencies, cooldowns, or arbitrary Instance targets from a client without full server verification.
- **Built-in Starter Modules Available:** Pull ready-to-use server modules via `get_luau_module` (`TokenBucket`, `Finite`, `RevisionGate`, `RevisionTrade`, `RequestEpoch`, `ScopedRay`) rather than writing fragile ad-hoc checks.
- **Validation Order (Cheap First):**
  1. Verify rate limit (`TokenBucket.allow(player.UserId)`); clean up on `Players.PlayerRemoving`.
  2. Type-check every argument (`typeof(x) == "number"`), string length bounds, and table key/depth limits.
  3. Reject `NaN` / `math.huge` / out-of-range numbers (`Finite.number(x, min, max)` and `Finite.vector3(...)`).
  4. Verify ownership, cooldown, distance/line-of-sight (`ScopedRay`), and character alive state BEFORE yielding or writing state.
- **Never Invoke Clients for Authoritative Decisions:** Never use `RemoteFunction:InvokeClient()` on server gameplay paths (a malicious or disconnected client can yield forever or spoof returns).

## 2. Conflict-Safe DataStore Persistence
- **Versioned Schema & Load-Failure Protection:** Always track `SchemaVersion`. Distinguish `"no prior save"` (new player) from `"DataStore error"` (failed read) — NEVER overwrite an existing player's profile with defaults when `GetAsync`/`UpdateAsync` throws.
- **Session Ownership & `UpdateAsync`:**
  - Prefer `UpdateAsync` over `SetAsync` for profile commits; include an active session lock/token so two servers cannot corrupt the same player key.
  - **CRITICAL:** Never yield (`task.wait`, HTTP calls, unrelated datastore calls) or trigger external side effects (`FireClient`, currency grants) INSIDE an `UpdateAsync` transform callback — transforms can retry automatically on conflict.
- **Lifecycle Flush:** Save periodically, on `Players.PlayerRemoving`, and inside `game:BindToClose()` (yielding cleanly with bounded timeout until active saves flush).

## 3. Idempotent `ProcessReceipt` Purchases
- Assign exactly **ONE** server script as `MarketplaceService.ProcessReceipt`. Never grant Developer Product rewards from `PromptProductPurchaseFinished` (it is only UI feedback).
- Store processed `receiptInfo.PurchaseId` inside a bounded deduplication list (e.g., last 50–100 purchase IDs) persisted in the SAME `UpdateAsync` commit as the granted coins/items.
- Return `Enum.ProductPurchaseDecision.PurchaseGranted` ONLY after the profile commit succeeds. Return `Enum.ProductPurchaseDecision.NotProcessedYet` on missing profile or DataStore failure so Roblox safely retries.

## 4. Dupe-Proof Player-to-Player Trading
- Use a server-owned trade session with **monotonic revision numbers** (`RevisionTrade` / `RevisionGate`).
- Any offer change by either player MUST increment `revision` and immediately clear BOTH players' `confirmed` / `locked` flags.
- Reserve/validate item ownership on the server before starting the countdown, reject stale-revision confirm calls, verify neither player disconnected mid-trade, and swap items atomically before unlocking inventories.

## 5. Mandatory Security Verification
- Before finishing any server script, run `{"command": "audit_luau", "params": {"code": "<script_source>", "filename": "<Name>.server.luau", "context": "server"}}` and resolve all `G12`–`G22`, `G53`–`G59` security/persistence findings.

