---
name: nvidia-3d-assets
description: Master orchestrator for NVIDIA's Omniverse 3D asset, SimReady, and OpenUSD content agent suite. Automates geometry repair, material assignment (MDL), PhysX properties, kinematics/articulation, and texture generation.
metadata:
  version: 1.0.0
---

# NVIDIA 3D Asset & USD Content Agents Suite

The **NVIDIA 3D Asset Suite** is an enterprise-grade agent automation toolkit developed by NVIDIA Omniverse for Pixar's OpenUSD (`.usd`, `.usdz`, `.usda`) 3D pipeline. It leverages Vision-Language Models (VLMs) and specialized physics/geometry engines to automate 3D asset generation, validation, and simulation readiness.

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\nvidia-usd-content-agents`

## The 34 Specialized NVIDIA 3D Skills

### 1. Asset Pipeline & Ingestion
- `content-workflow-asset`: End-to-end 3D asset lifecycle management in OpenUSD.
- `content-workflow-convert-to-usd`: Lossless conversion of OBJ, FBX, GLTF, STL to USD.
- `geometry-source-intake`: Ingestion and sanity checks for CAD and external polygon meshes.
- `usd-cli`: Official USD command-line utilities (usdview, usdedit, usdcat, usdzip).

### 2. Geometry & Mesh Processing
- `content-workflow-geometry`: Polygon density analysis, topology audit, bounding volumes.
- `content-workflow-geometry-repair`: Automatic non-manifold edge fixing, hole filling, normal healing.
- `content-workflow-mesh-segmentation`: Semantic sub-mesh partitioning for articulation and physics.
- `geometry-evidence-review`: Visual evidence checks for geometric artifacts and mesh quality.

### 3. Materials & Texturing
- `content-workflow-material`: NVIDIA MDL (Material Definition Language) assignment and PBR shader setup.
- `content-workflow-texture`: Texture generation, UV unwrapping, baking, and resolution scaling.
- `content-texture-candidate`: VLM-evaluated texture generation matching target references.
- `content-texture-quality`: Seam audits, mipmap validation, and compression checks.
- `content-texture-scope`: Memory footprint budgeting for textures across target runtimes.
- `content-texture-publish`: Finalizing and archiving verified texture sets into asset registries.

### 4. Physics & Simulation (SimReady)
- `content-workflow-physics`: Rigid body dynamics, collision hull authoring (convex, mesh, primitives).
- `content-workflow-simready`: Compliance testing for NVIDIA Isaac Sim robotics simulation.
- `content-workflow-physics-external-tuning`: PhysX parameter tuning (friction, restitution, mass, damping).
- `content-sdf-operations`: Volumetric Signed Distance Field generation for hyper-accurate collision.

### 5. Kinematics & Articulation
- `content-workflow-articulation`: Rigging mechanical joints (revolute, prismatic, spherical).
- `content-articulation-authoring`: Setting joint limits, axes of freedom, and drive motors.
- `content-articulation-inspection`: Validating kinematics trees and collision-free ranges.
- `content-articulation-proposal`: Automated joint proposal from segmented mesh relationships.
- `content-articulation-review`: Operational kinematics sign-off for digital twins.

### 6. Scene Assembly & Quality Gates
- `content-workflow-scene-collection`: Assembling large-scale digital twins and factory stages.
- `content-workflow-scene-decomposition`: Breaking down complex compound stages into reusable USD layers.
- `content-workflow-large-scene`: Level of detail (LOD) hierarchies and memory streaming.
- `content-workflow-validation`: Strict schema verification against OpenUSD asset specifications.
- `fixed-pipeline`: Deterministic batch pipelines for enterprise asset ingestion.
- `product-image-decomposer`: Reconstructing 3D object geometry from multiview product photography.

## Workflow Example: Preparing a SimReady Robot Component
```bash
# 1. Convert CAD/FBX to OpenUSD
agent run content-workflow-convert-to-usd --input part.fbx --output part.usd
# 2. Repair mesh topology
agent run content-workflow-geometry-repair --asset part.usd
# 3. Add PhysX and validate SimReady compliance
agent run content-workflow-physics --asset part.usd --type rigid_body
agent run content-workflow-simready --asset part.usd
```
