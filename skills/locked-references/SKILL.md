---
name: locked-references
description: >-
  Multi-shot visual consistency framework for AI video and image models using invariant reference anchors, seed preservation, and locked attribute sets.
---

# Locked References — AI Video & Image Visual Consistency

Ensures that characters, outfits, faces, props, and lighting remain 100% consistent across multiple generated scenes and camera angles.

## The 4 Anchor Principles
1. **Attribute Passports**: Lock exact color hex codes, fabrics, haircuts, and facial markers.
2. **Static Seed & Seed-Shift**: Fix base image seed, modify only camera angle or motion prompts.
3. **Identity Tokens**: Use unique pseudo-names (e.g., `Character_A_Alex_LeatherJacket_v2`) to prevent generic model drift.
4. **IP-Adapter / ControlNet Conditioning**: Always condition generation on the original turnaround sheet.
