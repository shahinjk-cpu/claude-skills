---
name: threejs-mastery-suite
description: >
  Interactive browser 3D graphics: scene hierarchies, cameras, materials, lighting, GLTF/GLB asset loading, post-processing shaders, and performance-optimized WebGL canvases.
category: design_frontend
version: "2.0.0"
role: consolidated_suite
triggers: threejs-mastery-suite, three.js 3d webgl visualization suite, threejs, threejs-3d, threejs-gltf-loading, threejs-materials-lighting, threejs-scene-setup
---

# 🌐 Three.js 3D WebGL Visualization Suite

Interactive browser 3D graphics: scene hierarchies, cameras, materials, lighting, GLTF/GLB asset loading, post-processing shaders, and performance-optimized WebGL canvases.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (4 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`threejs-3d`**: Build interactive 3D in the browser with Three.js/WebGL: scenes, materials, lighting, GLTF loading, animation, interaction, post-processing, shaders. Use for 3D sites, viewers or showing generated 3D models.
  - *Reference File:* `references/threejs-3d.md`
- **`threejs-gltf-loading`**: Load glTF/GLB models in three.js with GLTFLoader and play their skinned animations with AnimationMixer, including DRACO/Meshopt-compressed meshes and KTX2 textures. Use when importing 3D models into three.js — when the user mentions glTF, GLB, GLTFLoader, AnimationMixer, animation clips, DRACOLoader, or "load a 3D model". For scene/camera/renderer setup use threejs-scene-setup; for materials and lights use threejs-materials-lighting.
  - *Reference File:* `references/threejs-gltf-loading.md`
- **`threejs-materials-lighting`**: Light and shade a three.js scene: choose materials (MeshStandardMaterial PBR vs unlit MeshBasicMaterial), add ambient/hemisphere/directional/point/spot lights, turn on shadow maps, and use an environment map (IBL) for realistic reflections. Use when a three.js model looks black, flat, or wrong — when the user mentions three.js materials, MeshStandardMaterial, lights, shadows, envMap, or PBR. For renderer/loop setup use threejs-scene-setup; for loading models use threejs-gltf-loading.
  - *Reference File:* `references/threejs-materials-lighting.md`
- **`threejs-scene-setup`**: Stand up a three.js scene: import maps and the three/addons path, the Scene/PerspectiveCamera/WebGLRenderer trio, the setAnimationLoop render loop, responsive resize, OrbitControls, and opting into WebGPURenderer. Use when starting or debugging a three.js app — when the user mentions three.js, THREE.Scene, WebGLRenderer, WebGPURenderer, PerspectiveCamera, the render loop, resizing, or OrbitControls. For models use threejs-gltf-loading; for materials/lights use threejs-materials-lighting.
  - *Reference File:* `references/threejs-scene-setup.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `threejs-3d`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
