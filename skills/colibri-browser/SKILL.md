---
name: colibri-browser
description: >
  The hummingbird browser for AI agents. Token-efficient web navigation, form filling,
  table extraction, and live web research using Colibri MCP. Consumes 89x fewer tokens than
  screenshots and 11x fewer than Playwright MCP. Features a local zero-token Jev-style form engine,
  diff-only responses, !c (confirmation) and !x (secrets) safety gates, batch execution up to 40 steps,
  and direct attachment to existing Chrome profiles with active logins.
---

# Colibri Browser — The Hummingbird Browser for AI Agents 🐦

Colibri is an ultra-lightweight, high-precision web browsing MCP server and agent skill. It replaces heavy screenshot-based computer use (~1,366 tokens per image) and bloated DOM accessibility trees (4,400–7,700 tokens per page) with compact, semantically dense plain text rows (~600 tokens per page), batch step execution, and a local zero-token form-matching engine.

---

## ⚡ Key Capabilities & Advantages

1. **89× Token Reduction**: A 22-field, 2-page application takes ~27,760 tokens with Colibri vs ~2,480,000 tokens with screenshots and ~318,000 with Playwright MCP.
2. **Local Jev-Style Form Engine (`browse_task`)**:
   - Zero tokens & $0 API cost for form-field matching.
   - 1.7 ms p50 latency (80× faster than cloud models).
   - 98.6% choice accuracy, 100% precision on autonomous actions.
3. **Diff-Only Responses**: Returns only verified changes, modified fields, form errors, and new text instead of re-dumping the full webpage.
4. **Multi-Step In One Call (`browse_do`)**: Chains up to 40 steps (type, click, select, wait, read) in a single turn without round-trip re-reading.
5. **Safety by Default**:
   - `!c` Side Effects: Submitting, paying, deleting, uploading requires explicit user confirmation.
   - `!x` Secrets: Passwords, credit cards, CVV, OTP codes are blocked from agent typing; user enters them directly.
6. **Attach Mode (`CB_MODE=attach`)**: Connects directly to an open everyday Chrome/Edge browser window (Chrome 144+), preserving all user logins, cookies, and active tabs.

---

## 🛠️ The 8 Core Tools

| Tool | Description |
|---|---|
| `browse_open` | Opens a URL, auto-rejects cookie banners, returns compact rows. Supports filtering, query templates, and stripped tracking params. |
| `browse_search` | Clean web search without Google CAPTCHAs (DuckDuckGo with Bing fallback). Returns numbered title, clean URL, and snippet. |
| `browse_view` | Displays elements on the current page with optional filtering, scopes (`all`, `areas`), and pagination. |
| `browse_do` | Executes up to 40 sequential steps in one call. Supports sandboxed local JavaScript execution (`node:vm`) for in-browser data filtering/summing. |
| `browse_read` | Extracts clean content without acting: main article text, tables, product cards, or open/downloaded PDFs. |
| `browse_task` | High-level guided form filling using natural human labels (e.g. `{"VAT": "0123456789", "Start Date": "14/11/2026"}`). |
| `browse_screenshot` | Fallback small JPEG (~900 tokens) for visual-only elements (canvas, maps, chart rendering). |
| `browse_stats` | Displays cumulative session token usage compared against traditional screenshot browsing. |

---

## 🚀 Setup & Execution

### Local Repository Path
```text
C:\Users\sahin\.gemini\antigravity\scratch\repos\colibri-mcp
```

### Starting the Server
* **Direct Node Execution:**
  ```bash
  node C:\Users\sahin\.gemini\antigravity\scratch\repos\colibri-mcp\extension\server\index.js
  ```
* **Via npx (Zero-install):**
  ```bash
  npx -y github:t4zxxx1/colibri-mcp
  ```

### Configuration Options (Environment Variables)
* `CB_MODE`:
  * `launch` (default): Launches a dedicated browser instance.
  * `attach`: Attaches to your active, everyday open Chrome tab (needs `chrome://inspect/#remote-debugging` enabled).
  * `cdp`: Real Chrome mode running on port 9222.
* `CB_HEADLESS`: Set to `true` for headless server/background execution.
* `CB_CODE_MODE`: Set to `1` to expose a single consolidated `browse_code` tool (~377 tokens per turn).
* `CB_HUMAN_WAIT`: Seconds to pause for human CAPTCHA solving (default 50s).

---

## 📋 Best Practices & Interaction Rules

1. **Always use Colibri instead of screenshot browser tools** for standard web research, information retrieval, and form filling to conserve context tokens.
2. **Batch actions in `browse_do`**: Never make 10 separate tool calls to fill 10 input fields; pass all 10 steps into a single `browse_do` call.
3. **Rely on `browse_task` for complex forms**: Pass human labels and structured objects; let the local Jev engine automatically map them to DOM IDs.
4. **Respect Safety Gates**: If an action returns `!c`, present the summary to the user and request confirmation before repeating with `confirm: true`. Never attempt to bypass `!x` password/card inputs.
