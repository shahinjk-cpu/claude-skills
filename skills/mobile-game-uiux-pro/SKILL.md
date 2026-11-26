---
name: mobile-game-uiux-pro
description: >-
  Designs world-class mobile game UI/UX, Game Feel (Juice), thumb ergonomics,
  ASMR tactile feedback, and responsive HUDs in Figma and Flutter/Flame/Unity.
  Use when designing game menus, HUDs, reward sequences, touch mechanics,
  spring/bounce physics, haptics, and anti-fatigue color palettes for mobile games.
---

# Mobile Game UI/UX & "Game Feel" (Juice) Architecture

Use this skill when architecting, designing, or reviewing mobile game user interfaces, player ergonomics, micro-interactions, reward psychology, and sensory tactile feedback.

---

## 1. Mobile Ergonomics & The "Thumb Zone" Rule

1. **One-Handed Portrait Reachability (The 60% Bottom Rule)**:
   - 82% of casual/puzzle mobile gamers play with one hand using their thumb.
   - **Primary Action Zone (Natural Comfort Zone):** Bottom 40% of the screen. Place the piece dock, primary gameplay board, and main interactive controls here.
   - **Neutral Zone (Stretch Zone):** Middle 30% of the screen. Place the secondary grid and passive meters here.
   - **Dead Zone (Hard to Reach):** Top 25% of the screen. Place read-only HUD elements here (Score, Level badge, Pause button). Never place time-sensitive or repetitive buttons in top corners.
2. **Touch-Point Occlusion (The Finger-Offset Rule)**:
   - When a player drags a game piece or card, their physical thumb blocks approximately 120x120 pixels of screen real estate.
   - **Mandatory UX Rule:** Always render dragged objects floating **35–45 pixels above the actual touch contact point**, with a subtle elevation drop shadow (`elevation: 12`, `blurRadius: 16`, `offset: (0, 8)`).
3. **Generous Tap Targets**:
   - Minimum interactive bounding box: `48x48 dp` (preferably `56x56 dp` for game buttons).
   - Add invisible padding around small icons (e.g., sound mute, info button) to eliminate mis-clicks.

---

## 2. "Game Feel" & "Juice" (Tactile Dopamine System)

A static game feels dead. "Juice" transforms simple grid placement into an irresistible tactile loop:

### 1. Spring Physics & Overshoot (Zero Linear Motion)
- Never use `Curves.linear`. Always use elastic springs:
  - **Tile Placement / Drop:** `Curves.elasticOut` or `Curves.bounceOut` with slight scale compression (Squash to `0.92x` height, Stretch to `1.08x` width, then settle).
  - **Button Presses:** Instant scale-down to `0.94x` on tap-down, spring back to `1.0x` on release.
  - **Combo Popups:** Overshoot scale to `1.25x` in 120ms, ease down to `1.0x` in 80ms, linger for 600ms, fade up with positive Y-offset.

### 2. Multi-Sensory Lockstep Synchronization
Every action must trigger a tri-fold sensory response simultaneously (< 16ms latency):
1. **Visual:** Particle flare, outline glow, micro-scale pop.
2. **Audio:** Pitch-shifted harmonic chord (C-D-E-G-A pentatonic scale prevents audio fatigue).
3. **Tactile (Haptics):**
   - Drag hover / Snap: `selectionClick()` (micro pulse).
   - Place block: `lightImpact()`.
   - Single line clear: `mediumImpact()`.
   - Combo x3+: `heavyImpact()` followed by `lightImpact()` 80ms later.

### 3. Screen Micro-Shake
- On multi-line clear (3+ lines) or Bomb booster detonation:
  - Shake amplitude: `3–5 pixels` maximum.
  - Duration: `120–160 milliseconds`.
  - Decay curve: `Curves.easeOutQuad`.
  - Note: Never shake the HUD, only the game board canvas to prevent motion sickness.

---

## 3. Visual Hierarchy & Anti-Fatigue Zen Aesthetics

1. **AMOLED Dark Backgrounds (Anti-Eye-Strain)**:
   - Dark mode should not be harsh pure black (`#000000`). Use deep indigo/slate (`#0C0D14`, `#121420`).
   - Deep backgrounds save 35–45% battery on OLED screens and make vibrant game blocks pop without blinding the player at night.
2. **Color Palette Harmony (Accessibility & Distinction)**:
   - Game blocks must maintain high contrast against the board grid (`>= 4.5:1` contrast ratio).
   - Use distinct shapes or subtle embossed inner borders so color-blind players can distinguish pieces by pattern/luminance, not hue alone.
3. **Ghost Preview Precision**:
   - When hovering a piece over valid slots, render the ghost cells at `35% opacity` with a soft pulsing border (`1.5 dp`, theme accent color).
   - If invalid, show no ghost or a subtle red desaturated flash (`#EF4444` at 15% opacity).

---

## 4. Cognitive Load & Frictionless Onboarding

1. **Zero Text Tutorials (Show, Don't Tell)**:
   - Never start a casual game with a multi-step modal dialog or wall of text.
   - On first launch:
     - Board starts with 7 blocks pre-filled in a row.
     - A 1x1 block waits in the dock.
     - An animated translucent hand points from the block to the empty slot.
     - The player drags it in -> Line clears -> **"NICE!"** celebration -> Game starts naturally in 3 seconds.
2. **HUD Zen Cleanliness**:
   - Display only 2 persistent metrics during gameplay: **Current Score** and **Best Score**.
   - Hide settings, coin counters, and daily quest progress inside sleek slide-in drawers or post-game summaries to keep the player in the "Flow" state.

---

## 5. Flutter Implementation Blueprint (120 FPS Rendering)

```dart
// Optimized Game Tile Container with Juicy Scale Feedback
class JuicyTileWidget extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;

  const JuicyTileWidget({super.key, required this.child, this.onTap});

  @override
  State<JuicyTileWidget> createState() => _JuicyTileWidgetState();
}

class _JuicyTileWidgetState extends State<JuicyTileWidget>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 140),
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.93).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerDown: (_) => _controller.forward(),
      onPointerUp: (_) {
        _controller.reverse();
        widget.onTap?.call();
      },
      onPointerCancel: (_) => _controller.reverse(),
      child: AnimatedBuilder(
        animation: _scaleAnimation,
        builder: (context, child) => Transform.scale(
          scale: _scaleAnimation.value,
          child: child,
        ),
        child: widget.child,
      ),
    );
  }
}
```

---

## 6. Review Checklist for Game Designers
- [ ] Is the primary interactive zone restricted to the bottom 60% of the screen?
- [ ] Does the dragged piece float 35–45px above the touch contact point?
- [ ] Does every placement have lockstep audio + haptic + visual feedback?
- [ ] Is linear animation banned across all UI transitions?
- [ ] Are backgrounds dark and eye-strain-free for nighttime play?
- [ ] Is onboarding frictionless with zero modal reading required?
- [ ] Does the game run at native 60/120 Hz without frame drops?
