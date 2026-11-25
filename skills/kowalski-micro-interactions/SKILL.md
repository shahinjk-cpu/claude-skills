---
name: kowalski-micro-interactions
description: >-
  Emil Kowalski interaction design mastery: physics-based spring transitions, magnetic buttons, fluid toggle animations, and micro-delight mechanics.
---

# Emil Kowalski Micro-Interactions & Fluid UI

A guide to implementing interaction design based on Emil Kowalski's principles of digital craftsmanship.

## 1. Spring Physics Over Duration Easing
Avoid mechanical `cubic-bezier` curves; use natural springs:
```typescript
// Framer Motion spring config
const spring = {
  type: "spring",
  stiffness: 500,
  damping: 30,
  mass: 1
};
```

## 2. Shared Layout Animations
Use `layoutId` for smooth morphing between tabs, selectors, and active pills without jumping.

## 3. The 100ms Rule
Visual acknowledgement of an action must occur within 100ms of click/tap, even if backend latency is higher.
