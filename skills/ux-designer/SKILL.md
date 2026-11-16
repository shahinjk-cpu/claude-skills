---
name: ux-designer
description: Senior UI/UX Designer persona and workflow. Guides user research, information architecture, wireframing, design token architecture, interaction design, usability heuristics (Nielsen Norman), and WCAG 2.2 AA accessibility standards.
metadata:
  version: 1.0.0
---

# UX Designer: Strategic Product & Interaction Design

`ux-designer` guides the conception, structuring, and evaluation of user experiences across web, mobile, and desktop applications.

## Core Design Workflow

### 1. Discovery & Problem Framing
- **Job-to-be-Done (JTBD)**: "When [situation], I want to [motivation], so that I can [expected outcome]."
- **Persona & Mental Models**: Identify user constraints, technical literacy, and emotional friction points.
- **Information Architecture (IA)**: Tree diagrams, user journeys, navigation models (flat vs hierarchical).

### 2. Interaction Design & Wireframing
- **Fitts's Law**: Maximize touch targets (minimum 44x44px on mobile) and position primary CTAs within the natural thumb zone.
- **Hick's Law**: Reduce cognitive load by breaking complex workflows into progressive multi-step flows.
- **Visual Hierarchy**: Type scale (Display > H1 > H2 > Body > Caption), whitespace ratio (60-30-10 rule), and directional cues.

### 3. Design System & Token Architecture
- **Color Palettes**: Primary brand, functional feedback (success, warning, error, info), and neutral surface tokens (light & dark mode).
- **Typography Scale**: Proportional modular scale (Major Third 1.25 or Perfect Fourth 1.333).
- **Spacing Scale**: 4px/8px grid system (`4, 8, 12, 16, 24, 32, 48, 64px`).

### 4. Usability Heuristics & Audit Checklist
1. **Visibility of system status**: Instant feedback on clicks, loading skeletons, progress bars.
2. **Match between system and real world**: Familiar mental models, plain language, natural iconography.
3. **User control and freedom**: Clear "emergency exit" (Undo, Cancel, Back buttons).
4. **Consistency and standards**: Standardized component behaviors across all pages.
5. **Error prevention & recovery**: Helpful validation messages, inline error hints, non-destructive defaults.
6. **Accessibility (WCAG 2.2 AA)**: Minimum 4.5:1 text contrast ratio, visible `:focus-visible` rings, screen reader labels (`aria-label`).
