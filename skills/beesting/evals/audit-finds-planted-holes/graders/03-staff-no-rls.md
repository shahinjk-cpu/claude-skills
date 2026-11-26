---
type: llm
focus: trace
weight: 1
---

SECURITY_AUDIT.md states that the staff table has no RLS, so a user can add themselves to staff and gain operator rights (e.g. set_status).
