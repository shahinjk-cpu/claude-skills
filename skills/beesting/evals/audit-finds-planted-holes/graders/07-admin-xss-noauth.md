---
type: llm
focus: trace
weight: 1
---

SECURITY_AUDIT.md flags admin.html: no authentication, and customer fields (name/address) inserted via innerHTML without escaping (stored XSS).
