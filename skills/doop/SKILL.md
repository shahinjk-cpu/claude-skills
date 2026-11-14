---
name: doop
description: >
  Declarative data deduplication, state diffing, and idempotent mutation pipeline. Prevents redundant API calls, duplicate database records, and distributed race conditions.
metadata:
  version: "1.0.0"
  category: backend_api
  triggers: doop, deduplication, state diff, idempotent api, dedupe records
---

# Doop — Declarative Deduplication & State Synchronization

Guarantees data cleanliness and idempotent operations across distributed data streams and local databases.

## Mechanisms
- Content-addressable hashing (SHA-256) of input payloads.
- Bloom filters for instantaneous zero-overhead membership testing.
- Two-way JSON diffing (`jsonpatch`) to emit minimal network mutation payloads.
