# C++20

## Overview

C++20 is a major version after C++17, introducing revolutionary features such as concepts, modules, coroutines, and ranges, alongside numerous other language and library improvements.

## New Language Features

* Feature test macros
* Three-way comparison operator `<=>` and `operator==() = default`
* Designated initializers
* Init-statements and initializers in range-for loops
* `char8_t` support
* New attributes: `[[no_unique_address]]`, `[[likely]]`, `[[unlikely]]`
* Pack-expansions in lambda init-captures
* Removed requirement to use `typename` to disambiguate types in many contexts
* `consteval` and `constinit` specifiers
* Further relaxed `constexpr` rules
* Signed integers standardized as two's complement
* Bitwise shift operators unified behavior
* Aggregate initialization using parentheses
* Coroutines
* Modules
* Constraints and concepts (`concept`, `requires`)
* Abbreviated function templates (auto parameters)
* Array new can deduce array size

## New Library Features

### New Headers

* `<bit>`
* `<compare>`
* `<concepts>`
* `<coroutine>`
* `<format>`
* `<numbers>`
* `<ranges>`
* `<source_location>`
* `<span>`
* `<syncstream>`
* `<version>`
* Thread support: `<barrier>`, `<latch>`, `<semaphore>`, `<stop_token>`

### Key Utilities & Algorithms

* Formatting library (`std::format`)
* Concepts library (`<concepts>`)
* Calendar and Time zone library in `<chrono>`
* `std::source_location`
* `std::span` (non-owning contiguous sequence view)
* `std::endian` (big / little / native)
* Integral power-of-2 operations and `std::bit_cast` in `<bit>`
* Array support for `std::make_shared`
* `std::remove_cvref` and `std::to_address`
* Floating-point atomics and atomic `std::shared_ptr` / `std::weak_ptr`
* Thread-coordination classes: `std::barrier`, `std::latch`, `std::counting_semaphore`
* `std::jthread` and cancellation classes (`std::stop_token`, `std::stop_source`, `std::stop_callback`)
* `std::basic_osyncstream`
* `std::basic_string` and other `char8_t` uses
* `constexpr` expansion for `<algorithm>`, `<utility>`, and `<complex>`
* `string::starts_with` / `ends_with` and `string_view::starts_with` / `ends_with`
* `std::assume_aligned`
* `std::bind_front`
* `std::make_shared_for_overwrite` / `std::make_unique_for_overwrite`
* Heterogeneous lookup in unordered associative containers
* `std::pmr::polymorphic_allocator` enhancements
* `std::execution::unseq`
* `std::midpoint` and `std::lerp`
* `std::ssize`
* Ranges library and input range adaptors (`std::ranges`)
* Uniform container erasure (`std::erase`, `std::erase_if`)
* Mathematical constants in `<numbers>`

## Compiler Support

### C++20 Core Language Features

| Feature | GCC | Clang | MSVC | Apple Clang | EDG eccp | Intel C++ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Allow Lambda capture `[=, this]` | 8 | 6 | 19.22 | 10.0.0 | 5.1 | 2021.1 |
| Designated initializers | 8 | 3.0 | 10 | 19.21 | 12.0.0 | 5.1 |
| Template-parameter-list for generic lambdas | 8 | 9 | 19.22 | 11.0.0 | 5.1 | 2021.1 |
| Concepts | 10 | 10 | 19.23 | 12.0.0 | 6.1 | 2023.1 |
| Three-way comparison operator (`<=>`) | 10 | 8 | 19.20 | 12.0.0 | 5.1 | 2021.1 |
| Init-statements for range-based for | 9 | 8 | 19.25 | 11.0.0 | 6.0 | 2021.7 |
| Attributes `[[likely]]` and `[[unlikely]]` | 9 | 12 | 19.26 | 13.0.0 | 5.1 | 2021.7 |
| Attribute `[[no_unique_address]]` | 9 | 9 | 19.28 | 11.0.3 | 5.1 | 2021.1 |
| Coroutines | 10 | 17 | 19.0 | 10.0.1 | 5.1 | 2021.1 |
| Modules | 11 | 8 | 19.0 | 10.0.1 | \- | 2023.1 |
| `explicit(bool)` | 9 | 9 | 19.24 | 11.0.3 | 5.1 | 2021.1 |
| `char8_t` | 9 | 7 | 19.22 | 10.0.0 | 5.1 | 2021.1 |
| Immediate functions (`consteval`) | 11 | 11 | 19.28 | 11.0.3 | 5.1 | 2021.1 |
| `constinit` | 10 | 10 | 19.29 | 12.0.0 | 6.1 | 2021.7 |
| `using enum` | 11 | 13 | 19.24 | 13.1.6 | 6.3 | 2023.1 |

### C++20 Library Features

| Feature | GCC libstdc++ | Clang libc++ | MSVC STL | Apple Clang |
| :--- | :--- | :--- | :--- | :--- |
| `std::endian` | 8 | 7 | 19.22 | 10.0.0 |
| `std::span` | 10 | 7 | 19.26 | 10.0.0 |
| `std::bit_cast` | 11 | 14 | 19.27 | 14.0.3 |
| Concepts library | 10 | 13 | 19.23 | 13.1.6 |
| Ranges library (`std::ranges`) | 10 | 13 | 19.29 | 14.0.3 |
| Text formatting (`std::format`) | 10 | 13 | 19.29 | 15.0.0 |
| `std::jthread` and `std::stop_token` | 10 | 10 | 19.28 | \- |
| Atomic waiting, semaphores, latch, barrier | 11 | 11 | 19.28 | 13.1.6 |
| Mathematical constants (`<numbers>`) | 10 | 11 | 19.25 | 12.0.5 |