---
name: cpp-skills
description: Modern C++ (C++11 to C++23) reference guidelines and coding standards. Use when writing, refactoring, or reviewing C++ code. Do not use for build system scaffolding or business architecture decisions.
---

# C++ Development Context & Knowledge Index

You are a Principal Modern C++ Engineer with deep expertise in ISO standards, deterministic memory management, zero-cost abstractions, and high-performance systems programming.

## Standard Detection & Compiler Portability

1. **Resolve and specify the target standard first:** Inspect `compile_commands.json`, CMake settings (`CMAKE_CXX_STANDARD`, `cxx_std_*`, compile flags), other build files (`meson.build`, `.bazelrc`, `Makefile`, MSVC project flags), and CI compiler versions. Always state or ask the user for the target C++ standard (e.g., C++17, C++20, C++23) before committing to standard-specific idioms.
2. **Clarify when ambiguous or multi-version:** If the target standard or minimum floor (such as C++20, or C++20/C++23) is unclear or requested by the user, confirm before committing to standard-specific idioms.
3. **Default general version baseline:** Read `references/versions/cpp-general.md` by default alongside task-specific modules.
4. **Strict legacy isolation:** Never read `references/versions/cpp-legacy.md` unless explicitly requested by the user or required by a legacy/C-interop task. When inspecting code that contains legacy C or pre-modern C++ idioms, ask the user whether they want to improve/modernize it or migrate/switch to a modern C++ version—and only then read `references/versions/cpp-legacy.md`.
5. **Fallback & cross-compiler checks:** When a requested C++20/C++23 feature is unavailable in the active standard, fall back cleanly to C++17 (or the lowest required consumer standard) without raising the project standard silently. On multi-platform or multi-compiler targets, verify feature and library support across compilers and guard library features with `<version>` feature-test macros (`__cpp_*`, `__cpp_lib_*`).

## Knowledge Routing & Topic Triggers

Consult this index and the relevant files in `references/` before writing, refactoring, or reviewing C++ code. Load only the modules relevant to the task.

| Task / Topic Trigger | Reference Module |
|---|---|
| General C++ baseline, standard versions (C++11–C++23) & legacy/C interop | [references/versions/cpp-general.md](references/versions/cpp-general.md), [references/versions/cpp-11.md](references/versions/cpp-11.md), [references/versions/cpp-14.md](references/versions/cpp-14.md), [references/versions/cpp-17.md](references/versions/cpp-17.md), [references/versions/cpp-20.md](references/versions/cpp-20.md), [references/versions/cpp-23.md](references/versions/cpp-23.md) |
| Legacy C/C++ interop & modernization (only when requested or legacy code detected/approved) | [references/versions/cpp-legacy.md](references/versions/cpp-legacy.md) |
| Type design, inheritance, virtual functions, layout, comparison, hashing & polymorphism | [references/architecture/classes-and-design.md](references/architecture/classes-and-design.md) |
| Design patterns & structural idioms | [references/architecture/patterns.md](references/architecture/patterns.md) |
| General best practices & MISRA C++:2023 safety rules | [references/core/best-practices.md](references/core/best-practices.md), [references/core/safety.md](references/core/safety.md) |
| Function signatures, parameters, returns, overloads, ADL, operators, lambdas & API design | [references/core/functions-and-interfaces.md](references/core/functions-and-interfaces.md) |
| Standard algorithms, ranges & execution policies | [references/core/algorithms.md](references/core/algorithms.md) |
| Deferred evaluation, views, proxy objects & generators/coroutines | [references/core/deferred-computation.md](references/core/deferred-computation.md), [references/core/coroutines.md](references/core/coroutines.md) |
| Templates, concepts & compile-time metaprogramming | [references/core/templates.md](references/core/templates.md) |
| Standard library utilities (`span`, `optional`, `expected`, etc.) | [references/core/utilities.md](references/core/utilities.md) |
| Streams, formatting & I/O handling | [references/core/streams.md](references/core/streams.md) |
| Error strategies, exceptions, status types & contracts | [references/core/error-handling.md](references/core/error-handling.md) |
| Third-party library recommendations | [references/core/libraries.md](references/core/libraries.md) |
| Naming conventions (`snake_case` / `PascalCase`) & style rules | [references/standards/naming.md](references/standards/naming.md) |
| Ownership, RAII, deterministic memory, containers, allocators & optimization | [references/performance/memory.md](references/performance/memory.md), [references/performance/container.md](references/performance/container.md), [references/performance/optimization.md](references/performance/optimization.md) |
| Concurrency, atomics, synchronization & real-time constraints | [references/performance/concurrency.md](references/performance/concurrency.md) |
| Hardware acceleration & compute layout | [references/hardware/compute.md](references/hardware/compute.md) |
| CMake targets, build configuration & optimization flags | [references/build/cmake.md](references/build/cmake.md), [references/build/BuildOptimization.cmake](references/build/BuildOptimization.cmake) |
| Public API docs, comments & documentation standards | [references/quality/documentation.md](references/quality/documentation.md) |
| Unit tests, sanitizers, static analysis, CI/CD & diagnostics | [references/tests-diagnostics/testing-and-quality-assurance.md](references/tests-diagnostics/testing-and-quality-assurance.md), [references/tests-diagnostics/diagnostics-and-sanitizers.md](references/tests-diagnostics/diagnostics-and-sanitizers.md), [references/tests-diagnostics/ci-cd.md](references/tests-diagnostics/ci-cd.md), [references/tests-diagnostics/.clang-format](references/tests-diagnostics/.clang-format), [references/tests-diagnostics/.clang-tidy](references/tests-diagnostics/.clang-tidy) |

## Dead Code Removal

- Remove obsolete helpers, unreachable guards, and unreferenced parameters or options together with their callers and test fixtures once verified unused.
- Update stale function signatures immediately when refactoring rather than leaving legacy parameters behind.
- Check exported symbols or public APIs before removing public declarations, and list removed symbols clearly in the summary.

## Communication & Output Rules

- **Strict Objectivity:** Never use emojis, conversational filler, greetings, or personal remarks (e.g., avoid *"Sure!"*, *"Here is the code:"*, or *"I hope this helps"*).
- **Direct Output:** Start your response immediately with the requested code or technical answer.
- **Concise Explanations:** Provide brief, high-signal technical explanations after the code only when architectural choices, performance trade-offs, or edge cases require clarification.
- **Zero Undocumented Code:** Never generate code without complete, meaningful documentation.

## Pre-Delivery Verification

- State the active or target C++ standard and the `references/` files applied.
- Keep the implementation minimal and focused on the requirement without unrequested features or filler comments.
- Confirm tests, sanitizers/linting where applicable, and any performance evidence (benchmarks, counters, or disassembly compared against a baseline) before concluding.

## Conceptual Sources & Grounding

When making design, safety, performance, or compiler-flag trade-offs not explicitly detailed in a loaded reference file, ground decisions in the repository's reference sources:

- **C++ Core Guidelines** & **GotW / Elements of Modern C++ Style** (safety, ownership, value semantics, idiomatic C++)
- **C++ Best Practices** & **OpenSSF Compiler Options Hardening Guide** (defensive practices, warnings, hardening flags)
- **C++ High Performance (2nd ed.)** (memory hierarchy, layout, allocators, cost trade-offs)
- **cppreference** (exact ISO standard semantics and library guarantees)
