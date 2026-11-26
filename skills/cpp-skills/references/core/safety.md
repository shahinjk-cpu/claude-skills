# Type Safety & Compile-Time Checks Reference

## Overview
Guidelines for enforcing strict type safety in modern C++, eliminating undefined behavior from unsafe casts, leveraging scoped enumerations, and utilizing compile-time assertions.

## Explicit Casting & Type Conversions
* **Avoid C-Style Casts**: Never use legacy C-style casts (`(type)expression`), which blindly perform `const_cast`, `static_cast`, or `reinterpret_cast` implicitly and dangerously.
* **Controlled Casting**: Use explicit C++ cast operators:
  * `static_cast`: For well-defined, checked conversions (e.g., numeric promotions, base-to-derived pointers).
  * `dynamic_cast`: For safe polymorphic downcasting (requires RTTI).
  * `const_cast`: Strictly for adding or removing `const` qualifiers when interfacing with legacy APIs.
* **Safe Bit Reinterpretation**: Avoid `void*` pointer aliasing and strict-aliasing violations. Use `std::bit_cast` (C++20) for safe, bitwise type punning between trivially copyable types, or `std::bitset` for bit-level manipulation, keeping `reinterpret_cast` as a last resort for low-level hardware or driver code.

## Enumerations & Initialization
* **Scoped Enumerations**: Use `enum class` instead of plain `enum` to prevent implicit integer conversions, namespace pollution, and type scoping issues.
* **Null Pointer Constant**: Always use `nullptr` instead of `NULL` or `0` to ensure strict pointer type safety.
* **Uniform Initialization**: Initialize variables using uniform brace initialization (`{}`, list-initialization) rather than assignment (`=`) to prevent narrow conversions and eliminate the "most vexing parse".

```bash
int a {5};
```

## Compile-Time Validation (`static_assert`)
* **Compile-Time Constraints**: Use `static_assert` inside functions, classes, and template structures to validate invariants, type traits (via `<type_traits>`), and architectural assumptions at compile time before any code runs.
* **Template Safety**: Combine `static_assert` with concepts or type traits to ensure templates receive valid template arguments, producing clear, readable compilation errors instead of cryptic template substitution failures (SFINAE noise).

## Compiler Warnings & Strictness
* **Warnings as Errors**: Enable aggressive compiler warning levels (e.g., `-Wall -Wextra -Werror` on GCC/Clang, `/W4 /WX` on MSVC) and treat all warnings as errors to catch latent bugs immediately in the CI/CD pipeline.