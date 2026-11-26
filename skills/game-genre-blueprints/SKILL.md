---
name: game-genre-blueprints
description: >
  Exhaustive game genre design systems: action combat, visual novels, open-world sandbox, racing/sports, RPG/JRPG, FPS/shooter, soulslike, stealth, roguelike/metroidvania, strategy/sim, puzzle platformers, and survival crafting.
category: game_3d
version: "2.0.0"
role: consolidated_suite
triggers: game-genre-blueprints, game genre architecture & mechanics blueprints, genre, genre-action-combat, genre-card-party-idle, genre-metroidvania-roguelike, genre-narrative-vn, genre-open-world-sandbox, genre-puzzle-platformer, genre-racing-sports, genre-rpg, genre-shooter, genre-soulslike, genre-stealth, genre-strategy-sim, genre-survival
---

# 🕹️ Game Genre Architecture & Mechanics Blueprints

Exhaustive game genre design systems: action combat, visual novels, open-world sandbox, racing/sports, RPG/JRPG, FPS/shooter, soulslike, stealth, roguelike/metroidvania, strategy/sim, puzzle platformers, and survival crafting.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (13 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`genre-action-combat`**: Art direction for action, hack-and-slash, beat 'em up, and fighting-game readable combat spaces and prop language in Blender.
  - *Reference File:* `references/genre-action-combat.md`
- **`genre-card-party-idle`**: Art direction for card games, deck builders, party games, idle/incremental, educational, and rhythm game presentational spaces in Blender.
  - *Reference File:* `references/genre-card-party-idle.md`
- **`genre-metroidvania-roguelike`**: Art direction for metroidvania, roguelike, and roguelite games in Blender with biome gates, room modules, and run-readable props.
  - *Reference File:* `references/genre-metroidvania-roguelike.md`
- **`genre-narrative-vn`**: Art direction for visual novel, interactive movie, walking simulator, and story-driven presentation spaces in Blender.
  - *Reference File:* `references/genre-narrative-vn.md`
- **`genre-open-world-sandbox`**: Art direction for open world and sandbox games in Blender with biome landmarks, traversable scale, and discovery props.
  - *Reference File:* `references/genre-open-world-sandbox.md`
- **`genre-puzzle-platformer`**: Art direction for puzzle and platformer games in Blender with readable interactables, jump volumes, and clear hazard language.
  - *Reference File:* `references/genre-puzzle-platformer.md`
- **`genre-racing-sports`**: Art direction for racing and sports games in Blender with track landmarks, stadium kits, and high-speed readability.
  - *Reference File:* `references/genre-racing-sports.md`
- **`genre-rpg`**: Art direction for RPG, JRPG, CRPG, ARPG, and MMORPG worlds in Blender including loot rarity reads and region identity.
  - *Reference File:* `references/genre-rpg.md`
- **`genre-shooter`**: Art direction for FPS, TPS, shooter, battle royale, and extraction-shooter maps and props in Blender with sightline and cover language.
  - *Reference File:* `references/genre-shooter.md`
- **`genre-soulslike`**: Art direction for soulslike games in Blender with monumental melancholy spaces, fog gates, bonfire landmarks, and lethal readability.
  - *Reference File:* `references/genre-soulslike.md`
- **`genre-stealth`**: Art direction for stealth-game spaces in Blender with shadow volumes, patrol-friendly layouts, and concealment materials.
  - *Reference File:* `references/genre-stealth.md`
- **`genre-strategy-sim`**: Art direction for strategy, RTS, turn-based strategy, tower defense, MOBA, city builder, colony sim, and simulation games in Blender.
  - *Reference File:* `references/genre-strategy-sim.md`
- **`genre-survival`**: Art direction for survival and survival-horror gameplay spaces in Blender emphasizing resource props, crafting readability, and tension routes.
  - *Reference File:* `references/genre-survival.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `genre-action-combat`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
