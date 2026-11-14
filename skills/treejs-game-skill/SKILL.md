---
name: treejs-game-skill
description: >
  Complete 3D Three.js game development architecture: game loop, third-person/FPS camera, physics collisions, GLTF asset loading, particle systems, and audio spatialization.
metadata:
  version: "1.0.0"
  category: game_3d
  triggers: treejs game, threejs game, 3d browser game, webgl game engine, three.js game loop
---

# Three.js Game Architecture — 3D Browser Game Engine

Complete blueprint and production patterns for building high-performance 3D browser games using Three.js, Cannon-es/Rapier physics, and WebGL.

## Core Subsystems
- **Fixed-Step Game Loop**: Decouple physics ticks (`60Hz`) from variable render refresh rates (`requestAnimationFrame`).
- **Entity Component Architecture**: Separate player movement, visual mesh, collision hulls, and AI controllers.
- **Asset Pipeline**: Compressed GLTF/GLB models using Draco and KTX2 texture compression.
- **Spatial Audio**: Web Audio API PositionalAudio nodes attached to scene meshes.
