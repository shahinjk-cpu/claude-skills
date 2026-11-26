# Modern C++23 & MISRA Best Practices

## Overview

A consolidated checklist of core best practices for building safe, deterministic, and high-performance C++23 applications, blending modern standard idioms (RAII, Concepts, Ranges, Lambdas) with safety-critical rules from **MISRA C++:2023**.

## Source Files, Physical Design & ABI Boundaries

- **Header vs. Source Split**: Keep headers focused on what callers need—declarations, templates, `inline` functions, and `constexpr` entities—and move non-inline definitions and implementation details into source files. Never define non-inline functions or non-`constexpr` variables in a header, and keep `using namespace` directives out of headers (prefer targeted `using` declarations when needed).
- **Self-Contained & Minimal Includes**: Include every header you directly use rather than relying on transitive includes, while omitting unneeded headers to protect compile times and avoid unnecessary rebuilds. Order includes from most specific to most general (own header, project headers, third-party headers, standard library headers) so each header proves self-containment, and enforce standalone compilation in tests.
- **Forward Declarations & Include Guards**: Forward-declare types when only a pointer or reference appears in a header, but include the full definition for `enum` types so underlying-type mismatches cannot alter struct sizes. Guard headers with `#pragma once` or project/path-prefixed include guards without leading underscores.
- **Namespace Discipline**: Keep project symbols inside a dedicated project namespace rather than global scope (reserving global scope for `main`), use a `detail` namespace for language-required implementation entities, and scope OS-visible IPC names and session entities cleanly to avoid collisions. Never open `namespace std` except for permitted user-type specializations.
- **Internal Linkage & Anonymous Namespaces**: Place `.cpp`-local helpers, constants, and types in an anonymous namespace (or use `static` on single free functions) so the compiler can inline or strip internal symbols freely without linkage leaks. Never place an unnamed namespace inside a header, as it generates distinct per-translation-unit entities; use inline namespaces intentionally for ABI versioning.
- **One-Definition Rule (ODR) & Build Consistency**: Ensure inline functions, templates, and class definitions match identically across every translation unit. Compile all translation units of a binary with consistent language standards, preprocessor macros, sanitizer flags, and standard library configurations to prevent subtle ODR violations or linker mismatches. Note that internal-linkage entities in headers duplicate per translation unit, whereas a `static` local inside an `inline` function is shared across translation units.

## Memory Management & Value Semantics

- **Strict RAII (Resource Acquisition Is Initialization)**: Bind the lifetime of every resource (memory, file descriptors, locks, sockets) to stack-allocated objects with deterministic destructors. Never use raw `new` or `delete`.
- **Smart Pointers**: Default to `std::unique_ptr` for exclusive ownership and `std::shared_ptr` (with `std::weak_ptr` to break cycles) only when shared ownership is strictly required. Allocate via `std::make_unique` and `std::make_shared`.
- **Move Semantics**: Implement move constructors and move assignment operators as `noexcept` for resource-owning classes, and transfer ownership cleanly using `std::move` and `std::forward`.
- **Rule of Zero**: Design classes so they do not require custom destructors, copy/move constructors, or copy/move assignment operators by relying on standard RAII wrappers.

## Lambda Expressions & Functional Idioms

- **Explicit Captures**: Avoid default capture modes (`[=]` or `[&]`) in non-trivial or asynchronous scopes to prevent dangling references or unintended copies; capture variables explicitly (`[x, &y]`) or use generalized init-captures (`[ptr = std::move(p)]`).
- **Concise & Pure Lambdas**: Keep lambdas short, focused, and stateless whenever possible so the compiler can inline them effortlessly into algorithms and views.
- **`constexpr` & Template Lambdas (C++20/23)**: Leverage implicit `constexpr` evaluation and explicit template parameter lists (`[]<typename T>(const T& val) { ... }`) for type-safe generic callbacks.

## Generic Programming, Ranges & Algorithms

- **Concepts Over SFINAE**: Constrain templates with `concept` definitions and `requires` clauses (`<concepts>`) to enforce clear compile-time contracts and readable diagnostics.
- **Declarative Algorithms & Ranges**: Prefer `std::ranges` algorithms and lazy `std::views` pipelines over raw `for` loops to eliminate off-by-one errors and express intent clearly.
- **Immutability by Default**: Mark variables, member functions, and references `const` (and `constexpr`/`consteval` where applicable) unless mutation is explicitly required.

## Concurrency, Asynchronous & Real-Time Processing

- **Safe Multithreading**: Manage threads via RAII (`std::jthread` where supported) and synchronize shared state using `std::scoped_lock` or lock-free `std::atomic` primitives.
- **Asynchronous Task Composition**: Use `std::async`, `std::future`, and `std::promise` (or task-based executors) for non-blocking background work without manual thread lifecycle management.
- **Real-Time Determinism**: On real-time critical paths:
  - Avoid dynamic heap allocations (`new`, `std::vector` resizing, `std::function` heap fallback); pre-allocate buffers at startup or use fixed-capacity containers (`std::array`, `std::span`).
  - Avoid unbounded locks (`std::mutex`) on hard real-time threads; use lock-free single-producer/single-consumer (SPSC) queues or atomic flags.
  - Guarantee bounded execution times ($O(1)$ or deterministic $O(N)$) and avoid blocking I/O or exceptions on the hot path.

## MISRA C++:2023 Safety-Critical Guidelines

- **Eliminate Undefined & Unspecified Behavior**: Enforce universal brace initialization (`{}`) across all entities—variables, member initializers, return values, and smart pointers (e.g., `auto ptr { std::make_unique<int>(42) };` rather than `=`), banning legacy copy-initialization (`=`) and uninitialized declarations. Prevent signed integer overflow and eliminate dangling pointers or references.
- **Strong Type Safety**: Ban C-style casts in favor of `static_cast` or `std::bit_cast`, use `enum class`, and avoid implicit narrowing conversions.
- **Predictable Control Flow**: Ensure all switch statements handle all cases explicitly (`default:` or exhaustive `enum class`), avoid `goto`, and keep cyclomatic complexity low.
- **Compiler & Static Analysis Enforcement**: Compile with maximum warning levels treated as errors (`-Wall -Wextra -Wpedantic -Werror`) and validate compliance continuously with **Clang-Tidy** and static analyzers.

## Annotations

- **Discard Return Values (`[[nodiscard]]`)**: Annotate functions whose return value must not be ignored (`[[nodiscard]]`) so callers cannot silently drop status codes, resources, or computed results.
