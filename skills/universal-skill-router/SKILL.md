---
name: universal-skill-router
description: >-
  Master Router and Orchestrator for all 5,101+ local skills across Web, Mobile, AI Agents,
  Desktop Automation, DevOps, Security, UI/UX, Data Science, and GameDev. Automatically
  identifies, routes, and activates the exact specialized skill(s) for any user request
  from the Master Skill Catalog (skills_manifest.json). Use whenever beginning any coding,
  design, research, automation, or debugging task.
---

# Universal Skill Router & Orchestrator

This is the central routing engine for the **5,101 installed skills** located in your environment.

Because LLM context limits prevent loading all 5,100+ skills simultaneously into the system prompt, this router dynamically indexes, identifies, and activates the required skills **on-demand**.

---

## ⚡ Routing Workflow

Before starting work on any user request:

### Step 1: Detect & Query Matching Skills
Run the router query tool or check the manifest:
```bash
python skill_router.py "<task_keywords>"
```
Or read `skills_manifest.json`.

### Step 2: Read Chosen Skill(s)
Once the matching skill is identified (e.g., `frontend-dashboard-pro`, `playwright-e2e-automation`, `browser-use-open-source`, `microsoft-ufo`), use `read_file` on its `SKILL.md`:
```
read_file(Path: ".../skills/<skill-name>/SKILL.md")
```

### Step 3: Compose & Execute
- Adopt the persona, architectural rules, code standards, and verification steps prescribed in the skill.
- Combine multi-disciplinary skills when appropriate (e.g. `spec-driven-development` + `nextjs-react-performance` + `clean-code`).
- If subagents are involved, ensure the subagent's prompt instructs it to read the specific `SKILL.md`.

---

## 🛡️ Core 22 Mandatory Always-Active Skills (Hər Əməliyyatda Məcburi Qaydalar)

Regardless of the specific task or domain, the following 22 foundational skills are **PERMANENTLY ACTIVE** across all turns:

1. **`token-budget-advisor`**: Continuously monitors context limits, prevents context window bloat, and optimizes message conciseness.
2. **`compact-conversation`**: Dynamically compacts redundant dialogue and tool outputs while retaining 100% of architectural decisions and state.
3. **`ai-session-optimizer`**: Minimizes turn roundtrips, enforces batched parallel tool calls, and eliminates idle turns.
4. **`prompt-caching-strategy`**: Exploits prompt prefix caching to maximize cache hits and minimize token costs.
5. **`clean-code`**: Pragmatic, direct, standard-library-first code. No gratuitous abstractions, no conversational inline comments.
6. **`anti-slop-ui`**: Strictly prohibits generic AI aesthetics (cookie-cutter rounded buttons, purple glowing cards, unstyled typography).
7. **`memory-safety-patterns`**: Enforces strict allocation discipline, stack vs heap optimization, and leak prevention.
8. **`file-system-memory`**: Uses disk files and structured JSON state for persistent memory across sessions rather than context pollution.
9. **`error-handling-patterns`**: Resilient exception handling, exponential backoff, and graceful degradation on failure.
10. **`verification-loop`**: Mandatory compile/run/diff validation before marking tasks complete. Never declare victory without passing tests.
11. **`gateguard`**: Fact-forcing gate that stops unverified edits until existing interfaces and dependencies are inspected.
12. **`zero-hallucination-coder`**: Strict rule against guessing APIs, package names, or file paths. Always inspect files first.
13. **`code-simplification`**: Relentlessly reduces complexity and cyclomatic depth; simplifies architecture wherever possible.
14. **`security-best-practices`**: Secret protection, credential isolation, and safe shell command execution.
15. **`universal-skill-router`**: The brain that dynamically matches and loads specialized skills based on task context.
16. **`session-guard`**: Preserves execution state across agent handoffs, system restarts, and long-running workflows.
17. **`work_efficiently`**: Issues all independent tool calls in parallel within a single turn. Never one call per turn.
18. **`git-safety-net`**: Creates atomic, well-described conventional commits and preserves rollback capability.
19. **`locked-references`**: Strictly adheres to user-locked constraints, constants, and business domain boundaries without drift.
20. **`written-gates-generation`**: Establishes clear milestones and measurable acceptance criteria before code execution.
21. **`inferssd`**: Expert dynamic streaming and low-memory offloading patterns for heavy local models.
22. **`typegpu`**: Type-safe hardware execution standards for modern compute and WebGPU shaders.

---

## 📚 Master Index Reference
- Full Markdown Directory: `skills_index.md`
- Searchable JSON Manifest: `skills_manifest.json`
- Router Search Utility: `skill_router.py`
