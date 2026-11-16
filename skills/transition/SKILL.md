---
name: transition
description: High-performance CSS transitions, View Transitions API, UI state changes, micro-interactions, and motion choreography for modern web and mobile apps.
metadata:
  version: 1.0.0
---

# Transition & State Motion Engineering

`transition` provides production-grade patterns for fluid state transitions, page navigation morphing, and interactive micro-animations.

## The 4 Rules of UI Transitions

1. **GPU-Accelerated Only**: Only animate `transform` and `opacity`. Never transition `width`, `height`, `top`, `left`, `margin`, or `padding` to avoid layout reflows.
2. **Sub-300ms Duration**:
   - Micro-interactions (hover, click, toggle): **100ms - 150ms**
   - Modal dialogs, dropdown menus: **200ms - 250ms**
   - Full page / layout morphs: **250ms - 350ms**
3. **Easing Psychology**:
   - Entering elements: `cubic-bezier(0, 0, 0.2, 1)` (Decelerate / ease-out)
   - Exiting elements: `cubic-bezier(0.4, 0, 1, 1)` (Accelerate / ease-in)
   - Persistent movements: `cubic-bezier(0.4, 0, 0.2, 1)` (Standard / ease-in-out)
4. **Accessible Reduced Motion**: Always wrap transitions in `@media (prefers-reduced-motion: reduce)`.

## Modern Implementation Patterns

### 1. View Transitions API (React / Next.js)
```tsx
import { flushSync } from 'react-dom';

function navigateWithTransition(updateDom: () => void) {
  if (!document.startViewTransition) {
    updateDom();
    return;
  }
  document.startViewTransition(() => {
    flushSync(() => {
      updateDom();
    });
  });
}
```

```css
::view-transition-old(root),
::view-transition-new(root) {
  animation-duration: 250ms;
  animation-timing-function: cubic-bezier(0.2, 0, 0, 1);
}
```

### 2. High-Performance Dropdown & Modal Transition
```css
.modal-backdrop {
  opacity: 0;
  transition: opacity 200ms ease-out;
  pointer-events: none;
}
.modal-backdrop.is-open {
  opacity: 1;
  pointer-events: auto;
}

.modal-content {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
  transition: opacity 200ms ease-out, transform 200ms cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-backdrop.is-open .modal-content {
  opacity: 1;
  transform: scale(1) translateY(0);
}
```
