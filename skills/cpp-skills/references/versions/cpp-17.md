# C++17

## Overview

C++17 is a major standard version following C++14, introducing major features such as structured bindings, `constexpr if`, fold expressions, filesystem library, `std::optional`, `std::variant`, `std::any`, and parallel algorithms.

## Merged Technical Specifications & Standards
* **File System TS**: The filesystem library (`std::filesystem`).
* **Library Fundamentals v1 TS**: `std::any`, `std::optional`, `std::string_view`, `std::apply`, polymorphic allocators, searchers.
* **Library Fundamentals v2 TS**: `std::void_t`, `std::conjunction`, `std::disjunction`, `std::negation`, `std::not_fn`, `std::gcd`, `std::lcm`.
* **Parallelism v1 TS**: Execution policies, `std::reduce`, `std::inclusive_scan`, `std::exclusive_scan`.
* **C11 Library**: `std::aligned_alloc`, `std::timespec_get`.

## New Language Features

* `u8` character literals
* `noexcept` made part of the type system
* Stricter order of evaluation rules
* Lambda capture of `*this` by copy
* Compile-time `if constexpr`
* `constexpr` lambda expressions
* **Variables**:
  * Inline variables (`inline`)
  * Structured bindings (`auto [x, y] = pair;`)
  * Init-statements and initializers for `if` and `switch`
  * Guaranteed copy elision and temporary materialization rules
* **Templates**:
  * Unary and binary fold expressions (`(...)`)
  * Class template argument deduction (CTAD), e.g., `std::tuple t(4, 3, 2.5);`
  * Non-type template parameters declared with `auto`
* **Namespaces & Attributes**:
  * Simplified nested namespaces (`namespace a::b::c {}`)
  * Using-declaration declaring multiple names
  * Attribute namespaces without repetition
  * New attributes: `[[fallthrough]]`, `[[maybe_unused]]`, `[[nodiscard]]`
  * Preprocessor support for `__has_include`

## New Headers

* `<any>`
* `<charconv>`
* `<execution>`
* `<filesystem>`
* `<memory_resource>`
* `<optional>`
* `<string_view>`
* `<variant>`

## New Library Features

### Utility Types & Containers
* `std::tuple` enhancements (`std::apply`, `std::make_from_tuple`, deduction guides)
* `std::any` (type-safe container for single values of any type)
* `std::optional` (may or may not hold a value)
* `std::variant` (type-safe union)
* `std::string_view` (non-owning string reference)
* `std::as_const` and `std::not_fn`
* Map/Set extract and merge, `try_emplace`, and `insert_or_assign`
* Non-member `std::size`, `std::empty`, and `std::data`

### Memory Management & Compile-Time Programming
* Uninitialized memory algorithms (`std::destroy_at`, `std::destroy`, `std::uninitialized_move`, etc.)
* `std::enable_shared_from_this::weak_from_this`
* `std::pmr::memory_resource` and `std::pmr::polymorphic_allocator`
* `std::byte` (distinct byte type)
* Type traits and logical operators (`std::conjunction`, `std::disjunction`, `std::negation`, `std::is_swappable`, `std::is_invocable`, `std::is_aggregate`)

### Algorithms & Numerics
* `std::clamp`
* Parallel algorithms and execution policies (`std::execution::par`, etc.)
* `std::gcd` and `std::lcm`
* Mathematical special functions and 3D `std::hypot`
* Elementary string conversions (`std::to_chars` / `std::from_chars`)
* `std::scoped_lock` and `std::launder`

## Compiler Support

### C++17 Core Language Features

| Feature | GCC | Clang | MSVC | Apple Clang | EDG eccp | Intel C++ | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| Nested namespace definition | 6 | 3.6 | 19.0 | 4.12 | 17.0 | 17.7 | 
| `static_assert` with no message | 6 | 2.5 | 19.10 | 4.12 | 18.0 | 17.7 | 
| `u8` character literals | 6 | 3.6 | 19.0 | 4.11 | 17.0 | 17.7 | 
| Unary fold expressions | 6 | 3.9 | 19.12 | 4.14 | 19.0 | 18.1 | 
| Lambda capture of `*this` | 7 | 3.9 | 19.11 | 4.14 | 19.0 | 18.1 | 
| `constexpr` lambda expressions | 7 | 5 | 19.11 | 4.14 | 19.0 | 18.1 | 
| `[[fallthrough]]` attribute | 7 | 3.9 | 19.10 | 4.13 | 18.0 | 17.7 | 
| `[[nodiscard]]` attribute | 7 | 3.9 | 19.11 | 4.13 | 18.0 | 17.7 | 
| `[[maybe_unused]]` attribute | 7 | 3.9 | 19.11 | 4.13 | 18.0 | 17.7 | 
| Guaranteed copy elision | 7 | 4 | 19.13 | 5.0 | 19.0.1 | 19.1 | 
| Structured Bindings | 7 | 4 | 19.11 | 4.14 | 19.0 | 18.1 | 
| `constexpr if` statements | 7 | 3.9 | 19.11 | 4.14 | 19.0 | 18.1 | 
| Init-statements for `if` and `switch` | 7 | 3.9 | 19.11 | 4.14 | 18.0 | 18.1 | 
| Inline variables | 7 | 3.9 | 19.12 | 4.14 | 19.0 | 18.1 | 
| Class template argument deduction | 7 | 5 | 19.14 | 5.0 | 19.0.1 | 19.1 | 

### C++17 Library Features

| Feature | GCC libstdc++ | Clang libc++ | MSVC STL | Apple Clang | 
| ----- | ----- | ----- | ----- | ----- | 
| `std::void_t` | 6 | 3.6 | 19.0 | Yes | 
| `std::uncaught_exceptions()` | 6 | 3.7 | 19.0 | Yes | 
| `std::size()`, `std::empty()`, `std::data()` | 6 | 3.6 | 19.0 | Yes | 
| `std::invoke` | 6 | 3.7 | 19.0 | Yes | 
| Parallel algorithms | 9 | 17 (partial) | 19.14 | 18.0 | 
| `std::clamp()` | 7 | 3.9 | 19.0 | 10.0.0 | 
| Polymorphic memory resources (`pmr`) | 9 | 16 | 19.13 | 15.0.0 | 
| `std::apply` | 7 | 11 | 19.13 | Yes | 
| `std::byte` | 7 | 5 | 19.11 | Yes | 
| `std::string_view` | 7 | 14 | 19.10 | 10.0.0 | 
| `std::any` | 7 | 14 | 19.10 | 10.0.0 | 
| `std::optional` | 7 | 14 | 19.10 | 10.0.0 | 
| `std::variant` | 7 | 14 | 19.10 | 10.0.0 | 
| `std::to_chars` / `std::from_chars` | 8 | 11 | 19.14 | 10.0.0 | 
| File system library (`std::filesystem`) | 8 | 7 | 19.14 | 11.0.0 | 
| `std::scoped_lock` | 7 | 5 | 19.11 | Yes | 
