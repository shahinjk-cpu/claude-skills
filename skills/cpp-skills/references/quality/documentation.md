# Code Documentation & API Reference Standards

## Overview

Guidelines for writing clear, maintainable, and automated documentation across C++23 codebases using Doxygen standards, ensuring public APIs, behavioral contracts, and concurrency guarantees are explicitly specified.

## Doxygen Formatting & Tags

- **Standard Comment Blocks**: Use Doxygen-compatible comment styles (`///` for single-line/brief comments and `/** ... */` for detailed multi-line blocks) on all headers and public interfaces. Every header file, namespace, class, struct, enum, concept, and function declaration must include a formal Doxygen comment block specifying `@brief`, `@param`, `@return`, and `@throws` (or `noexcept` guarantees) where applicable.
- **Structured Metadata Tags**: Use standard Doxygen tags consistently to enable automated API reference generation (HTML/XML/Sphinx):
  - `@brief`: Concise one-line summary of the class, function, or file.
  - `@tparam` & `@param`: Document template parameters and function arguments, specifying ownership (`[in]`, `[out]`, `[in,out]`) and preconditions.
  - `@return`: Describe return values, including `std::expected` error states or `std::optional` empty semantics.
  - `@throws` / `@exception`: Explicitly list exceptions thrown or guarantee `noexcept` behavior.
  - `@note` & `@warning`: Highlight critical edge cases, lifetime constraints, or performance caveats.

## Public API & Contract Documentation

- **Thorough Public Coverage**: Every public class, struct, free function, enum, and concept in `include/` must be fully documented; keep internal implementation details in `.cpp` files concise and focused on *why* rather than *what*.
- **Inline Comments (`//`)**: Use concise `//` comments inside function bodies to explain *why* non-obvious logic, memory optimizations, or hardware/OS constraints are implemented—never state the obvious.
- **Preconditions & Postconditions**: Clearly state valid input ranges, pointer non-nullability requirements, and guaranteed object states upon completion.
- **Usage Examples (`@code` / `@endcode`)**: Embed compilable, self-contained usage snippets directly inside class and complex function docblocks to demonstrate idiomatic usage.

## Thread Safety & Concurrency Contracts

- **Explicit Synchronization Guarantees**: Document the thread-safety level of every public class and function using clear, standardized terminology:
  - **Thread-Safe**: Safe for concurrent read and write access from multiple threads without external synchronization.
  - **Const-Safe (Thread-Compatible)**: Safe for concurrent `const` (read-only) access across threads, provided no thread mutates the instance simultaneously.
  - **Thread-Hostile / Not Thread-Safe**: Requires external synchronization (e.g., `std::scoped_lock`) or thread-affine execution.
- **Locking & Ordering Requirements**: Document any internal locks acquired, callback re-entrancy rules, or potential deadlock hazards.

## Maintenance & CI/CD Enforcement

- **Synchronized Updates**: Treat documentation updates as mandatory part of code reviews—any pull request modifying public signatures or behavior must update the corresponding Doxygen comments and `README.md` guides simultaneously.
- **Automated Documentation Builds**: Enforce warning-free Doxygen generation (`WARN_AS_ERROR = YES` in `Doxyfile`) within the CI/CD pipeline to catch broken references, undocumented parameters, and stale tags automatically.
