---
type: llm
focus: trace
weight: 1
---

SECURITY_AUDIT.md notes that sb.rpc('mark_paid') in admin.html is neither awaited nor .then()-ed, so with supabase-js the request is never sent.
