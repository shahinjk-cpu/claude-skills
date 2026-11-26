---
name: godot-expert
description: Complete Godot Engine master development suite covering GDScript, 2D/3D physics, shaders, particle systems, multiplayer networking, and testing.
---

# Godot Engine Master Development Suite


## Godot Engine Development Modules

### Module: godot-2d-movement
---
name: godot-2d-movement
description: >
  Implement 2D kinematic character movement in Godot 4.7 with CharacterBody2D and
  move_and_slide(): platformer run/jump with gravity, top-down 8-direction motion,
  slope handling, and reading collisions. Use when coding a 2D player or enemy
  controller, a platformer or top-down character, or fixing move_and_slide()/
  is_on_floor() behavior in a .tscn with a CharacterBody2D.
---

# Godot 2D Movement (4.x)

Build responsive 2D character controllers w

### Module: godot-3d-essentials
---
name: godot-3d-essentials
description: >
  Set up a Godot 4.7 3D scene: Node3D transforms, Camera3D, lighting
  (DirectionalLight3D/OmniLight3D), WorldEnvironment for sky/ambient/tonemap/post,
  MeshInstance3D materials, and GridMap for tile-based 3D levels. Use when building
  a 3D scene in a Godot project, placing cameras/lights, configuring environment and
  post-processing, or working with Node3D/.tscn 3D content and GridMap.
---

# Godot 3D Essentials (4.x)

Assemble a working 3D scene:

### Module: godot-animation
---
name: godot-animation
description: >
  Animate in Godot 4.7 three ways: AnimationPlayer for keyframed clips (incl. Call
  Method tracks), AnimationTree with state machines and blend spaces for
  character animation, and Tween for short procedural/UI tweens via create_tween().
  Use when working with AnimationPlayer/AnimationTree nodes in a .tscn, blending
  character states, sprite-sheet animation, or code-driven Tweens.
---

# Godot Animation (4.x)

Choose and drive the right animation tool

### Module: godot-audio
---
name: godot-audio
description: >
  Play and mix audio in Godot 4.7: AudioStreamPlayer (2D/3D variants), audio buses
  with volume/mute and effects, music vs SFX routing, db/linear volume, and precise
  sync-to-beat playback timing. Use when playing sounds or music in a Godot project,
  routing AudioStreamPlayer nodes to buses, adjusting bus volume via AudioServer, or
  syncing gameplay to the beat.
---

# Godot Audio (4.x)

Play SFX and music, route them through buses, control volume in deci

### Module: godot-csharp
---
name: godot-csharp
description: >
  Use C#/.NET in Godot 4.7: partial classes extending nodes, the PascalCase lifecycle
  (_Ready/_Process/_PhysicsProcess), [Export] fields, [Signal] delegates as C# events,
  type-safe node lookup, and calling between C# and GDScript. Use when writing Godot game code in
  C# (.cs files, .csproj), needing the Godot .NET build, converting GDScript patterns
  to C#, or wiring Godot signals as C# events.
---

# Godot C# / .NET (4.x)

Write Godot game code in C#:

### Module: godot-export
---
name: godot-export
description: Godot-specific Blender export favoring GLTF/GLB with correct scale, materials, animation clips, and collision shapes via MCP.
license: MIT
metadata:
  author: https://github.com/arjun988
  version: "1.0.0"
  domain: blender
  role: specialist
  triggers: Godot, Godot export, Godot GLTF, Godot GLB, Godot materials, Godot animation
  related-skills: export-pipeline, lod-pipeline, collision-proxy, asset-optimization, materials
---

# Godot Export

GLTF/GLB first.

### Module: godot-gdscript
---
name: godot-gdscript
description: >
  Write idiomatic GDScript for Godot 4.7: static typing, the node lifecycle
  (_ready/_process/_physics_process), @export/@onready/@tool annotations,
  signals, and await for asynchronous flow. Use when editing .gd scripts in a
  Godot project (project.godot), writing or debugging GDScript, or porting 3.x
  GDScript to 4.x (function signatures, yield to await, export to @export).
---

# Godot GDScript (4.x)

Write correct, statically typed GDScript and use

### Module: godot-gdscript-headless-testing
---
name: godot-gdscript-headless-testing
description: >
  Run GDScript test suites from the command line with `godot --headless`, using a
  SceneTree/MainLoop runner script that exits non-zero on failure so CI can gate
  merges. Use when a Godot project needs unit tests without opening the editor,
  when wiring a CI job (GitHub Actions or similar) that must fail the build on a
  failing `.gd` test, or when a `godot --headless` invocation hangs, opens a
  window, or exits 0 despite failed assert

### Module: godot-gdscript-patterns
---
name: godot-gdscript-patterns
description: Master Godot 4 GDScript patterns including signals, scenes, state machines, and optimization. Use when building Godot games, implementing game systems, or learning GDScript best practices.
---

# Godot GDScript Patterns

Production patterns for Godot 4.x game development with GDScript, covering architecture, signals, scenes, and optimization.

## When to Use This Skill

- Building games with Godot 4
- Implementing game systems in GDScript
- Designin

### Module: godot-multiplayer
---
name: godot-multiplayer
description: >
  Build networked games with Godot 4.7 high-level multiplayer: set up an
  ENetMultiplayerPeer server/client, define RPCs with the @rpc annotation
  (call via rpc()/rpc_id()), set per-node multiplayer authority, and replicate
  state with MultiplayerSpawner and MultiplayerSynchronizer. Use when adding
  multiplayer/networking to a Godot project, writing @rpc functions, or syncing
  player/world state across peers.
---

# Godot Multiplayer (4.x high-leve

### Module: godot-nodes-scenes
---
name: godot-nodes-scenes
description: >
  Structure a Godot 4.7 project with the scene tree and node composition: build
  reusable scenes, instance PackedScenes at runtime, navigate the tree safely,
  and register autoload singletons. Use when designing .tscn scenes, deciding how
  to split nodes, spawning instances with instantiate(), wiring autoloads, or
  fixing "node not found"/freed-node errors in a Godot project.
---

# Godot Nodes & Scenes (4.x)

Compose games from nodes and scenes, i

### Module: godot-patterns
---
name: godot-patterns
description: Idiomatic Godot 4 GDScript patterns - static typing, scene and node design, signals, resources, autoloads, input, and lifecycle safety. Use when writing or reviewing GDScript, designing scenes, or deciding where game state should live.
origin: ECC
---

# Godot 4 GDScript Patterns

Idiomatic patterns for Godot 4.x projects written in GDScript. Verified against the Godot 4.7 documentation; most guidance applies to every 4.x release.

## When to Activate

- Wri

### Module: godot-physics
---
name: godot-physics
description: >
  Use Godot 4.7 physics bodies and detection in 2D and 3D: RigidBody, StaticBody,
  Area, and CharacterBody; collision layers vs masks; contact/overlap signals; and
  raycasts (RayCast nodes and direct space-state queries). Use when configuring
  collision layers/masks, detecting overlaps with Area2D/Area3D, applying forces to a
  RigidBody, or casting rays in a Godot project (.tscn with physics bodies), including
  3D projects running Jolt Physics, the def

### Module: godot-resources
---
name: godot-resources
description: >
  Design data-driven Godot 4.7 games with custom Resource classes: define typed
  data with class_name + @export, save/load .tres/.res files, instance and duplicate
  resources, and load on demand with ResourceLoader (incl. threaded loading). Use
  when modeling items/stats/configs as data in a Godot project, creating .tres
  resources, or working with custom Resource subclasses and ResourceLoader/ResourceSaver.
---

# Godot Resources (4.x)

Model game da

### Module: godot-shaders
---
name: godot-shaders
description: >
  Write Godot 4.7 shaders in the Godot Shading Language: canvas_item shaders for 2D
  and spatial shaders for 3D, with vertex/fragment functions, uniforms (source_color,
  hint_range), TIME/UV animation, and screen-reading via hint_screen_texture. Use
  when authoring .gdshader files, writing fragment/vertex code, making 2D/3D visual
  effects, or porting 3.x shaders (SCREEN_TEXTURE, hint_color) to 4.x.
---

# Godot Shaders (4.x)

Write `canvas_item` (2D) a

### Module: godot-signals-groups
---
name: godot-signals-groups
description: >
  Build event-driven, decoupled Godot 4.7 gameplay with signals and node groups:
  declare and emit custom signals, connect with Callables (incl. bind/one-shot),
  and broadcast to many nodes via groups and call_group. Use when wiring node
  communication in a Godot project, replacing tight references with signals,
  emitting/connecting events, or porting 3.x connect("sig", self, "method") code.
---

# Godot Signals & Groups (4.x)

Decouple nodes wit

### Module: godot-testing
---
name: godot-testing
description: Testing Godot 4 GDScript projects - a zero-dependency headless check scene, gdUnit4 and GUT suites, scene-runner tests, signal assertions, and CI commands. Use when adding tests to a Godot project, setting up CI, or proving a change did not break the game.
origin: ECC
---

# Godot 4 Testing

A layered way to test GDScript games so most checks run headlessly in seconds, with no window and no human.

## When to Activate

- Adding the first tests to a Godot proj

### Module: godot-tilemap
---
name: godot-tilemap
description: >
  Build and edit tile-based 2D levels in Godot 4.7 with TileMapLayer and TileSet:
  paint layers, set up collision/navigation/custom-data on tiles, autotile with
  terrain sets, and read/write cells from code (set_cell, get_cell_tile_data,
  local_to_map). Use when working with TileMapLayer nodes, .tres TileSets, autotiling,
  or migrating a deprecated TileMap node to TileMapLayer.
---

# Godot TileMap (4.7 TileMapLayer)

Author tile-based levels with `Tile

### Module: godot-ui-control
---
name: godot-ui-control
description: >
  Build Godot 4.7 user interfaces with Control nodes: anchors and offsets for
  responsive layout, Container nodes (VBox/HBox/Grid/Margin) for automatic
  arrangement, Theme resources for consistent styling, and keyboard/gamepad focus
  navigation. Use when laying out a HUD, menu, or UI in a Godot project, working
  with Control/Container nodes, anchors, themes, or focus in a .tscn.
---

# Godot UI / Control nodes (4.x)

Lay out responsive UI with `Contr

