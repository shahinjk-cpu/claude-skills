# Error Handling & Exception Safety

## Overview
Guidelines for robust error handling, contracts, and exception safety in modern C++, balancing value-based result types (`std::optional`, `std::expected`) for expected failures with exceptions, assertions, and strict exception safety guarantees where appropriate.

## Choose One Strategy per Interface
Commit to a single, explicit error strategy per interface rather than mixing exceptions and status codes inconsistently:

| Failure Kind | Mechanism |
|---|---|
| Programming error or broken precondition | Assertion in debug builds, hard fail in release (do not treat as recoverable business logic) |
| Expected failure (parse error, not found, would block) | Result type: `std::optional`, `std::expected` (C++23), or an explicit project status/result type |
| Exceptional failure (resource exhaustion, runtime invariant violation) | Exception (when exceptions are enabled) |
| Unrecoverable state (corrupted state, failure during unwinding/destruction) | Terminate |

- When exceptions are disabled in a project or target, rely consistently on result types and document that choice clearly.

## Value-Based Result Types (`std::expected` & `std::optional`)
- **`std::optional<T>`**: Use when absence alone carries sufficient meaning without a specific error reason.
- **`std::expected<T, E>` (C++23)**: Prefer `std::expected<T, E>` (from `<expected>`) over ad-hoc error codes or output parameters when callers need the failure reason (e.g., parsing, I/O, validation). Before C++23, use `std::variant<T, E>` or a dedicated result type of equivalent shape.
- **Monadic Composition**: Use monadic operations (`.and_then()`, `.transform()`, `.or_else()`, `.transform_error()` in C++23) to chain steps cleanly while accounting for move costs per step.
- **Error Type Design**: Pair `std::expected` with strongly typed `enum class` descriptors, `std::error_code` at system boundaries, or compact error types—avoiding heap-allocated strings on hot failure paths. Mark result return values `[[nodiscard]]` so errors cannot be silently ignored, and `static_assert` visitor invocability across all alternatives of a `std::variant`.

## Exception Handling Strategy
- **Exceptional Conditions Only**: Throw exceptions for truly exceptional conditions or broken runtime invariants—never for normal control flow or hot paths.
- **Throw by Value, Catch by `const&`**: Throw exception objects by value (deriving from `std::exception` or a domain base derived from it with diagnostic context) and always catch by `const` reference (`catch (const CustomException& e)`) to prevent slicing and avoid unnecessary copies.
- **Preserve Original Exceptions**: Rethrow active exceptions using bare `throw;` rather than `throw e;` to preserve the dynamic type and context.
- **Boundary Rules**: Never allow exceptions to escape a destructor (which calls `std::terminate` during unwinding) or cross a `C` ABI boundary (catch and translate at the boundary). Restrict `catch (...)` to top-level boundaries (`main`, thread entry points, plugin boundaries) that log and rethrow or terminate deliberately rather than swallowing errors.

## `noexcept` & Exception Safety Guarantees
- **`noexcept` Discipline**: Mark functions `noexcept` only when the non-throwing guarantee is genuine—such as destructors, `swap`, move operations, and simple non-throwing accessors. Apply the Lakos rule: avoid `noexcept` on narrow contracts even when valid inputs do not throw; document non-throwing behavior instead.
- **Guarantee Tiers**: Make each function's exception safety guarantee clear:
  - **Nothrow**: Guaranteed not to fail; required for destructors, `swap`, move operations, and operations relied upon during container reallocation.
  - **Strong**: Commit-or-rollback semantics—if an operation fails, observable state remains unchanged as if the call had not occurred (often achieved via copy-and-swap or staging before committing with non-throwing operations).
  - **Basic**: Invariants remain intact and no resources leak on failure, even if observable state changes.
  - **None**: Unacceptable in new code.
- **Container Reallocation & Staging**: Perform operations that may throw before mutating final state via non-throwing moves/swaps, and note that containers provide the strong guarantee on reallocation only when element move constructors are `noexcept` (otherwise falling back to copies).

## Preconditions, Assertions & Invariants
- **Compile-Time & Type-Level Enforcement**: Prefer `static_assert` with clear messages, `concepts`, or strong types / non-representable invalid states over runtime checks whenever possible.
- **Boundary & `assert` Discipline**: Validate invariants at module boundaries rather than repeating checks on every internal helper. Remember that `assert` compiles out under `NDEBUG` and must never contain side effects or behavior that differs silently between debug and release builds; enforce release-required preconditions with explicit checks.

## Testing Failure Paths
- **Explicit Failure Coverage**: Test error branches and `catch` handlers directly rather than only happy paths.
- **Fault Injection & Sanitizers**: Exercise failure paths with fault injection (such as throwing allocators, failing mocks, or truncated inputs) and verify resource cleanup and memory/undefined-behavior correctness under sanitizers and leak checkers.
