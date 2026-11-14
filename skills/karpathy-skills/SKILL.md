---
name: karpathy-skills
description: >
  Andrej Karpathy coding guidelines and deep learning principles. Zero silent assumptions, minimal runnable examples, verified math, neural nets from scratch, and anti-bloat simplicity.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: karpathy, andrej karpathy, neural nets from scratch, clean code, no bloat, micrograd
---

# Karpathy Skills — Radical Simplicity & Deep Learning Fundamentals

Programming guidelines and AI engineering principles inspired by Andrej Karpathy's philosophy: radical simplicity, zero bloat, building from first principles, and rigorous empirical verification.

## Core Rules
1. **No Silent Assumptions**: If an input format or requirement is ambiguous, check the data explicitly rather than guessing.
2. **Minimal Runnable Example**: When building or debugging, construct the smallest possible working script (10-30 lines) that proves the concept before scaling.
3. **Start Flat & Simple**: Do not create complex class hierarchies or abstractions until you feel the physical pain of repetition.
4. **Inspect the Tensors**: Always print shapes, min, max, mean, and check for NaNs at every forward/backward pass.
