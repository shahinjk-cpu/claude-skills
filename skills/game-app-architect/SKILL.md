---
name: game-app-architect
description: >-
  Architects and builds desktop and mobile games (2D/3D, Flutter Flame, Godot, Unity,
  Three.js, Phaser, HTML5 Canvas) and cross-platform desktop/mobile applications
  (Flutter, Electron, Tauri, React Native/Expo). Use when designing game loops,
  physics, state machines, UI overlays, offline-first app databases, or optimizing
  60/120 FPS performance.
---

# Desktop & Mobile Game and Application Architect

Use this skill when creating, structuring, or optimizing 2D/3D games and cross-platform desktop or mobile applications.

## 1. Game Development Architecture (2D & 3D)

### Core Game Loop & Separation of Concerns
1. **Strict Decoupling**:
   - Separate **Game State / Simulation Logic** (deterministic, tick-based using `deltaTime`) from **Rendering** and **Input Handling**.
   - Never tie movement speed or physics directly to frame count; always multiply by `dt` (delta time in seconds).
2. **State Machine Pattern**:
   - Manage both high-level game flow (`Boot -> MainMenu -> Playing -> Paused -> GameOver -> Victory`) and entity behavior (`Idle -> Patrol -> Chase -> Attack -> Cooldown`) using explicit Finite State Machines (FSM) or Behavior Trees.
3. **Entity-Component-System (ECS) / Composition**:
   - Prefer composition over deep inheritance hierarchies (`Player` has `HealthComponent`, `MovementComponent`, `InventoryComponent`, `SpriteComponent`).
4. **Performance & Memory (60/120 FPS Target)**:
   - **Object Pooling**: Pre-instantiate and recycle frequent objects (bullets, particles, floating damage numbers, enemies) instead of allocating/destroying inside `update()`.
   - **Spatial Partitioning**: Use grid buckets or quadtrees when checking collisions across many entities instead of $O(N^2)$ nested loops.
   - **Asset Preloading**: Load spritesheets, audio buffers, and shaders during a loading screen before starting the game loop.
5. **Game Feel ("Juice")**:
   - Include subtle camera shake on impacts, hit-pause/flash frames (40–60ms), particle bursts, easing curves on UI popups, and responsive audio feedback.

### Stack Selection Quick Guide
- **Mobile + Desktop Cross-Platform 2D**: Flutter + **Flame Engine** (pairs directly with existing Flutter/Dart tools) or **Godot 4**.
- **Web / Instant Playable 2D & 3D**: **Phaser 3 / PixiJS** (2D) or **Three.js / Babylon.js** (3D).
- **Heavy 3D / Native Desktop & Mobile**: **Unity (C#)** or **Godot 4 (GDScript/C#)**.

## 2. Desktop & Mobile Application Architecture

1. **Layered Clean Architecture**:
   - `presentation/` (Views, Widgets, ViewModels/Controllers) -> `domain/` (Entities, Use Cases, Repository Interfaces) -> `data/` (Local DB, Remote APIs, DTOs).
2. **Offline-First & Local Persistence**:
   - Desktop and mobile apps must remain responsive offline. Cache state locally (SQLite / Drift / Isar / Hive / IndexedDB) and sync optimistic updates with backend (Supabase / Firebase) when connectivity resumes.
3. **Platform Ergonomics**:
   - **Desktop (Windows/macOS/Linux)**: Support keyboard shortcuts, window resizing constraints, hover tooltips, context menus (right-click), and system tray / file drag-and-drop where relevant.
   - **Mobile (iOS/Android)**: Respect safe areas (`SafeArea`), thumb-friendly bottom navigation, minimum `48x48dp` tap targets, and haptic feedback.
