# ZeroScript - Free AI Agent for Roblox Studio

![GitHub stars](https://img.shields.io/github/stars/sebattfg/ZeroScript-Free?style=social)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)

**ZeroScript** is a free browser extension that turns Claude, ChatGPT, DeepSeek, Gemini, Google AI Studio, Grok, Mistral Le Chat, Kimi, GLM, Qwen, Arena or Meta AI into a Roblox Studio AI agent.
Control Roblox Studio with AI directly from your browser - read/edit scripts, run Luau, generate assets, all from a normal AI chat. No API key, no terminal, no coding needed.

> 🌐 **Website: [zerodev.tools/zeroscript](https://zerodev.tools/zeroscript)** the free Lemonade.gg / Luamotion alternative for building Roblox games with AI.

Twelve AI providers are supported: **Claude** (claude.ai), **DeepSeek** (chat.deepseek.com, recommended), **ChatGPT** (chatgpt.com), **Google Gemini** (gemini.google.com), **Google AI Studio** (aistudio.google.com), **Grok** (grok.com), **Mistral Le Chat** (chat.mistral.ai), **Kimi** (kimi.ai), **GLM** (chat.z.ai), **Qwen** (chat.qwen.ai), **Arena** (arena.ai / lmarena.ai), and **Meta AI** (meta.ai). On ChatGPT, screenshots and image input are turned off on purpose because the free tier limits files separately from messages. On Arena, use **Direct** mode (ZeroScript blocks Start in Battle / Side-by-Side / Agent modes).

> 💬 **Stuck? Join the [Discord community](https://discord.gg/9aNyZsMWcb)** get help, share feedback, and follow updates.

> *Also known as: ZeroScript Roblox, ZeroScript free download, Roblox Claude agent, Roblox ChatGPT agent, Roblox DeepSeek agent, Roblox Gemini agent, Roblox Google AI Studio agent, Roblox Grok agent, Roblox Mistral agent, Roblox Kimi agent, Roblox GLM agent, Roblox Qwen agent, Roblox Arena agent, Roblox Meta AI agent, Roblox Studio AI automation, Luau AI, MCP Roblox*

## ⚠️ ZeroScript is Free Beware of Paid Copycats

ZeroScript is 100% free and open-source. It always has been, and it always will be. There is no official paid version, no subscription, and no sign-in required to use the extension.

If you come across a site or extension using the ZeroScript name that asks for payment or account creation, it is **not** this project. The only official links are the ones listed at the top of this README.

## How it works

```
AI chat (Claude / DeepSeek / ChatGPT / Gemini / Google AI Studio / Grok / Mistral / Kimi / GLM / Qwen / Arena / Meta AI) -> ZeroScript Extension -> Bridge (your PC) -> Roblox Studio
```

The extension runs inside the chat page. When you type a request, it sends commands to the Bridge running on your PC, which drives Roblox Studio through the built-in MCP server.

## Setup

> 📺 **Lost? Watch the [setup tutorial on YouTube](https://youtu.be/kPKiZLZ9_Ps) it covers every step below.**

### 1. Download the zip and install the extension

Download the latest zip from the **Releases** page and extract it. The zip contains both the **Bridge** and the **extension folder**.

To load the extension:

- Go to `edge://extensions` (Edge) or `chrome://extensions` (Chrome)
- Enable **Developer mode** (top right toggle)
- Click **Load unpacked**
- Select the `zeroscript-extension` folder from the extracted zip

### 2. Start Roblox Studio and enable MCP

Open Studio and load a Place, then enable MCP (first time only):

- Click **Assistant AI** in the top bar
- Click **...** (top right of the Assistant panel)
- Click **Manage MCP Servers**
- Click **Enable Studio as MCP Server**

> Not sure where to find these options? The [video tutorial](https://youtu.be/kPKiZLZ9_Ps) shows exactly where to click.

### 3. Run ZeroScript (Desktop App & Bridge)

- **Windows (recommended, no terminal):** double-click `ZeroScript.vbs` (or `start_app.bat` on first run) to open the **ZeroScript Desktop App** and system tray icon — closing the window leaves the bridge running silently in the background. *(You can still use `start.bat` if you prefer the classic terminal view.)*
- **macOS:** double-click `MacOS_Start.command` inside the extracted folder. The first time, macOS will show a security warning ("could not verify... free of malware") - this is normal for any script downloaded outside the App Store, click **Done**, then go to **System Settings > Privacy & Security**, scroll to the bottom, and click **Open Anyway**. You only need to do this once.

Once the app or window says **Bridge online**, you're ready to connect.

### 4. Start a session

Go to https://claude.ai, https://chat.deepseek.com, https://chatgpt.com, https://gemini.google.com, https://aistudio.google.com, https://grok.com, https://chat.mistral.ai, https://www.kimi.ai, https://chat.z.ai, https://chat.qwen.ai, https://arena.ai or https://www.meta.ai and open a new chat. The ZeroScript bar appears above the input box. Click **▶︎ Start Roblox agent**. Type what you want to build.

> Works across all 12 supported AI chat sites above (including `lmarena.ai` and `www.chatgpt.com`).
> On Arena, keep the mode dropdown on **Direct** - ZeroScript blocks Start in Battle / Side-by-Side / Agent modes.
> If Gemini or any AI ever claims the bridge is offline mid-chat while Studio is connected, ZeroScript now automatically reminds it and refreshes instructions behind the scenes.
### 5. Watch the setup tutorial

[Watch the setup tutorial on YouTube](https://youtu.be/kPKiZLZ9_Ps)

## What the AI can do

- Read and edit scripts
- Run Luau code directly in Studio
- Inspect the game tree and instances
- Generate meshes, materials, and models
- Browse and insert from the Creator Store
- Control play-testing
- **Apply 17 specialized AAA Agent Skills** — built-in playbooks for **1:1 Game Recreation**, **AAA Animations & Motor6D Procedural Motion**, **Creature Gaits, Facial Rigs & State Machines**, **Movement/Parkour & Camera Feel**, **1:1 Map Design & Biomes**, **Zero-Trust Security, DataStores & Trading**, **Pets, Quests & Lobbies**, **1:1 Reference UI, Mobile & Gamepad UX**, UI & HUD Craftsmanship, 3D Building & Architecture, Cutscenes & Camera Choreography, Combat & VFX, Luau Architecture & Networking, NPC AI/Bosses, Lighting & Spatial Audio, Economy & Shops, and Performance Optimization (plus 1-click preset packs and custom `.md` skills)
- **Built-in 60-Gate Luau Auditor, 19 Starter Modules, 12-Genre Style Guide & Local Project Memory** — AIs can automatically route playbooks (`route_skills`), scan scripts (`audit_luau`), pull reusable security/UI/animation modules (`get_luau_module`), inspect 12 genre design tokens (`get_style_guide`), diagnose Roblox bugs (`diagnose_bug`), and persist architecture facts (`memory_read` / `memory_write`), all also available interactively in the Desktop App's **Toolkit** tab

## New in 1.9.1

- **All-AI Start Button & Session Startup Fixes.** Fixed Start/Stop/menu buttons hijacking host `<form>`/`<fieldset>` submissions (`type="button"` + event isolation), fixed `startSession()` falsely reporting `Agent active` when startup sending/generation fails or returns an internal error, and added native `openNewChat()` support across all 12 AI providers.
- **Gemini, Google AI Studio, Claude, Grok, Mistral & Kimi Fixes.** Replaced Gemini's fragile Angular `<fieldset>` mount with safe `barAnchor()`, broadened Gemini/Claude/Grok send-button & editor selectors, fixed Grok plain-text assistant turn classification, added auto-clearing of interfering Google AI Studio `Grounding with Google Search` / `URL context` chips at startup, and unified normalized multi-line editor injection across contenteditable providers.

## New in 1.9.0

- **60-Gate Pure-Python Luau Static Auditor (`audit_luau`).** Scans individual Luau scripts or full local folders for Remote security gaps, `UpdateAsync` yield bugs, `RBXScriptConnection` leaks, division by zero, nil receivers, and circular `require()` dependencies — directly from the Desktop App **Toolkit** tab or automatically via any connected AI.
- **19 Battle-Tested Luau Starter Modules (`luau_modules/`).** Ready-to-use `TokenBucket`, `AttackWindow`, `RevisionTrade`, `RevisionGate`, `Finite`, `CriticalSpring`, `ModalTransition`, `HealthBinding`, `ViewportFit`, `StudioProbe`, and more via `list_luau_modules` / `get_luau_module` and in-app preview.
- **4 New AAA Playbooks (17 Total) + Presets.** Added **Zero-Trust Security, DataStores & Trading**, **Pets, Quests, Dialogue & Matchmaking Lobbies**, **1:1 Reference UI, Mobile & Gamepad UX**, and **Creature Gaits, Facial Rigs & Anim State Machines**, plus **Security, Data & LiveOps** and **1:1 UI, Mobile & Polish** preset packs.
- **Smart Skill Router, 12-Genre Style Vocab, Bug Recovery & Local Project Memory.** Interactive task router, 12-genre anti-slop style guide, 12 *Symptom → Probe → Repair → Retest* bug guides, 53 API gotchas, and local secret-filtered architecture memory ledger.

## New in 1.8.0

- **4 Overpowered AAA Playbooks (13 Total).** Added **1:1 Game Recreation & Clone Architect**, **AAA Animations, Motor6D & Procedural Motion** (code-authored live `KeyframeSequence` + 60fps `Motor6D.Transform` springs), **AAA Movement, Parkour & Camera Feel**, and **1:1 Map Design, Landmarks & Biomes**, plus **1:1 Game Cloner** and **Animations & Game Feel** preset packs.
- **Liquid Glass Mode & Atmospheric Backdrops.** New Apple-inspired translucent blown-glass UI option in Settings with curved specular edge lensing, 4 scenic backdrops (**Sunset Skyline**, **Aurora Sky**, **Deep Ocean**, **Midnight Neon**), selectable refraction styles (**Liquid Glass**, **Frosted Dark**, **Crystal Clear**), and a 6th **Prism** accent theme.
- **Upgraded App Motion & Utilities.** Spring transitions, cursor specular sheen, smooth `requestAnimationFrame` ambient backdrop, animated KPI counters, Activity JSON export + call copy, and `Ctrl+K` Command Palette arrow-key navigation.

## New in 1.7.0

- **ChatGPT & Arena Start Bar Fixes.** Hardened `chatgpt.js` with non-React `barAnchor()` placement and multi-selector editor detection (`chatgpt.com` + `www.chatgpt.com`); fixed `arena.js` across `arena.ai` / `lmarena.ai` / `chat.lmsys.org` with dual `<textarea>`/`contenteditable` support, safe dialog gating, and an actionable **`＋ New agent chat`** button on older chats.
- **4 New AI Providers (12 Total).** Added first-class Studio agent integration for **Claude** (`claude.ai`), **Google AI Studio** (`aistudio.google.com`), **Grok** (`grok.com`), and **Mistral Le Chat** (`chat.mistral.ai`).
- **6 New Pro Developer Playbooks + Preset Packs.** Expanded built-in skills from 3 to 9 (Combat/VFX, Luau/DataStore, NPC AI/Bosses, Lighting/Audio, Economy/Loops, Performance/Mobile) with 5 one-click loadout presets and `.md` import/export.
- **Modern Desktop Workspace + 5 New Features.** Redesigned dark glassmorphism UI with **Live Activity Inspector**, **Prompt Studio + Global Rules Sync** across all 11 AIs, **System Health Doctor** diagnostics, **`Ctrl+K` Command Palette**, pinned AI quick-launch, and 5 selectable accent themes.

## New in 1.6.0

- **ZeroScript Desktop App (`ZeroScript.vbs`).** Launch ZeroScript into a clean dark desktop dashboard + system tray icon instead of keeping a terminal window open, with live Studio/Bridge telemetry, AI provider quick-launch, MCP server management, and live logs.
- **Overpowered AI Agent Skills (`skills/`).** Built-in UI, Building, and Cutscenes playbooks plus custom skill editor in the Environment tab, synced live to connected AI tabs via `read_skill` / `list_skills`.
- **ChatGPT reliability fixes.** Prevented `unwedgeStop()` synthetic clicks from killing the agent loop, improved thinking/warmup detection, hardened composer bar mounting and CodeMirror reading, and added support for ChatGPT Projects/Custom GPT URLs.

## New in 1.5.5

- **DeepSeek: the agent starts again on the new unified model.** DeepSeek merged Instant, Expert and Vision into one model and removed the model picker, which left "Start Roblox agent" stuck on "DeepSeek mode not ready". ZeroScript now recognises the new chat box, switches Search off and starts, with DeepThink left on.
- **DeepSeek: screenshots work on every chat.** Images no longer need the Vision tab (it is gone) - the unified model sees your Studio captures, one at a time or several in a row.

## New in 1.5.4

- **ChatGPT: the ZeroScript bar is back above the composer.** ChatGPT redesigned its input box and renamed the layout slot the bar sits in. ZeroScript kept asking for the old name, so the browser dropped the bar into a stray strip at the bottom right of the composer and squeezed the text field to nothing. The bar now takes the right row again, and it reads the layout live instead of trusting a fixed name, so the next redesign should not knock it out.
- **ChatGPT: long commands read cleanly on the new interface.** The same redesign replaced the code-block editor that used to hide line breaks and cut long lines off - the cause of the truncated commands fixed in 1.5.1. A 400-line block now reads back whole. If you are still on the old interface, the previous workaround is untouched.

## New in 1.5.3

- **Kimi moved to kimi.ai.** The old address, kimi.com, now asks for a Chinese phone number to sign in, which locked most people out. Open https://www.kimi.ai instead - the page is unchanged, the bar appears above the input box exactly as before. Reopen any Kimi tab you had on the old address.
- **DeepSeek: the Instant model can now run the agent.** Picking Instant used to leave "Start Roblox agent" spinning forever with no explanation, because only Expert and Vision were accepted. Choose Instant before starting and the session runs on it - much faster than Expert, without the reasoning pass. Images stay off on Instant just like on Expert; the Vision tab remains the only one that can see screenshots.
- **DeepSeek: a reply written in DeepSeek's own tool-call format no longer kills the turn.** DeepSeek occasionally answers with its internal markup instead of a ZeroScript command. Nothing recognised it, so the tool never ran, the raw tags stayed on screen and the agent stopped dead with you waiting. It is now caught, hidden behind a tool chip like any other command, and DeepSeek is told to rewrite the call properly.
- **ChatGPT: the bar no longer clips into the composer's rounded corners.**

See [CHANGELOG.md](CHANGELOG.md) for older releases.

## Panel status

| Dot | Meaning |
|-----|---------|
| Green | Bridge + Studio ready (a place is open) |
| Yellow | Bridge OK, but Studio isn't usable yet - open Roblox Studio, load a place, or enable its MCP server (hover the dot for the exact reason) |
| Grey | Bridge offline - open `ZeroScript.vbs` (Windows) or `MacOS_Start.command` (macOS) |

## Requirements

- Windows or macOS
- Roblox Studio (MCP support built-in)
- Microsoft Edge or Chrome
- Python 3.9+ (installed automatically on Windows, or install it yourself on macOS - see [python.org/downloads](https://www.python.org/downloads/))

## Support

ZeroScript is free. If it saves you time: [Ko-fi](https://ko-fi.com/sebattfg) - Robux tip passes available in the extension panel

---

Credit: the idea for connecting other MCP servers (Blender, Sketchfab, etc.) alongside Roblox Studio came from [javnpa](https://github.com/javnpa).

Credit: macOS/Linux support contributed by [archivealf](https://github.com/archivealf).
