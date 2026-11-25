---
name: ai-session-optimizer
description: >-
  Claude Code and LLM session timing tricks, 5-hour window maximization, peak-hours routing, and cost-reduction heuristics.
---

# AI Session Optimizer & Timing Heuristics

Proven heuristics to maximize session limits, bypass peak-hour throttling, and eliminate wasted quota across Claude, Gemini, and OpenAI.

## 1. The 5-Hour Session Window Maximizer
- **Session Kickstart**: Send a minimal 1-token message (e.g. `ping` or `ok`) 2–3 hours before starting heavy work.
- **Window Reset Benefit**: When your peak work begins, the 5-hour rolling rate window will reset midway through your session, giving you effectively 2x capacity!

## 2. Peak Hours Avoidance Strategy
- **Peak Load Hours**: Weekdays 5:00 AM – 11:00 AM PT (1:00 PM – 7:00 PM GMT).
- During peak hours, route non-critical research or repetitive batch tasks to Gemini 2.5 Flash or local models via `InferSSD`.
- Reserve premium models (Claude 3.7 Sonnet / Opus) for architecture and final code validation.
