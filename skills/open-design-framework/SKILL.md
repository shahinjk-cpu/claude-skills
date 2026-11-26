---
name: open-design-framework
description: Open Design (OD) master framework covering UI component generation, design system refinement, Next.js / React / Vue exports, and Figma migrations.
---

# Open Design (OD) Master Framework

Automated design-to-code workflows, framework exports, and design system governance.

## Modules & Generators
### Code Migration (`od-code-migration`)
---
name: od-code-migration
description: Default reference pipeline for the code-migration taskKind — code-import → design-extract → token-map → rewrite-plan → patch-edit ↔ build-test devloop → diff-review → handoff.
od:
  scenario: code-migration
  mode: scenario
---

# od-code-migration (scenario)

Spec §1 / §10.1 / §20.3 / §21.3.2 / §23.3.3: the canonical
code-migration flow. The pipeline cannot ship an `accept` decision
without a passing buil

### Contribute (`od-contribute`)
---
name: od-contribute
description: One-click contribution flow for OpenDesign (nexu-io/open-design) — even for non-coders. Pick one of four cards (ship a Skill or Design System you made with OD; translate docs; fix a typo / write a blog; report a bug), the agent validates and opens a PR (or issue) for you. Trigger words contribute to open design, ship my OD skill, ship my OD design system, translate OD docs, report an OD bug, od-contribute.
all

### Default (`od-default`)
---
name: od-default
description: Hidden fallback scenario for free-form Home prompts. Infer the task type and ask only when routing is materially ambiguous.
od:
  scenario: default-router
  mode: scenario
---

# od-default (hidden scenario)

This plugin runs only when the user types a free-form Home prompt without
choosing one of the visible category chips. It is the design-engine
fallback, not a visible catalog entry.

## Route first; clarify o

### Design Refine (`od-design-refine`)
---
name: od-design-refine
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Design Refine

Use this plugin when the user wants to improve an existing OpenDesign artifact rather than create a new one.

## Workflow

1. Inspect the current artifact and identify the highest-leverage refinement target.
2. Pick one direction before editing: clarity, hierarchy, polish, accessibility, responsiveness, or fidelity.
3.

### Figma Migration (`od-figma-migration`)
---
name: od-figma-migration
description: Default reference pipeline for the figma-migration taskKind — figma-extract → token-map → generate → critique.
od:
  scenario: figma-migration
  mode: scenario
---

# od-figma-migration (scenario)

Spec §1 / §10.1 / §21.3.1 / §23.3.3: the canonical figma-migration
flow. The pipeline is sequenced so each stage's output is the next
stage's input — `figma-extract` writes `figma/tree.json`,
`token-map` writes

### Media Generation (`od-media-generation`)
---
name: od-media-generation
description: Default reference pipeline for image, video, and audio projects — routes through media-image / media-video / media-audio atoms based on the project kind, wraps the output in a live artifact, and devloops on critique-theater until the score converges.
od:
  scenario: media-generation
  mode: scenario
---

# od-media-generation (scenario)

This scenario plugin is the bundled default for projects whose
`met

### New Generation (`od-new-generation`)
---
name: od-new-generation
description: Default reference pipeline for the new-generation taskKind — discovery → plan → generate → critique with a critique-theater devloop.
od:
  scenario: new-generation
  mode: scenario
---

# od-new-generation (scenario)

Spec §10.1 / §23.3.3: when a plugin omits `od.pipeline`, the daemon
falls back to this scenario plugin's pipeline. Replacing the
default for an enterprise / vertical edition is now a content 

### Next Media Inputs (`od-next-media-inputs`)
---
name: od-next-media-inputs
en_name: "OD Next Media Inputs"
zh_name: "OD Next 素材输入"
description: |
  Prepare required media inputs within an existing OD Next plan. Reuse capability
  evidence, acquire and measure assets efficiently, and resolve asynchronous
  jobs without removing required content or weakening quality standards.
triggers:
  - "OD Next media inputs"
  - "prepare required media assets"
  - "reuse media capability results"
od:
  

### Next Strategy (`od-next-strategy`)
---
name: od-next-strategy
description: Bundled OD Next V2 strategy entrypoint for request-led planning and Build execution.
---

# OD Next Strategy V2

This bundled scenario packages the stable content used by the internal OD Next
planning and Build recipe. It is not a portable strategy selector and does not
activate itself.

When Open Design supplies a validated V2 binding, load the assets in this order:

1. `assets/core-system-prompt.md`
2. `a

### Nextjs Export (`od-nextjs-export`)
---
name: od-nextjs-export
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Export To Next.js

Use this plugin when the user wants to hand an accepted OpenDesign artifact to a Next.js App Router project.

## Workflow

1. Decide whether the result should be a route, layout fragment, or reusable component.
2. Keep components server-first unless interactivity, browser APIs, or client state require `'use client'

### Plugin Authoring (`od-plugin-authoring`)
---
name: od-plugin-authoring
description: Guided scenario for creating an OpenDesign plugin folder that can be installed into My plugins.
od:
  scenario: plugin-authoring
  mode: scenario
---

# od-plugin-authoring (scenario)

Use this scenario when the user wants to create their own OpenDesign plugin.

## Required outcome

Produce a folder named `generated-plugin/` in the active project workspace.
At minimum, the folder must contain:

- `SKILL.

### Plugin Contribute Open Design (`od-plugin-contribute-open-design`)
---
name: od-plugin-contribute-open-design
description: Open a pull request adding a local OpenDesign plugin to the OpenDesign community catalog using gh CLI.
triggers:
  - contribute plugin
  - open design pr
  - github pull request
od:
  mode: utility
  platform: desktop
  scenario: plugin-sharing
---

# Contribute Plugin to OpenDesign

Use this workflow when the active project contains a copied plugin folder and the user wants to propose it fo

### Plugin Publish Github (`od-plugin-publish-github`)
---
name: od-plugin-publish-github
description: Publish a local OpenDesign plugin to a new public GitHub repository using gh CLI.
triggers:
  - publish plugin
  - github repo
  - open source plugin
od:
  mode: utility
  platform: desktop
  scenario: plugin-sharing
---

# Publish Plugin to GitHub

Use this workflow when the active project contains a copied plugin folder and the user wants it published as a new public GitHub repository.

## Workflo

### React Export (`od-react-export`)
---
name: od-react-export
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Export To React

Use this plugin when the user wants to hand an accepted OpenDesign artifact to a React app.

## Workflow

1. Inspect the current artifact and identify the smallest React component boundary that preserves the design.
2. Produce React 18 + TypeScript code with clear props only for content or state that is likely to vary

### Share To Community (`od-share-to-community`)
---
name: od-share-to-community
description: Package the user's just-finished work as an OpenDesign plugin without asking for fields the project files already answer, then surface the existing Add-to-My-plugins / Open-Design-PR buttons.
od:
  scenario: plugin-sharing
  mode: scenario
---

# od-share-to-community (scenario)

Triggered by the post-completion "Share to OpenDesign" submission action. The user just finished a piece of work in this pro

### Tune Collab (`od-tune-collab`)
---
name: od-tune-collab
description: Default reference pipeline for the tune-collab taskKind — pick a direction, patch-edit the existing artifact, critique, hand off.
od:
  scenario: tune-collab
  mode: scenario
---

# od-tune-collab (scenario)

Spec §1 / §10.1 / §21.5 / §23.3.3: the canonical "iterate on an
existing artifact" flow. Inherits `parentArtifactId` from the
project metadata so the produced artifact's
`ArtifactManifest.parentArtifactI

### Vue Export (`od-vue-export`)
---
name: od-vue-export
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Export To Vue

Use this plugin when the user wants to hand an accepted OpenDesign artifact to a Vue 3 project.

## Workflow

1. Convert the artifact into a Vue 3 single-file component with a clear template, script, and style boundary.
2. Use Composition API only when the component needs state, lifecycle hooks, or derived values.
3. Pref

### Web Effect Extractor (`od-web-effect-extractor`)
---
name: od-web-effect-extractor
description: Extract visual effects, animation systems, Canvas/WebGL/Shader behavior, and interaction details from a reference website, then rebuild them as an editable OpenDesign web artifact.
od:
  scenario: web-effect-extraction
  mode: scenario
---

# Web Effect Extractor

Use this plugin when the user gives a website URL and asks OpenDesign to recreate, remix, or learn from its visual effects. It is especial

