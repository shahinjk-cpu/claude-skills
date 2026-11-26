# C++23

## New Language Features

* New language feature testing macros
* Explicit object parameter, explicit object member functions, a.k.a. "deducing this"
* Multidimensional subscript operator (e.g. `v[1, 3, 7] = 42;`)
* `static operator[]`, `static operator()`, and static lambdas
* `auto(x)` and `auto{x}`: decay-copy in the language
* Assumptions via new attribute `[[assume(expression)]]`
* Attributes on lambda-expressions
* Optional extended floating-point types: `std::float{16|32|64|128}_t`, and `std::bfloat16_t`
* New preprocessor directives: `#elifdef`, `#elifndef`, and `#warning`
* Literal suffix `'Z'`/`'z'` for (signed) `std::size_t` literals, e.g. `auto ouz = 0uz;`
* White-spaces trimming before line splicing
* Simpler implicit move
* Extending the lifetime of temporaries in range-based for loop initializer
* CTAD from inherited constructors
* Labels at the end of compound statements
* Alias declarations (`using`) in init-statements, e.g. `for (using T = int; T e : v)`
* Make `()` more optional for lambda expressions
* Narrowing contextual conversions to `bool` in `static_assert` and `if constexpr`
* Make declaration order layout (of non-static class data members) mandated
* Text encoding changes:
  * Character sets and encodings
  * Consistent character literal encoding
  * Named universal character escapes, e.g. `"\N{CAT FACE}"` for `"🐱"`
  * Delimited escape sequences, e.g. `"\o{7777}"`, `"\x{C0DE}"`, `"\u{CAFE}"`
  * Support for UTF-8 as a portable source file encoding
* `if consteval` / `if not consteval`
* `constexpr` changes:
  * Non-literal variables, labels, and gotos in `constexpr` functions
  * Permitting `static` and `thread_local` variables in constant expressions in `constexpr` functions
  * `constexpr` function does not need its return type and parameter types to be literal type
  * `constexpr` function for which no invocation satisfies the requirements of a core constant expression

## New Library Features

* New library feature testing macros

### New Modules

* `std` and `std.compat`

### New Headers

* `<expected>`
* `<flat_map>`
* `<flat_set>`
* `<generator>`
* `<mdspan>`
* `<print>`
* `<spanstream>`
* `<stacktrace>`
* `<stdfloat>`

### C Compatibility Headers

* `<stdatomic.h>`

### General Utilities

* `std::expected`: a new vocabulary type to return a function's result (`<expected>`)
* `std::move_only_function`: a move-only callable wrapper
* `std::bind_back`: a call wrapper
* `std::byteswap`: reverses the bytes
* `std::forward_like`
* `std::invoke_r`: invokes a Callable object
* `std::to_underlying`: a utility function to get the underlying value of enum
* `std::unreachable`: a function to mark unreachable code
* Monadic operations (`transform`, `or_else`, and `and_then`) for `std::optional` and `std::expected`
* `std::tuple` is compatible with other tuple-like objects
* Adding default arguments for `std::pair`'s forwarding constructor
* `std::basic_common_reference` specialization for `std::reference_wrapper` yielding reference types

### Coroutine Library

* `std::generator`: synchronous coroutine generator for ranges

### Diagnostic

* Stacktrace library

### Algorithm, Iterators, and Ranges

* New range adaptors:
  * `views::adjacent` and `views::adjacent_transform`
  * `views::as_const`
  * `views::as_rvalue`
  * `views::cartesian_product`
  * `views::chunk_by`
  * `views::chunk`
  * `views::enumerate`
  * `views::join_with`
  * `views::repeat`
  * `views::slide`
  * `views::stride`
  * `views::zip`, `views::zip_transform`
* `ranges::range_adaptor_closure`: a helper for program-defined range adaptor closures
* `ranges::to`: a range conversion function
* New constrained ranges algorithm:
  * `ranges::starts_with` and `ranges::ends_with`
  * `ranges::contains` and `ranges::contains_subrange`
  * `ranges::find_last`, `ranges::find_last_if`, and `ranges::find_last_if_not`
  * `ranges::iota`, `ranges::shift_left`, and `ranges::shift_right`
  * `ranges::fold_left` etc.
* Rectifying constant iterators, sentinels, and ranges (`ranges::cbegin` and similar utilities)
* Making multi-param constructors of some views explicit
* Ranges iterators as inputs to non-ranges algorithms
* Relaxing range adaptors to allow for move-only types

### Containers

* `std::mdspan`: a non-owning multidimensional array reference
* Constructibility and assignability of containers from other compatible ranges
* `std::flat_set`, `std::flat_multiset`, `std::flat_map`, `std::flat_multimap`
* Allowing iterator pair construction in `std::stack` and `std::queue`
* Heterogeneous erasure overloads for associative containers
* Non-deduction context for allocators in container deduction guides
* Requiring `std::span` and `std::basic_string_view` to be trivially copyable

### Compile-time Support

* `constexpr` support for:
  * `std::bitset`
  * `std::unique_ptr`
  * `std::type_info::operator==`
  * Some `<cmath>` functions
  * Integral overloads of `std::to_chars` and `std::from_chars`
* Metaprogramming utilities:
  * Adding move-only types support for comparison concepts
  * Type traits: `std::is_scoped_enum`, `std::is_implicit_lifetime`, `std::reference_constructs_from_temporary`, and `std::reference_converts_from_temporary`

### Memory Management

* `std::out_ptr` and `std::inout_ptr`: smart pointer adaptors for C interoperability
* `std::allocate_at_least` and `std::allocator::allocate_at_least`
* `std::start_lifetime_as`: an explicit lifetime management function for implicit-lifetime types
* Disallowing user specialization of `std::allocator_traits`

### String and Text Processing

* New member functions and changes in string types:
  * `std::basic_string::contains` and `std::basic_string_view::contains`
  * Disabling construction from `nullptr` for `std::basic_string` and `std::basic_string_view`
  * Explicit range constructor for `std::basic_string_view`
  * `std::basic_string::resize_and_overwrite`
  * Rvalue reference overload of `std::basic_string::substr` for efficient slicing
* Formatting ranges, tuples, escaped presentation of characters and strings, `std::thread::id`, and stacktraces

### I/O and Print

* Formatted output functions `std::print` and `std::println` provided in header `<print>`
* `spanstream` library (`std::span`-based string stream) provided in header `<spanstream>`
* Support exclusive mode in `std::fstreams`
* Support of printing `volatile T*`: `std::basic_ostream::operator<<(const volatile void*)`

## Obsolete Features

### Removed Features

* Garbage collection support and reachability-based leak detection
* Mixed wide string literals concatenation support
* Non-encodable wide character literals and multicharacter wide character literals

### Deprecated Features

* `std::aligned_storage` and `std::aligned_union`
* `std::numeric_limits::has_denorm`

### Reverted Deprecations

* The comma operator in subscript expressions (semantics changed to support overloadable multidimensional subscript `operator[]`)
* Some C compatibility headers

---

## Compiler Support

### C++23 Core Language Features

| Feature | GCC | Clang | MSVC | Apple Clang | EDG eccp | Intel C++ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Literal suffix for (signed) size_t | 11 | 13 | 19.43 | 13.1.6 | 6.5 | 2022.2 |
| Make () more optional for lambdas | 11 | 13 | 19.44 | 13.1.6 | 6.3 | 2022.2 |
| `if consteval` | 12 | 14 | 19.44 | 14.0.0 | 6.3 | 2022.2 |
| Removing Garbage Collection Support | 12 | N/A | 19.30 | N/A | N/A | N/A |
| Narrowing contextual conversions in static_assert and constexpr if | 9 | 13 | 14 | 19.44 | 14.0.0 | 2022.2 |
| Trimming whitespaces before line splicing | Yes | Yes | 19.50 | Yes | 6.7 | 2022.2 |
| Make declaration order layout mandated | Yes | Yes | 19.30 | Yes | 6.8 | 2022.2 |
| Removing mixed wide string literal concatenation | Yes | Yes | 19.44 | Yes | Yes | Yes |
| Explicit object member functions (deducing this) | 14 | 18 | 19.32 | 19.43 | 6.3 | 22.5 |
| `auto(x)` and `auto{x}` | 12 | 15 | 19.50 | 14.0.3 | 6.4 | 2022.2 |
| `#elifdef` and `#elifndef` | 12 | 13 | 19.40 | 13.1.6 | 6.5 | 2022.2 |
| Non-literal variables in constexpr functions | 12 | 15 | 19.43 | 14.0.3 | 6.3 | 2022.2 |
| Consistent character literal encoding | Yes | Yes | 19.30 | Yes | Yes | 2022.2 |
| Character sets and encodings | 10 | Yes | 19.51 | Yes | Yes | 2022.2 |
| Extend init-statement to allow alias-declaration | 12 | 14 | 19.50 | 14.0.0 | 6.8 | 2022.2 |
| Multidimensional subscript operator | 12 | 15 | 19.42 | 14.0.3 | 6.8 | 2022.2 |
| Attributes on lambdas | 9 | 13 | 19.44 | 13.1.6 | 6.6 | 2022.2 |
| `#warning` | Yes | Yes | 19.50 | 15.0.0 | 6.5 | 2023.2 |
| Remove non-encodable wide character literals | 13 | 14 | 19.51 | 15.0.0 | 6.7 | 2023.2 |
| Labels at the end of compound statements | 13 | 16 | 19.51 | 16.0.0 | 6.5 | 2023.2 |
| Delimited escape sequences | 13 | 15 | 19.50 | 15.0.0 | 6.7 | 2023.2 |
| Named universal character escapes | 13 | 15 | 19.51 | 15.0.0 | 6.7 | 2023.2 |
| Relaxing some constexpr restrictions | 13 | 17 | 19.51 | 6.9 | 2024.0 | - |
| Simpler implicit move | 13 | 13 | 19.50 | 6.7 | 2022.2 | - |
| `static operator()` | 13 | 16 | 19.44 | 16.0.0 | 6.7 | 2023.2 |
| `static operator[]` | 13 | 16 | 19.44 | 16.0.0 | 6.7 | 2023.2 |
| Attribute `[[assume]]` | 13 | 19 | 19.51 | 6.8 | - | - |
| Support for UTF-8 as a portable source file encoding | 13 | 15 | 19.0 | 15.0.0 | N/A | 2023.2 |

### C++23 Library Features

| Feature | GCC libstdc++ | Clang libc++ | MSVC STL | Apple Clang |
| :--- | :--- | :--- | :--- | :--- |
| Stacktrace library | 12 | 14 | 19.34 | - |
| `<stdatomic.h>` | 12 | 15 | 19.31 | 14.0.3 |
| `std::is_scoped_enum` | 11 | 12 | 19.30 | 13.0.0 |
| `std::basic_string::contains()` | 11 | 12 | 19.30 | 13.0.0 |
| `std::to_underlying` | 11 | 13 | 19.30 | 13.1.6 |
| `<spanstream>` | 12 | 19 | 19.31 | - |
| `std::out_ptr()`, `std::inout_ptr()` | 14 | 19 | 19.30 | - |
| `ranges::starts_with()` and `ranges::ends_with()` | 16 | 18 | 19.31 | 16.0.0 |
| `std::invoke_r()` | 12 | 17 | 19.31 | 15.0.0 |
| `views::zip`, `views::adjacent` | 13 | 22 | 19.33 | 14.0.3 |
| `std::byteswap()` | 12 | 14 | 19.31 | 14.0.3 |
| Monadic operations for `std::optional` | 12 | 14 | 19.32 | 14.0.3 |
| `std::move_only_function` | 12 | 19 | 19.32 | - |
| `<expected>` | 12 | 16 | 19.33 | 15.0.0 |
| `std::unreachable()` | 12 | 15 | 19.32 | 14.0.3 |
| `std::mdspan` | 16 | 18 | 19.39 | 15.0.0 |
| `<flat_map>` | 15 | 20 | 19.51 | - |
| `<flat_set>` | 15 | 21 | 19.51 | - |
| Formatted output library `<print>` | 14 | 18 | 19.37 | 15.0.0 |
| `std::generator` | 14 | 19 | 19.43 | - |