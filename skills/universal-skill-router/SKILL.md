---
name: universal-skill-router
description: >-
  Master Router and Orchestrator for all 940+ local skills across Web, Mobile, AI Agents,
  Desktop Automation, DevOps, Security, UI/UX, Data Science, and GameDev. Automatically
  identifies, routes, and activates the exact specialized skill(s) for any user request
  from the Master Skill Catalog (skills_manifest.json). Use whenever beginning any coding,
  design, research, automation, or debugging task.
---

# Universal Skill Router & Orchestrator

This is the central routing engine for the **942+ installed skills** located at `C:/Users/shahin.karimov/.gemini/config/skills/`.

Because LLM context limits prevent loading all 940+ skills simultaneously into the system prompt, this router dynamically indexes, identifies, and activates the required skills **on-demand**.

---

## ⚡ Routing Workflow

Before starting work on any user request:

### Step 1: Detect & Query Matching Skills
Run the router query tool or check the manifest:
```powershell
python C:/Users/shahin.karimov/.gemini/config/skill_router.py "<task_keywords>"
```
Or read `C:/Users/shahin.karimov/.gemini/config/skills_manifest.json`.

### Step 2: Read Chosen Skill(s)
Once the matching skill is identified (e.g., `frontend-dashboard-pro`, `playwright-e2e-automation`, `browser-use-open-source`, `microsoft-ufo`), use `read_file` on its `SKILL.md`:
```
read_file(Path: "C:/Users/shahin.karimov/.gemini/config/skills/<skill-name>/SKILL.md")
```

### Step 3: Compose & Execute
- Adopt the persona, architectural rules, code standards, and verification steps prescribed in the skill.
- Combine multi-disciplinary skills when appropriate (e.g. `spec-driven-development` + `nextjs-react-performance` + `taste-skill`).
- If subagents are involved, ensure the subagent's prompt instructs it to read the specific `SKILL.md`.

---

## 📚 Master Index Reference
- Full Markdown Directory: [skills_index.md](file:///C:/Users/shahin.karimov/.gemini/config/skills_index.md)
- Searchable JSON Manifest: [skills_manifest.json](file:///C:/Users/shahin.karimov/.gemini/config/skills_manifest.json)
- Router Search Utility: [skill_router.py](file:///C:/Users/shahin.karimov/.gemini/config/skill_router.py)
