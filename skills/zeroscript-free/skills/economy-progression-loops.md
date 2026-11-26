---
id: economy-progression-loops
name: Economy, Shops & Progression Loops
category: Gameplay
tagline: "Balanced Roblox tycoon/RPG/simulator loops: server-authored ItemRegistry, multipliers & Rebirth math, daily rewards, quest trackers, and crisp feedback."
enabled: true
mode: auto
builtin: true
---
# AAA Economy, Shops & Progression Loops Playbook

Follow these design and engineering standards whenever building currencies, shops, inventories, upgrades, quests, rebirth systems, or tycoon loops in Roblox Studio.

## 1. Single Source of Truth Registry (`ReplicatedStorage.Shared.Catalog`)
- Define ALL items, upgrades, crates, pets, passes, and quest tiers in ONE shared declarative `ModuleScript` table (`id`, `name`, `price`, `currency`, `rarity`, `stats`, `iconAsset`, `description`).
- **Both client UI and server handlers read from the SAME registry:**
  - UI renders cards dynamically from `Catalog` (no hardcoded mismatched prices between UI labels and server scripts!).
  - Server looks up `Catalog[itemId]` and never accepts client-supplied prices or reward amounts.

## 2. Satisfying Core Loop & Anti-Inflation Math
Design clear short-term (`10–30s`), medium-term (`3–10m`), and long-term (`Rebirth` / `Prestige`) goals:
- **Cost & Output Curves:** Scale upgrades predictably (`baseCost * (growthRate ^ level)`, typically `1.15x–1.35x` for incremental simulators) so players always see an attainable next unlock right ahead of them.
- **Clean Multipliers Architecture:** Compute effective gains in one pure server function:
  `gain = baseGain * (1 + upgradeBonus) * petMultiplier * rebirthMultiplier * eventMultiplier` (additive within tier, multiplicative across major tiers — prevents accidental `10^100` overflow bugs early!).
- **Number Formatting (`FormatUtility`):** Format values `>= 1,000` cleanly (`1.25K`, `42.8M`, `3.10B`, `9.4T`) in HUDs and shop prices, while keeping full numeric precision in `leaderstats`/data tables (avoid `IntValue` truncation past `2^53`; use `NumberValue` or Attributes cleanly).

## 3. Snappy Shop & Purchase UX
When a player buys, equips, or claims a reward:
1. Disable/debounce button briefly client-side (`busy = true`) and invoke a `RemoteFunction` (`PurchaseItem`) or `RemoteEvent` (`BuyRequest` + `StateSync`).
2. Server validates ownership/capacity/balance atomically BEFORE deducting coins (`if coins < cost then return false, "Not enough Coins" end`), prevents duplicate unlock of unique items, updates profile, replicates updated inventory/currency via `Attributes` or `SyncState` remote.
3. Client triggers celebratory feedback ONLY on server confirmation: chime SFX + brief confetti/spark flash + smooth "Owned / Equipped" badge transition + toast on insufficient funds!

## 4. Quests, Daily Streaks & Retention Hooks
- Model quests cleanly with `{ id, title, metric ("Kills"|"CoinsEarned"|"Playtime"), target, progress, reward, claimed }`.
- Increment metrics centrally inside server services (never trust a client `"QuestProgress"` remote!), push compact delta updates, and guard `ClaimQuestReward` with an atomic `if quest.claimed or quest.progress < quest.target then return end` check!
- Set `claimed = true` BEFORE granting currency so concurrent rapid clicks can NEVER double-claim a reward.
