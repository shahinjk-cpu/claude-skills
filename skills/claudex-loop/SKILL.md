---
name: claudex-loop
description: >
  Autonomous recursive agent loop (Ralph loop / Claude execution loop). Implements goal-driven iterative cycles: analyze, generate, test, critique, and self-heal until goal passes.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: claudex loop, ralph loop, autonomous loop, self-healing agent, agent recursion
---

# Claudex Loop — Autonomous Iterative Execution Engine

Executes multi-step complex tasks through a closed-loop self-refining execution protocol that refuses to quit until all verification gates pass.

## The Closed-Loop Algorithm
1. **Hypothesis & Plan**: Formulate explicit expected outcome and success metrics.
2. **Execute**: Run targeted action or code modification.
3. **Verify**: Run automated tests, linters, or visual checks immediately.
4. **Critique**: If failed, capture exact error stack, form root cause analysis, and mutate plan without repeating identical mistakes.
