---
name: nvidia-usd-content-workflows
description: Master 3D asset pipeline and Universal Scene Description (USD) workflow suite for Nvidia Omniverse, SimReady assets, geometry repair, material authoring, and physics simulation.
---

# Nvidia USD Content & 3D Asset Pipeline Master Suite

End-to-end Universal Scene Description (USD) asset production, repair, material binding, physics validation, and scene assembly.

## Pipeline Workflows
### Articulation (`content-workflow-articulation`)
---
name: content-workflow-articulation
description: >-
  Run durable Joint Agent articulation-v1 workflows that bind usd-cli
  inspection evidence, pause for explicit review, resume without repeating
  completed phases, author only approved revolute or prismatic joints, and
  verify exact saved USDZ readback. Use when prompt-driven joint, drawer,
  hinge, slider, mechanism, or articulation work needs the isolated agentic
  workspace.
version: "0

### Asset (`content-workflow-asset`)
---
name: content-workflow-asset
description: >-
  Run one prompt-specific asset workflow through a sole outer reasoner that
  supplies and freezes a typed public-leaf dependency graph. Use for selective,
  resumable asset composition without a built-in domain or stage order. Explicit
  compatibility-fixed mode still composes Geometry preparation, articulation
  review, material assignment, bounded texture
  generation, physics authoring, validat

### Asset Task Processing (`content-workflow-asset-task-processing`)
---
name: content-workflow-asset-task-processing
description: Plan and execute one or more domain tasks over finalized decomposed scene assets, with an immutable eligible work matrix, independent per-item results, agent-chosen ordering, durable decision memory, and a sealed Workflow 2 handoff. Use after scene decomposition for material, physics, articulation, geometry, labeling, or mixed asset processing.
metadata:
  author: NVIDIA Omniverse
---


### Cli (`content-workflow-cli`)
---
name: content-workflow-cli
description: >-
  Default launcher for supported Content Agent tasks from the repository root,
  including deterministic Geometry handoff, conversion, material or physics
  authoring, texture, segmentation, validation, large scenes, durable
  articulation, composed assets, review, and resume. Use fixed-pipeline app CLIs
  only when the user explicitly requests fixed control flow, YAML configuration,
  REST, benchmar

### Convert To Usd (`content-workflow-convert-to-usd`)
---
name: content-workflow-convert-to-usd
description: Use before USD-based content workflows when a source asset must be routed to OpenUSD through the existing content-workflow-cli conversion workflow, including dependency preflight, existing USD passthrough, CAD/mesh, URDF, MuJoCo/MJCF, durable reports, blocked results, and downstream USD handoff.
metadata:
  author: NVIDIA Omniverse
---

# content-workflow-convert-to-usd

Use this skill when a

### Geometry (`content-workflow-geometry`)
---
name: content-workflow-geometry
description: Complete a provider-neutral Geometry handoff from CAD, mesh, generated, or existing USD. Use when a workflow needs source lineage, prepared and optimized geometry, OVRTX and USD evidence, semantic parts or parameters, and content_agents_manifest.json without claiming final physics, runtime behavior, or SimReady status.
metadata:
  author: NVIDIA Omniverse
---

# Content Workflow Geometry

Own Geome

### Geometry Repair (`content-workflow-geometry-repair`)
---
name: content-workflow-geometry-repair
description: Complete a source-preserving Geometry repair workflow for imported CAD, mesh, USD, URDF, or MJCF geometry with bounded topology work, collision separation, and explicit evidence. Use when a user or parent workflow needs a durable certified, conditional, rejected, blocked, failed, or cancelled geometry-repair outcome rather than one isolated diagnosis or edit.
metadata:
  author: NVIDIA Omniv

### Large Scene (`content-workflow-large-scene`)
---
name: content-workflow-large-scene
description: Coordinate a large OpenUSD scene through decomposition, per-asset domain processing, and original-topology collection using durable run state and deterministic handoff gates. Use when a scene is too large or repetitive to process monolithically, when material/physics/other tasks must run over decomposed representatives, or when resuming or repairing a three-phase large-scene run.
metadata:
  aut

### Material (`content-workflow-material`)
---
name: content-workflow-material
description: Default material-authoring workflow for supported, unqualified USD material tasks. Use with usd-cli when a long-running coding agent assigns visual or non-visual materials, uses libraries, performs iterative visual review, and produces canonical artifacts and validation evidence; use material-agent-* only for explicit fixed pipeline requests.
metadata:
  author: NVIDIA Omniverse
---

# content-work

### Mesh Segmentation (`content-workflow-mesh-segmentation`)
---
name: content-workflow-mesh-segmentation
description: Segment one fused triangular USD mesh into logical mesh prims by identifying visible parts, freezing deterministic geometry fragments, choosing per part between a registered image-mask seed produced through the image-generation skill and direct agentic signed fragment selection, and falsifying each provisional result with signed confuser evidence and held-out multi-view review before locki

### Physics (`content-workflow-physics`)
---
name: content-workflow-physics
description: Own agent-driven physics planning, policy, component decisions, guarded repair, authoring, optional attested VoMP mass properties, simulation-backed validation, refinement, acceptance, and durable artifacts for a USD asset, using usd-cli only for low-level scene operations.
metadata:
  author: NVIDIA Omniverse
---

# content-workflow-physics

Use this skill when a long-running coding agent must infe

### Physics External Tuning (`content-workflow-physics-external-tuning`)
---
name: content-workflow-physics-external-tuning
description: Use when a long-running coding agent owns the outer loop of external-runtime (BYOR) physics refinement — requesting budgeted qualification-gated tune-external sweeps through the wrapper broker, visually judging rendered rollout evidence against a behavior goal, revising the active parameter search, and writing digest-bound accept/revise/stop decisions.
metadata:
  author: NVIDIA Omni

### Scene Collection (`content-workflow-scene-collection`)
---
name: content-workflow-scene-collection
description: Collect validated decomposed-asset task results back onto original OpenUSD topology through domain-specific projection, representative propagation, conflict harmonization, independent domain layers, composition, and a sealed Workflow 3 handoff. Use after asset-task processing or when repairing collection for material, physics, articulation, geometry, or mixed-domain outputs.
metadata:
  aut

### Scene Decomposition (`content-workflow-scene-decomposition`)
---
name: content-workflow-scene-decomposition
description: Decompose a large OpenUSD scene into finalized processable representatives, instance/prototype/payload family mappings, optional extracted assets, and a sealed Workflow 1 handoff. Use for the decomposition phase of a large-scene run, for repeated or heavily instanced scenes, or when material and physics tasks need explicit scene partitions.
metadata:
  author: NVIDIA Omniverse
---

# con

### Simready (`content-workflow-simready`)
---
name: content-workflow-simready
description: Use after USD conversion, material and physics authoring, or Joint Agent publication to preflight SimReady Foundation, formally validate the current staged USD or USDZ, conditionally conform it from the failed validation report, revalidate the conformed output, run Gate 3B validation, and preserve durable non-blocking remediation evidence.
metadata:
  author: NVIDIA Omniverse
---

# content-workflo

### Texture (`content-workflow-texture`)
---
name: content-workflow-texture
description: Use one outer Codex or Claude reasoner to select and invoke focused, digest-bound Texture capabilities without a nested Texture workflow controller.
version: "0.5.1"
author: NVIDIA Omniverse
tags:
  - content-agents
  - texture
  - workflow
  - validation
tools:
  - Shell
  - Filesystem
  - Python
compatibility: Requires repository-root setup and Python >=3.12; agentic/ remains an internal implement

### Validation (`content-workflow-validation`)
---
name: content-workflow-validation
description: Validate USD assets through deterministic preparation, one decision-only Codex or Claude planning child, outer-validated exact adapters, independent assessment/review, and non-mutating terminal receipts. Use for agentic standalone Validation; use focused commands for explicit compatibility operations and the fixed-pipeline umbrella for config-driven Validation Agent runs.
version: "0.3.1"
author:

