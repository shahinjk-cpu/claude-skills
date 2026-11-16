---
name: cta-gallery
description: High-converting Call-to-Action (CTA) sections, magnetic button interactions, banner triggers, and trial onboarding blocks inspired by cta.gallery. Powered by the ctagallery MCP server (C:\Claude\ctagallery\server.py) to generate production-ready React + Tailwind CTA components and conversion copy.
metadata:
  version: "1.1.0"
  role: conversion_rate_optimizer
  transport: stdio
  command: python C:\Claude\ctagallery\server.py
  triggers: cta, cta gallery, call to action, duyme dizayni, konversiya, waitlist form, bento cta, pricing cta, lead capture
---

# Call to Action (CTA) Gallery Architecture & MCP Tools

`cta-gallery` provides architectural patterns and live MCP tools for high-converting, aesthetically refined Call-to-Action sections based on curated designs from [cta.gallery](https://www.cta.gallery).

## Available MCP Tools (via `ctagallery` MCP Server)

1. **`get_cta_categories`**:
   - Returns all CTA categories: `button` (glow, shimmer, 3D), `form` (waitlist, email capture), `pricing` (tier triggers), `modal-pop-up` (exit-intent), `newsletter`, `navigation`, `call-to-buy`, `templates` (full bento banners).
2. **`get_cta_copywriting_rules`**:
   - Returns conversion copywriting frameworks: action verbs, friction reducers ("No credit card required"), social proof anchors, and visual hierarchy rules.
3. **`search_cta_patterns(query, category?)`**:
   - Live lookup for Tailwind CSS and Framer Motion CTA code patterns.
4. **`generate_cta_component(cta_type, headline, button_text, subtext)`**:
   - Generates production-ready, beautiful React + Tailwind CTA code.

## Key CTA Archetypes

### 1. The Floating Dark-Glass Card CTA (The "Bottom Anchor")
- **Layout**: Centered elevated container placed just before the footer (`max-w-5xl mx-auto my-20 p-12 rounded-3xl`).
- **Surface**: Gradient border with deep radial glow (`bg-gradient-to-b from-neutral-900 to-neutral-950 border border-white/10 shadow-[0_0_80px_-20px_rgba(99,102,241,0.25)]`).
- **Typography**: Big high-contrast headline ("Ready to scale your engineering?"), short subtext, and a primary high-contrast action button.
- **Trust Elements**: Small avatar cluster + "Joined by 12,000+ developers" + "No credit card required • 14-day free trial".

### 2. Split-Screen Interactive CTA (Dual Intent)
- **Structure**: 2-column card separating two distinct user paths:
  - *Left (Self-Serve / Free)*: "Start building today" -> Primary button (`Get Started Free`).
  - *Right (Enterprise / Sales)*: "Need a custom deployment?" -> Secondary outlined button (`Talk to Solutions Team`).
- **Best For**: Developer tools, infrastructure platforms, SaaS with both PLG and enterprise motions.

### 3. Magnetic Glow Button (Micro-CTA)
- **Interaction**: Button with interactive cursor magnetism and a fluid radial light trail following mouse movement along the border (`radial-gradient(circle at var(--mouse-x) var(--mouse-y), rgba(255,255,255,0.2), transparent 40%)`).
- **Feedback**: Active scale down (`active:scale-95`), spring pop on hover.

### 4. Sticky Bottom Conversion Ribbon
- **Behavior**: Appears smoothly as user scrolls past 60% of the landing page.
- **Layout**: Slim floating bar docked at the bottom of the viewport (`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 p-3 px-6 rounded-full glass`).
- **Content**: Left: Value proposition reminder ("Ship faster with AI"); Right: Single primary CTA button + Dismiss ('X') icon.

## Conversion Principles & Rules

1. **One Primary Action**: Never compete between two equally dominant primary buttons. Always maintain a clear visual hierarchy (Solid Primary vs Ghost/Outlined Secondary).
2. **Friction Reducers**: Always position reassurance triggers near the action button (e.g., "Free 14-day trial", "Cancel anytime", "SOC-2 Certified", "Open Source").
3. **Copywriting Clarity**: Action verbs that state the immediate benefit (e.g., "Deploy in 60 seconds", "Claim your free domain", "Explore the interactive playground").
