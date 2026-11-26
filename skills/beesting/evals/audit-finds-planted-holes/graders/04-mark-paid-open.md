---
type: llm
focus: trace
weight: 1
---

SECURITY_AUDIT.md states that mark_paid is SECURITY DEFINER, executable by anon/PUBLIC and has no staff check, so anyone can mark any order paid.
