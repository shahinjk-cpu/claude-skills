---
name: written-gates-generation
description: >-
  Pre-generation evaluation gates, test specs, and validation checkpoints that block flawed generations before expensive model inference runs.
---

# Written Gates in Front of Generation

Written Gates are deterministic verification checks executed *before* launching expensive image, video, or code generation calls.

## Gate Checklist
- [ ] **Gate 1: Anchor Integrity**: Are all character/scene invariant attributes explicitly present in the prompt?
- [ ] **Gate 2: Negative Constraint Audit**: Are negative prompts aligned with forbidden mutations?
- [ ] **Gate 3: Camera & Lighting Check**: Does the prompt specify camera lens (e.g. 35mm, f/1.8), angle, and key lighting?
- [ ] **Gate 4: Budget & Resolution**: Are dimensions, aspect ratios, and step counts within allocation?

If any gate fails, halt generation and regenerate the prompt.
