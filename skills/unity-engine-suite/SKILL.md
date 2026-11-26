---
name: unity-engine-suite
description: >
  Complete Unity engine suite: C# gameplay scripting, animation state machines, input system, 2D tilemaps, 3D physics, ScriptableObject architectures, build pipelines, and asset export.
category: game_3d
version: "2.0.0"
role: consolidated_suite
triggers: unity-engine-suite, unity game development & pipeline suite, unity, unity-animation, unity-build-pipeline, unity-csharp-scripting, unity-export, unity-input-system, unity-navmesh, unity-physics, unity-scriptableobjects, unity-tilemap-2d
---

# 🎲 Unity Game Development & Pipeline Suite

Complete Unity engine suite: C# gameplay scripting, animation state machines, input system, 2D tilemaps, 3D physics, ScriptableObject architectures, build pipelines, and asset export.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (9 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`unity-animation`**: Drive Unity 6.3 LTS character animation with Animator Controllers: states, transitions, parameters, blend trees, animation layers, and humanoid Avatar IK. Use when wiring an Animator, setting parameters from script (SetFloat/SetBool/SetTrigger), building blend trees, or when the user mentions Animator, Mecanim, state machine, blend tree, or .controller.
  - *Reference File:* `references/unity-animation.md`
- **`unity-build-pipeline`**: Build and ship Unity 6.3 LTS players: build settings and scenes, player/quality settings, the IL2CPP vs Mono scripting backend, managed code stripping, scripted BuildPipeline.BuildPlayer, and CI/headless builds. Use when configuring or automating a build, choosing a scripting backend, shrinking build size, or when the user mentions Unity build, player settings, IL2CPP, code stripping, or Addressables.
  - *Reference File:* `references/unity-build-pipeline.md`
- **`unity-csharp-scripting`**: Write Unity 6.3 LTS C# gameplay scripts: the MonoBehaviour lifecycle (Awake/OnEnable/Start/Update/FixedUpdate/LateUpdate), GameObject and component access, coroutines, and Inspector serialization. Use when creating or editing .cs scripts in a Unity project, or when the user mentions MonoBehaviour, Start/Update, GetComponent, SerializeField, coroutines, or "Unity script".
  - *Reference File:* `references/unity-csharp-scripting.md`
- **`unity-export`**: Unity-specific Blender export for scale, axis, materials, humanoid/generic rigs, LODs, and collision import via MCP.
  - *Reference File:* `references/unity-export.md`
- **`unity-input-system`**: Wire player input in Unity 6.3 LTS with the Input System package: Input Actions, action maps, the PlayerInput component, and reading values via callbacks or polling. Use when the project has a .inputactions asset or com.unity.inputsystem, or when the user mentions the Unity Input System, InputAction, action maps, PlayerInput, control schemes, or rebinding.
  - *Reference File:* `references/unity-input-system.md`
- **`unity-navmesh`**: Add AI navigation in Unity 6.3 LTS: bake a NavMesh with the AI Navigation package (NavMeshSurface), move agents with NavMeshAgent.SetDestination, and handle dynamic obstacles. Use when setting up pathfinding, making an enemy chase the player, baking navigation, or when the user mentions NavMesh, NavMeshAgent, NavMeshSurface, NavMeshObstacle, or Unity pathfinding.
  - *Reference File:* `references/unity-navmesh.md`
- **`unity-physics`**: Set up 3D physics in Unity 6.3 LTS: Rigidbody movement and forces, colliders, triggers vs collisions, layer-based collision, raycasts, and joints. Use when adding a Rigidbody, handling OnCollisionEnter/OnTriggerEnter, tuning collision layers, casting rays, or when the user mentions Unity physics, AddForce, isKinematic, or linearVelocity.
  - *Reference File:* `references/unity-physics.md`
- **`unity-scriptableobjects`**: Architect Unity 6.3 LTS data and decoupling with ScriptableObjects: config/data assets, shared runtime variables, event channels, and runtime sets/registries. Use when designing data-driven systems, replacing singletons/managers, creating .asset data with CreateAssetMenu, or when the user mentions ScriptableObject, SO architecture, or data assets.
  - *Reference File:* `references/unity-scriptableobjects.md`
- **`unity-tilemap-2d`**: Build and script 2D tilemaps in Unity 6.3 LTS: the Grid + Tilemap components, the Tile Palette, tilemap colliders, rule tiles, and runtime SetTile/GetTile painting. Use when painting tile levels, adding a TilemapCollider2D, using rule or animated tiles, generating tilemaps from code, or when the user mentions Unity tilemap, tile palette, rule tile, or Grid.
  - *Reference File:* `references/unity-tilemap-2d.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `unity-animation`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
