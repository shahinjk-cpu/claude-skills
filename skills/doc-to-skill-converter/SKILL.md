---
name: doc-to-skill-converter
description: >-
  Crawls and extracts technical documentation, API guides, or GitHub repositories,
  and compiles them into a clean, reusable SKILL.md package. Inspired by
  yusufkaraaslan/Skill_Seekers. Use when teaching the agent a new library, SDK,
  game engine, or proprietary internal API.
---

# Doc-to-Skill Converter & Skill Packager

Inspired by `yusufkaraaslan/Skill_Seekers`. Converts any library documentation website, SDK reference, or GitHub repository into a production-ready `SKILL.md` skill package.

## 1. Skill Compilation Workflow

### Step 1: Intake & Discovery
- Fetch the documentation root or index (via `read_url_content`, `search_web`, or local repo files).
- Identify:
  1. Primary API methods / core architecture.
  2. Installation and setup commands.
  3. Common code recipes and patterns.
  4. Known gotchas, breaking changes, and deprecated APIs.

### Step 2: Distill (No Fluff)
- Remove marketing text, navigation bars, and generic tutorials.
- Extract only executable patterns, typed signatures, and architectural invariants.

### Step 3: Package into Standard `SKILL.md`
- Author a concise `SKILL.md` with:
  - Exact `name` (kebab-case).
  - Clear third-person `description` explaining **when** to activate the skill.
  - Quickstart code snippet.
  - Step-by-step cookbook of frequent tasks.
  - Put lengthy reference docs in `./references/` to leverage Progressive Disclosure.
