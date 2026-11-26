---
name: godot-engine-suite
description: >
  Complete Godot 4.x engine suite covering 2D movement, 3D essentials, character animation, physics, shaders/VFX, signals/groups, tilemaps, GDScript, C#, multiplayer, UI controls, export pipelines, and headless testing.
category: game_3d
version: "2.0.0"
role: consolidated_suite
triggers: godot-engine-suite, godot game engine full-stack suite, godot, godot-2d-movement, godot-3d-essentials, godot-animation, godot-audio, godot-csharp, godot-export, godot-gdscript-headless-testing, godot-gdscript, godot-multiplayer, godot-nodes-scenes, godot-physics, godot-resources, godot-shaders, godot-signals-groups, godot-tilemap, godot-ui-control
---

# 🎮 Godot Game Engine Full-Stack Suite

Complete Godot 4.x engine suite covering 2D movement, 3D essentials, character animation, physics, shaders/VFX, signals/groups, tilemaps, GDScript, C#, multiplayer, UI controls, export pipelines, and headless testing.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (16 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`godot-2d-movement`**: Implement 2D kinematic character movement in Godot 4.7 with CharacterBody2D and move_and_slide(): platformer run/jump with gravity, top-down 8-direction motion, slope handling, and reading collisions. Use when coding a 2D player or enemy controller, a platformer or top-down character, or fixing move_and_slide()/ is_on_floor() behavior in a .tscn with a CharacterBody2D.
  - *Reference File:* `references/godot-2d-movement.md`
- **`godot-3d-essentials`**: Set up a Godot 4.7 3D scene: Node3D transforms, Camera3D, lighting (DirectionalLight3D/OmniLight3D), WorldEnvironment for sky/ambient/tonemap/post, MeshInstance3D materials, and GridMap for tile-based 3D levels. Use when building a 3D scene in a Godot project, placing cameras/lights, configuring environment and post-processing, or working with Node3D/.tscn 3D content and GridMap.
  - *Reference File:* `references/godot-3d-essentials.md`
- **`godot-animation`**: Animate in Godot 4.7 three ways: AnimationPlayer for keyframed clips (incl. Call Method tracks), AnimationTree with state machines and blend spaces for character animation, and Tween for short procedural/UI tweens via create_tween(). Use when working with AnimationPlayer/AnimationTree nodes in a .tscn, blending character states, sprite-sheet animation, or code-driven Tweens.
  - *Reference File:* `references/godot-animation.md`
- **`godot-audio`**: Play and mix audio in Godot 4.7: AudioStreamPlayer (2D/3D variants), audio buses with volume/mute and effects, music vs SFX routing, db/linear volume, and precise sync-to-beat playback timing. Use when playing sounds or music in a Godot project, routing AudioStreamPlayer nodes to buses, adjusting bus volume via AudioServer, or syncing gameplay to the beat.
  - *Reference File:* `references/godot-audio.md`
- **`godot-csharp`**: Use C#/.NET in Godot 4.7: partial classes extending nodes, the PascalCase lifecycle (_Ready/_Process/_PhysicsProcess), [Export] fields, [Signal] delegates as C# events, type-safe node lookup, and calling between C# and GDScript. Use when writing Godot game code in C# (.cs files, .csproj), needing the Godot .NET build, converting GDScript patterns to C#, or wiring Godot signals as C# events.
  - *Reference File:* `references/godot-csharp.md`
- **`godot-export`**: Godot-specific Blender export favoring GLTF/GLB with correct scale, materials, animation clips, and collision shapes via MCP.
  - *Reference File:* `references/godot-export.md`
- **`godot-gdscript`**: Write idiomatic GDScript for Godot 4.7: static typing, the node lifecycle (_ready/_process/_physics_process), @export/@onready/@tool annotations, signals, and await for asynchronous flow. Use when editing .gd scripts in a Godot project (project.godot), writing or debugging GDScript, or porting 3.x GDScript to 4.x (function signatures, yield to await, export to @export).
  - *Reference File:* `references/godot-gdscript.md`
- **`godot-gdscript-headless-testing`**: Run GDScript test suites from the command line with `godot --headless`, using a SceneTree/MainLoop runner script that exits non-zero on failure so CI can gate merges. Use when a Godot project needs unit tests without opening the editor, when wiring a CI job (GitHub Actions or similar) that must fail the build on a failing `.gd` test, or when a `godot --headless` invocation hangs, opens a window, or exits 0 despite failed assertions.
  - *Reference File:* `references/godot-gdscript-headless-testing.md`
- **`godot-multiplayer`**: Build networked games with Godot 4.7 high-level multiplayer: set up an ENetMultiplayerPeer server/client, define RPCs with the @rpc annotation (call via rpc()/rpc_id()), set per-node multiplayer authority, and replicate state with MultiplayerSpawner and MultiplayerSynchronizer. Use when adding multiplayer/networking to a Godot project, writing @rpc functions, or syncing player/world state across peers.
  - *Reference File:* `references/godot-multiplayer.md`
- **`godot-nodes-scenes`**: Structure a Godot 4.7 project with the scene tree and node composition: build reusable scenes, instance PackedScenes at runtime, navigate the tree safely, and register autoload singletons. Use when designing .tscn scenes, deciding how to split nodes, spawning instances with instantiate(), wiring autoloads, or fixing "node not found"/freed-node errors in a Godot project.
  - *Reference File:* `references/godot-nodes-scenes.md`
- **`godot-physics`**: Use Godot 4.7 physics bodies and detection in 2D and 3D: RigidBody, StaticBody, Area, and CharacterBody; collision layers vs masks; contact/overlap signals; and raycasts (RayCast nodes and direct space-state queries). Use when configuring collision layers/masks, detecting overlaps with Area2D/Area3D, applying forces to a RigidBody, or casting rays in a Godot project (.tscn with physics bodies), including 3D projects running Jolt Physics, the default 3D engine for projects created in 4.6+.
  - *Reference File:* `references/godot-physics.md`
- **`godot-resources`**: Design data-driven Godot 4.7 games with custom Resource classes: define typed data with class_name + @export, save/load .tres/.res files, instance and duplicate resources, and load on demand with ResourceLoader (incl. threaded loading). Use when modeling items/stats/configs as data in a Godot project, creating .tres resources, or working with custom Resource subclasses and ResourceLoader/ResourceSaver.
  - *Reference File:* `references/godot-resources.md`
- **`godot-shaders`**: Write Godot 4.7 shaders in the Godot Shading Language: canvas_item shaders for 2D and spatial shaders for 3D, with vertex/fragment functions, uniforms (source_color, hint_range), TIME/UV animation, and screen-reading via hint_screen_texture. Use when authoring .gdshader files, writing fragment/vertex code, making 2D/3D visual effects, or porting 3.x shaders (SCREEN_TEXTURE, hint_color) to 4.x.
  - *Reference File:* `references/godot-shaders.md`
- **`godot-signals-groups`**: Build event-driven, decoupled Godot 4.7 gameplay with signals and node groups: declare and emit custom signals, connect with Callables (incl. bind/one-shot), and broadcast to many nodes via groups and call_group. Use when wiring node communication in a Godot project, replacing tight references with signals, emitting/connecting events, or porting 3.x connect("sig", self, "method") code.
  - *Reference File:* `references/godot-signals-groups.md`
- **`godot-tilemap`**: Build and edit tile-based 2D levels in Godot 4.7 with TileMapLayer and TileSet: paint layers, set up collision/navigation/custom-data on tiles, autotile with terrain sets, and read/write cells from code (set_cell, get_cell_tile_data, local_to_map). Use when working with TileMapLayer nodes, .tres TileSets, autotiling, or migrating a deprecated TileMap node to TileMapLayer.
  - *Reference File:* `references/godot-tilemap.md`
- **`godot-ui-control`**: Build Godot 4.7 user interfaces with Control nodes: anchors and offsets for responsive layout, Container nodes (VBox/HBox/Grid/Margin) for automatic arrangement, Theme resources for consistent styling, and keyboard/gamepad focus navigation. Use when laying out a HUD, menu, or UI in a Godot project, working with Control/Container nodes, anchors, themes, or focus in a .tscn.
  - *Reference File:* `references/godot-ui-control.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `godot-2d-movement`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
