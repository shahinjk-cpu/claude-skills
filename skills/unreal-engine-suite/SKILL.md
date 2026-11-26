---
name: unreal-engine-suite
description: >
  Unreal Engine 5 architecture suite: C++ gameplay programming, Blueprints visual scripting, Behavior Trees AI, Enhanced Input, Niagara VFX, asset packaging, and FBX/LOD pipeline.
category: game_3d
version: "2.0.0"
role: consolidated_suite
triggers: unreal-engine-suite, unreal engine 5 core & gameplay suite, unreal, unreal-behavior-trees, unreal-blueprints, unreal-cpp-gameplay, unreal-enhanced-input, unreal-export, unreal-niagara, unreal-packaging
---

# ⚡ Unreal Engine 5 Core & Gameplay Suite

Unreal Engine 5 architecture suite: C++ gameplay programming, Blueprints visual scripting, Behavior Trees AI, Enhanced Input, Niagara VFX, asset packaging, and FBX/LOD pipeline.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (7 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`unreal-behavior-trees`**: Build NPC AI in Unreal Engine 5 with Behavior Trees and Blackboards: composites (Selector/Sequence), tasks, decorators, services, and running the tree from an AIController. Use when creating enemy/NPC AI, BT_/BB_ assets, custom BTTask or BTService nodes, or when the user mentions Behavior Tree, Blackboard, AIController, BTTask, decorator, or service.
  - *Reference File:* `references/unreal-behavior-trees.md`
- **`unreal-blueprints`**: Build Unreal Engine 5 gameplay with Blueprint visual scripting: Blueprint Classes, the Event Graph and Construction Script, variables/functions/macros, and Blueprint communication (Cast, Interfaces, Event Dispatchers). Use when working in Blueprints, wiring an event graph, deciding how Blueprints talk to each other, or when the user mentions Blueprint, BP, event graph, construction script, or a Blueprint .uasset.
  - *Reference File:* `references/unreal-blueprints.md`
- **`unreal-cpp-gameplay`**: Write Unreal Engine 5 C++ gameplay code: the UCLASS/UPROPERTY/UFUNCTION reflection macros, the Gameplay Framework (GameMode, Pawn, Character, PlayerController, Actor components), and the module Build.cs. Use when writing or debugging UE C++, deriving from AActor/ACharacter/ AGameModeBase, exposing properties to the editor or Blueprints, or when the user mentions Unreal C++, UCLASS, GENERATED_BODY, GameMode, ACharacter, or .Build.cs.
  - *Reference File:* `references/unreal-cpp-gameplay.md`
- **`unreal-enhanced-input`**: Set up player input in Unreal Engine 5 with Enhanced Input: Input Actions, Input Mapping Contexts, modifiers and triggers, adding the mapping context, and binding actions by ETriggerEvent. Use when wiring movement/look/jump input, creating IA_/IMC_ assets, binding in C++ or Blueprints, or when the user mentions Enhanced Input, Input Mapping Context, Input Action, IA_/IMC_, or ETriggerEvent.
  - *Reference File:* `references/unreal-enhanced-input.md`
- **`unreal-export`**: Unreal Engine-specific Blender export for FBX scale, LODs, UCX collision, sockets, materials, and skeletal mesh workflows via MCP.
  - *Reference File:* `references/unreal-export.md`
- **`unreal-niagara`**: Create and control VFX in Unreal Engine 5 with Niagara: systems and emitters, modules and the spawn/update stages, exposed User parameters, and spawning or driving effects from Blueprints or C++. Use when building particle effects, NS_/NE_ assets, spawning a Niagara system at runtime, setting User parameters, or when the user mentions Niagara, VFX, or a particle system in Unreal.
  - *Reference File:* `references/unreal-niagara.md`
- **`unreal-packaging`**: Package and ship an Unreal Engine 5 project: the Platforms menu Package Project flow, build configurations (Development vs Shipping), cooking content, packaging settings and the Game Default Map, and command-line builds with RunUAT BuildCookRun. Use when packaging a build, making a shipping build, cooking content, configuring packaging settings, or when the user mentions package Unreal, cook content, shipping build, or BuildCookRun.
  - *Reference File:* `references/unreal-packaging.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `unreal-behavior-trees`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
