---
name: matt-pocock-skills
description: >
  TypeScript engineering mastery from Matt Pocock. Type-level programming, generics, type predicates, strict API schemas, Zod validation, and error-handling patterns.
metadata:
  version: "1.0.0"
  category: backend_api
  triggers: matt pocock, typescript wizardry, type-level programming, zod validation, typescript skills
---

# Matt Pocock Skills — TypeScript Wizardry & Type Engineering

Advanced TypeScript development patterns, type-level computation, and bulletproof API design straight from Matt Pocock's engineering practices.

## Core Patterns
1. **Derive, Don't Duplicate**: Derive types from runtime schemas using `z.infer<typeof Schema>` or `typeof Config`.
2. **Generics with Constraints**: Always constrain generic type arguments (`<T extends Record<string, unknown>>`).
3. **Narrowing with Type Predicates**: Use `is` guards (`function isError(val: unknown): val is Error`).
4. **Discriminated Unions**: Model domain states with shared `type` or `status` string literals for exhaustive switch cases.
