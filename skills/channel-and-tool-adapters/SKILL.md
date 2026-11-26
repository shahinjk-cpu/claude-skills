---
name: channel-and-tool-adapters
description: Unified Chat SDK channel integration and tool adapter suite (Slack, Discord, Teams, Telegram, WhatsApp, Linear, GitHub, Resend, Matrix, Webex, and custom tools).
---

# Channel & Tool Adapters Suite

Standardized adapter configurations for connecting AI agents to messaging platforms, issue trackers, and external tools via Chat SDK.

## Supported Channel Integrations
### Anydoc (`add-anydoc`)
---
name: add-anydoc
description: Add local office-document-to-Markdown conversion to NanoClaw agent containers with the pinned Firecrawl AnyDoc CLI. Use when agents need to read attached Word, PowerPoint, Excel, OpenDocument, RTF, EPUB, CSV, or text-based PDF files without uploading them to a hosted parser.
---

# Add AnyDoc

Install one pinned CLI and one focused container skill. Keep document conversion inside the agent container; do not chang

### Atomic Chat Tool (`add-atomic-chat-tool`)
---
name: add-atomic-chat-tool
description: Add Atomic Chat MCP server so the container agent can call local models served by the Atomic Chat desktop app via its OpenAI-compatible API.
---

# Add Atomic Chat Integration

This skill adds a stdio-based MCP server that exposes models running in the local [Atomic Chat](https://github.com/AtomicBot-ai/Atomic-Chat) desktop app as tools for the container agent. Claude remains the orchestrator but can of

### Clidash (`add-clidash`)
---
name: add-clidash
description: Add clidash — a zero-dependency, read-only web dashboard that derives its tabs and tables at runtime from any CLI that lists resources as JSON. Ships pre-wired for NanoClaw's ncl CLI (agent groups, sessions, channels, users, roles), plus message-activity charts, a log tail, and a read-only file viewer for group skills/CLAUDE.md/profiles.
---

# /add-clidash — CLI-derived read-only dashboard

clidash is a small, 

### Codex (`add-codex`)
---
name: add-codex
description: Use Codex (OpenAI's codex app-server) as a full agent provider — planning, tool orchestration, MCP tools, server-side history, session resume — alongside or instead of Claude. ChatGPT subscription or OpenAI API key, vault-only via the selected gateway. Per-group via `ncl groups config update --provider codex`. Distinct from using OpenAI as an MCP tool (where Claude remains the planner).
metadata:
  nanoclaw-provid

### Cursor (`add-cursor`)
---
name: add-cursor
description: Use Cursor (local Agent SDK) as a full agent provider — planning, tool orchestration, MCP tools, session resume — alongside or instead of Claude. Cursor-account sign-in or API key, held by the credential gateway. Per-group via `ncl groups config update --provider cursor`. Distinct from using Cursor as a cloud agent (those run on Cursor VMs and are not this provider).
metadata:
  nanoclaw-provider: cursor
  nanocl

### Dashboard (`add-dashboard`)
---
name: add-dashboard
description: Add a monitoring dashboard to NanoClaw. Installs @nanoco/nanoclaw-dashboard and a pusher that sends periodic JSON snapshots.
---

# /add-dashboard — NanoClaw Dashboard

Adds a local monitoring dashboard showing agent groups, sessions, channels, users, token usage, context windows, message activity, and real-time logs.

## Architecture

```
NanoClaw (pusher)              Dashboard (npm package)
┌──────────┐    

### Deltachat (`add-deltachat`)
---
name: add-deltachat
description: Add DeltaChat channel integration via @deltachat/stdio-rpc-server. Native adapter — no Chat SDK bridge. Email-based messaging with end-to-end encryption.
---

# Add DeltaChat Channel

The adapter drives the `@deltachat/stdio-rpc-server` JSON-RPC subprocess directly — pure Node.js against the DeltaChat core library. Messages are delivered over email with Autocrypt/OpenPGP encryption.

## Install

### 1. Copy th

### Dial (`add-dial`)
---
name: add-dial
description: Add Dial channel integration — a real phone number for SMS and AI voice calls via the Dial platform (getdial.ai). Native adapter — no Chat SDK bridge.
---

# Add Dial Channel

Adds [Dial](https://getdial.ai) — a real phone number for **SMS and AI voice
calls**. Native adapter (no Chat SDK bridge): both directions go through the
`dial` CLI — outbound via `dial message`, inbound via its command-target daemon. NanoCla

### Dial Number (`add-dial-number`)
---
name: add-dial-number
description: Add another phone number to an existing Dial channel — a second (or third) public line for the agent, so one NanoClaw install answers SMS and AI voice calls on multiple numbers. Use when Dial is already installed and the operator wants an additional number (e.g. a personal line plus a support line). Requires the Dial channel to already be installed (see /add-dial).
---

# Add another Dial number

One NanoCla

### Dial Tool (`add-dial-tool`)
---
name: add-dial-tool
description: Give chosen NanoClaw agents a real phone number as a container tool — the `dial` CLI baked into the agent image plus OneCLI credential injection for api.getdial.ai, attached only to the agents you pick, so they can send SMS, place AI voice calls, and receive verification codes from inside the sandbox. Independent of the Dial channel; idempotent; re-run to change which agents may use it. Use when the user wants

### Discord (`add-discord`)
---
name: add-discord
description: Add Discord bot channel integration via Chat SDK.
---

# Add Discord Channel

Adds Discord bot support via the Chat SDK bridge. NanoClaw doesn't ship channels
in trunk — this skill copies the Discord adapter in from the `channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent
reads the prose and applies them, and a parser can apply them deterministically
from the same docum

### Emacs (`add-emacs`)
---
name: add-emacs
description: Add Emacs as a channel. Opens an interactive chat buffer and org-mode integration so you can talk to NanoClaw from within Emacs (Doom, Spacemacs, or vanilla). Local HTTP bridge — no bot token or external service needed.
---

# Add Emacs Channel

Adds Emacs support via a local HTTP bridge. Works with Doom Emacs, Spacemacs, and vanilla Emacs 27.1+.

## What you can do with this

- **Ask while coding** — open the cha

### Gchat (`add-gchat`)
---
name: add-gchat
description: Add Google Chat channel integration via Chat SDK.
---

# Add Google Chat Channel

Adds Google Chat support via the Chat SDK bridge. NanoClaw doesn't ship channels
in trunk — this skill copies the Google Chat adapter in from the `channels`
branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent
reads the prose and applies them, and a parser can apply them deterministically
from the same

### Github (`add-github`)
---
name: add-github
description: Add GitHub channel integration via Chat SDK. PR and issue comment threads as conversations.
---

# Add GitHub Channel

Adds GitHub support via the Chat SDK bridge. The agent participates in PR and
issue comment threads. NanoClaw doesn't ship channels in trunk — this skill
copies the GitHub adapter in from the `channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent
reads the

### Imessage (`add-imessage`)
---
name: add-imessage
description: Add iMessage to NanoClaw — one channel, two backends. Local (this Mac's chat.db via the Chat SDK bridge; macOS + Full Disk Access) or Hosted iMessage (via photon.codes — native spectrum-ts with a device-login wizard; any OS, no Mac relay). Triggers on "add imessage", "connect imessage", "add photon", "imessage via photon", "native imessage".
---

# Add iMessage

NanoClaw talks to iMessage through a single **`im

### Iron Proxy (`add-iron-proxy`)
---
name: add-iron-proxy
description: Install or refresh Iron Proxy and its official Iron Control web console for NanoClaw. Use when selecting the Iron gateway, adding its management UI, configuring credentials and grants, or restoring the proxy, approval bridge, and agent guidance.
---

# Add Iron Proxy gateway

Install the official `iron-control` console and PostgreSQL alongside one central Iron Proxy. NanoClaw core supplies the generic gateway

### Karpathy Llm Wiki (`add-karpathy-llm-wiki`)
---
name: add-karpathy-llm-wiki
description: Add a persistent wiki knowledge base to a NanoClaw group. Based on Karpathy's LLM Wiki pattern. Triggers on "add wiki", "wiki", "knowledge base", "llm wiki", "karpathy wiki".
---

# Add Karpathy LLM Wiki

Set up a persistent wiki knowledge base on NanoClaw, based on Karpathy's LLM Wiki pattern.

Each step is safe to re-run: directory creation uses `mkdir -p`, initial wiki files are created only if abse

### Linear (`add-linear`)
---
name: add-linear
description: Add Linear channel integration via Chat SDK. Issue comment threads as conversations.
---

# Add Linear Channel

Adds Linear support via the Chat SDK bridge. The agent participates in issue
comment threads. Every comment on a Linear issue triggers the agent — no
@-mention needed. NanoClaw doesn't ship channels in trunk — this skill copies the
Linear adapter in from the `channels` branch.

The mechanical steps unde

### Macos Statusbar (`add-macos-statusbar`)
---
name: add-macos-statusbar
description: Add a macOS menu bar status indicator for NanoClaw. Shows a bolt icon with a green/red dot indicating whether NanoClaw is running, with Start, Stop, and Restart controls. macOS only.
---

# Add macOS Menu Bar Status Indicator

Adds a persistent menu bar icon that shows NanoClaw's running status and lets the user
start, stop, or restart the service — similar to how Docker Desktop appears in the menu bar.


### Matrix (`add-matrix`)
---
name: add-matrix
description: Add Matrix channel integration via Chat SDK. Works with any Matrix homeserver.
---

# Add Matrix Channel

Adds Matrix support via the Chat SDK bridge. NanoClaw doesn't ship channels in
trunk — this skill copies the Matrix adapter in from the `channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent
reads the prose and applies them, and a parser can apply them deterministicall

### Mattermost (`add-mattermost`)
---
name: add-mattermost
description: Add a self-hosted or cloud Mattermost bot channel through the Chat SDK bridge, reusing a healthy server when available and linking to official server setup guidance when needed.
---

# Add Mattermost Channel

Adds Mattermost DMs, channels, threads, files, reactions, and interactive
approval cards. Messages arrive over Mattermost's WebSocket; card clicks return
to NanoClaw over an authenticated HTTP callback. 

### Mnemon (`add-mnemon`)
---
name: add-mnemon
description: Add persistent graph-based memory via mnemon. Agents recall past context before responding and remember insights after each turn.
---

# Add Mnemon — Persistent Memory

Installs [mnemon](https://github.com/mnemon-dev/mnemon) in the agent container image. On each container start, `mnemon setup` registers Claude Code hooks that surface relevant memory before the agent responds and store new insights after each turn

### Ollama Provider (`add-ollama-provider`)
---
name: add-ollama-provider
description: Route a NanoClaw agent group to a local Ollama model instead of the Anthropic API. Ollama speaks the Anthropic API natively (v1/messages), so no provider code changes are needed — just env var overrides and a model setting. Use when the user wants to run their agent locally, cut API costs, or experiment with open-weight models. See docs/ollama.md for background.
---

# Add Ollama Provider

Routes an agen

### Ollama Tool (`add-ollama-tool`)
---
name: add-ollama-tool
description: Add Ollama MCP server so the container agent can call local models and optionally manage the Ollama model library.
---

# Add Ollama Integration

This skill adds a stdio-based MCP server that exposes local [Ollama](https://ollama.com) models as tools for the container agent. Claude remains the orchestrator but can offload work to local models served by the Ollama daemon on the host, and can optionally manage

### Onecli (`add-onecli`)
---
name: add-onecli
description: Install or refresh OneCLI as NanoClaw's gateway provider. Use when setup selects OneCLI, an existing OneCLI-backed install is migrated to the gateway seam, or its runtime, approval bridge, setup, and agent guidance must be restored from the in-tree package.
---

# Add OneCLI gateway

This skill owns the full OneCLI integration. NanoClaw core supplies the generic gateway seam and existing skill engine.

## Install

### Opencode (`add-opencode`)
---
name: add-opencode
description: Use OpenCode as an agent provider. OpenRouter, OpenAI, Google, DeepSeek, etc. via OpenCode config — not the Anthropic Agent SDK. Per group via `ncl groups config update --provider opencode`; host passes OPENCODE_* and XDG mount when spawning containers.
metadata:
  nanoclaw-provider: opencode
  nanoclaw-provider-label: OpenCode
  nanoclaw-provider-hint: Open-source provider router
  nanoclaw-provider-offered: '

### Product E2E Eval (`add-product-e2e-eval`)
---
name: add-product-e2e-eval
description: Add or extend a Paperclip full-stack runner E2E workflow, fixture, matcher, or report evidence path for local or Daytona execution.
---

# Add a Product E2E Eval

Use this skill for **Product E2E Evals**: real Chromium, Paperclip server,
database, runner, provider, and optionally Daytona. Everyday Workflows are in
this family even when their packaged results are imported into Evalbook. Runner
protocol c

### Resend (`add-resend`)
---
name: add-resend
description: Add Resend (email) channel integration via Chat SDK.
---

# Add Resend Email Channel

Connect NanoClaw to email via Resend for async email conversations. NanoClaw
doesn't ship channels in trunk — this skill copies the Resend adapter in from the
`channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent reads
the prose and applies them, and a parser can apply them deterministic

### Rtk (`add-rtk`)
---
name: add-rtk
description: Install rtk token-compression proxy into agent containers. Routes Bash tool calls through rtk for 60–90% token savings on dev commands (git, cargo, pytest, docker, kubectl, etc.).
---

# Add rtk

Install [rtk](https://github.com/rtk-ai/rtk) — a CLI proxy delivering 60–90% token savings on common dev commands (git, cargo, pytest, docker, kubectl, etc.) — and wire it transparently into agent containers via the Claude 

### Runner Eval (`add-runner-eval`)
---
name: add-runner-eval
description: Add or extend a Paperclip Runner protocol evaluation definition, roster, assertion, or report fixture with provenance and narrow validation.
---

# Add a Runner Eval

Use this skill for the **Runner Evals** family: a real Runner/provider session
against a seeded mock control plane. Product browser/server/database/Daytona
coverage belongs in [add-product-e2e-eval](../add-product-e2e-eval/SKILL.md).

Locate th

### Signal (`add-signal`)
---
name: add-signal
description: Add Signal channel integration via signal-cli device-link. Native adapter — no Chat SDK bridge.
---

# Add Signal Channel

Adds Signal support via a native adapter that speaks JSON-RPC to a
[signal-cli](https://github.com/AsamK/signal-cli) daemon — no Chat SDK bridge,
only Node.js builtins. NanoClaw links to Signal as a *secondary device* on your
existing phone: no new number, no bot API. Your assistant sends and

### Slack (`add-slack`)
---
name: add-slack
description: Add Slack channel integration via Chat SDK.
---

# Add Slack Channel

Adds Slack support via the Chat SDK bridge. Trunk ships no channels — this skill
copies the Slack channel layer (adapter, shared lib, bot-inbound guard,
provisioning core, container skills) in from the `channels` branch. The **Apply**
steps carry `nc:` directive fences (an agent applies the prose, a parser the
directives); all idempotent.

This 

### Tavily Tool (`add-tavily-tool`)
---
name: add-tavily-tool
description: Add Tavily Search and Extract as keyless remote MCP tools for selected NanoClaw agent groups. Use when installing Tavily web search or URL extraction without an API key.
---

# Add Tavily Tool

Install the pinned `mcp-remote` bridge in the agent image and register Tavily's
remote MCP server for each selected agent group. The MCP server supplies its
tool descriptions and input schemas at runtime.

The registe

### Teams (`add-teams`)
---
name: add-teams
description: Add Microsoft Teams channel integration via Chat SDK.
---

# Add Microsoft Teams Channel

Adds Microsoft Teams support via the Chat SDK bridge — interactive chat in team
channels, group chats, and direct messages. NanoClaw doesn't ship channels in
trunk — this skill copies the Teams adapter in from the `channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent
reads the prose a

### Telegram (`add-telegram`)
---
name: add-telegram
description: Add Telegram channel integration via Chat SDK.
---

# Add Telegram Channel

Adds Telegram bot support via the Chat SDK bridge. NanoClaw doesn't ship
channels in trunk — this skill copies the Telegram adapter, its pairing helper,
and their tests in from the `channels` branch. The
`pair-telegram` setup step is maintained in trunk, so it is not copied here.

The mechanical steps under **Apply** carry `nc:` directi

### Vercel (`add-vercel`)
---
name: add-vercel
description: Add Vercel deployment capability to NanoClaw agents. Installs the Vercel CLI in agent containers and sets up OneCLI credential injection for api.vercel.com. Use when the user wants agents to deploy web applications to Vercel.
---

# Add Vercel

This skill gives NanoClaw agents the ability to deploy web applications to Vercel. It installs the Vercel CLI in agent containers and configures OneCLI to inject Vercel cr

### Webex (`add-webex`)
---
name: add-webex
description: Add Webex channel integration via Chat SDK.
---

# Add Webex Channel

Adds Cisco Webex support via the Chat SDK bridge. NanoClaw doesn't ship channels
in trunk — this skill copies the Webex adapter in from the `channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent
reads the prose and applies them, and a parser can apply them deterministically
from the same document. Every d

### Wechat (`add-wechat`)
---
name: add-wechat
description: Add WeChat (personal) channel integration via Tencent's official iLink Bot API. Uses long-polling and QR scan — no webhook, no ToS risk, no paid token.
---

# Add WeChat Channel

Adds WeChat support via **iLink Bot API** — the first-party Tencent API for personal WeChat bots (different from WeCom / Official Account).

**Why this is different from wechaty/PadLocal:**

- Official Tencent API — no ToS violation, no 

### Whatsapp (`add-whatsapp`)
---
name: add-whatsapp
description: Add WhatsApp channel via native Baileys adapter. Direct connection — no Chat SDK bridge. Uses QR code or pairing code for authentication.
---

# Add WhatsApp Channel

Adds WhatsApp support via the native Baileys adapter — a direct WhatsApp Web
connection, no Chat SDK bridge. NanoClaw doesn't ship channels in trunk — this
skill copies the WhatsApp adapter in from the `channels` branch.

The mechanical steps unde

### Whatsapp Cloud (`add-whatsapp-cloud`)
---
name: add-whatsapp-cloud
description: Add WhatsApp Business Cloud API channel via Chat SDK. Official Meta API.
---

# Add WhatsApp Cloud API Channel

Connect NanoClaw to WhatsApp via the official Meta WhatsApp Business Cloud API.
NanoClaw doesn't ship channels in trunk — this skill copies the WhatsApp Cloud
adapter in from the `channels` branch.

The mechanical steps under **Apply** carry `nc:` directive fences: an agent reads
the prose and a

