---
name: neumorphism-design
description: >-
  Modern Neumorphism and Soft UI design guidelines, dual-drop shadows, extruded convex/concave surfaces, and tactile button component architecture.
---

# Neumorphism & Soft UI Design System

A modern implementation of Neumorphism focusing on high accessibility, subtle dual lighting, and tactile physical realism.

## Dual Light Source Shadow Formula
In light mode (`#e0e5ec`):
```css
.neu-flat {
  background: #e0e5ec;
  box-shadow: 9px 9px 16px rgb(163,177,198,0.6), 
             -9px -9px 16px rgba(255,255,255, 0.5);
}
.neu-pressed {
  background: #e0e5ec;
  box-shadow: inset 6px 6px 10px rgb(163,177,198,0.7), 
             inset -6px -6px 10px rgba(255,255,255, 0.7);
}
```

In dark mode (`#18191c`):
```css
.neu-dark {
  background: #18191c;
  box-shadow: 8px 8px 16px #0e0f11, 
             -8px -8px 16px #222327;
}
```

## Best Practices
- Keep contrast ratios WCAG AA compliant by pairing soft surfaces with crisp inner typography and borders.
- Use pressed states exclusively on `:active` and toggle states.
