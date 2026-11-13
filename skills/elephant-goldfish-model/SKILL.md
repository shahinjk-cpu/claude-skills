---
name: elephant-goldfish-model
description: Google's open-source framework and methodology for designing and reviewing software with AI agents. Uses a long-memory Elephant for brainstorming and drafting specifications, and zero-context Goldfish sub-agents for adversarial edge-case reviews, with human architectural sign-off (egm-brainstorm, egm-draft, egm-review, egm-resolve, egm-review-loop, egm-bootstrap, egm-drift-report).
metadata:
  version: 1.0.0
---

# Elephant-Goldfish Model (EGM)

> **"Design with an elephant. Review with a goldfish."**  
> Developed at Google for rigorous, hallucination-resistant spec-driven software development with AI agents.

Official repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\elephant-goldfish-model`  
Website: `https://egm.dev`

## The Core Problem It Solves

When developing complex systems with an AI coding agent, long single-session chat threads accumulate context pollution, confirmation bias, and conversational inertia. The model agrees with itself, assumes unstated requirements, and glosses over subtle edge cases.

EGM solves this by decoupling the engineering process into three distinct roles:

1. **The Elephant (Long Context / Vision)**:
   - Holds end-to-end architectural vision and product requirements.
   - Brainstorms deeply with the engineer and drafts modular, formal specifications.
2. **The Goldfish (Zero Context / Fresh Eyes Reviewers)**:
   - Brand-new, isolated sub-agents spawned with **zero** prior conversational history.
   - Review only the drafted specification and referenced codebase files.
   - Hunt aggressively for unstated assumptions, failure modes, missing error paths, and security gaps without bias.
3. **The Human (Architectural Authority)**:
   - Evaluates the trade-offs surfaced by the Goldfish reviewers.
   - Gives final sign-off before any implementation code is written.

## The 7 EGM Workflow Skills

| Skill | Trigger / Command | Stage & Purpose |
|---|---|---|
| `egm-brainstorm` | `/egm-brainstorm` | **1. Discovery**: Explore feature concepts, clarify problem statements, determine scope, and align on constraints with the Elephant. |
| `egm-draft` | `/egm-draft` | **2. Authoring**: Draft the formal technical specification document section-by-section using the structured concept brief. |
| `egm-review` | `/egm-review` | **3. Critique**: Dispatch independent, fresh-eyed Goldfish sub-agents to rigorously audit the specification against defined standards. |
| `egm-resolve` | `/egm-resolve` | **4. Mediation**: Triage Goldfish findings, resolve discrepancies, update the spec, and prepare it for human approval. |
| `egm-review-loop` | `/egm-review-loop` | **General Review**: Run multi-persona review loops across general documents, PRs, or architecture designs. |
| `egm-bootstrap` | `/egm-bootstrap` | **Onboarding**: Scan an existing legacy repository and scaffold hierarchical specification directories and README manifests. |
| `egm-drift-report` | `/egm-drift-report` | **Verification**: Audit written implementation code against approved design specifications to detect architectural drift. |

## Quickstart: The Feature Design Loop

1. Align on requirements:
   ```bash
   /egm-brainstorm "Add real-time websocket presence notifications to user dashboard"
   ```
2. Generate the design specification:
   ```bash
   /egm-draft
   ```
3. Run the Goldfish review audit:
   ```bash
   /egm-review
   ```
4. Resolve critiques with human approval:
   ```bash
   /egm-resolve
   ```
