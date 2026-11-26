# Standard C++ Utilities Reference

Guidelines for using modern C++ vocabulary types, time and randomness facilities, bit manipulation, numeric helpers, filesystem paths, and function wrappers cleanly.

---

## Vocabulary & Composite Types

- **Optional, Variant & Any (C++17)**: Use `std::optional` for nullable/absent values ("maybe"), `std::variant` for closed sum types ("one of a closed set"), and `std::any` only when type erasure is strictly required ("anything, erased"). Prefer `std::optional` and `std::variant` first; `std::any` is rarely the right choice.
- **Tuples vs. Named Structs**: Use `std::tuple` and `std::pair` for lightweight internal plumbing returns, and define a named `struct` with meaningful field names for public or domain interfaces.
- **Contiguous & Multidimensional Views**: Use `std::span` (C++20) for non-owning contiguous ranges and `std::mdspan` (C++23) for non-owning multidimensional array views.

---

## Time, Randomness & Bit Operations

- **Time (`<chrono>`)**: Represent all durations and timestamps with `<chrono>` types rather than raw integers with implicit units so the type encodes the unit. Use `std::chrono::steady_clock` for elapsed time / stopwatches and `std::chrono::system_clock` for wall-clock / calendar time; avoid `std::chrono::high_resolution_clock` since it is an implementation-defined alias. Convert explicitly with `std::chrono::duration_cast` when truncation can occur, and call `.count()` only at I/O or serialization boundaries (C++11).
- **Randomness (`<random>`)**: Seed a named random engine explicitly instead of calling `std::rand()`. Treat distributions as stateful objects whose output is not guaranteed identical across standard library implementations, and use distributions such as `std::uniform_int_distribution` rather than modulo range-mapping (`%`), which introduces bias (C++11).
- **Bit Manipulation (`<bit>`, C++20)**: Use `std::bit_cast`, `std::popcount`, `std::countl_zero`, `std::has_single_bit`, and `std::bit_width` instead of non-standard compiler builtins hidden behind macros.

---

## Numeric, Filesystem & Utility Helpers

- **Numeric Helpers (`<numeric>`)**: Reach for standard numeric algorithms—`std::accumulate`, `std::reduce`, `std::inner_product`, `std::gcd`, `std::lcm`, `std::midpoint`, `std::iota`, and scan algorithms (`std::inclusive_scan`, `std::exclusive_scan`)—instead of hand-rolling them.
- **Filesystem (`<filesystem>`, C++17)**: Use `std::filesystem::path` and `<filesystem>` operations for path manipulation and directory inspection. Keep in mind that functions throw `std::filesystem::filesystem_error` by default unless you pass a `std::error_code` overload.
- **Move, Forward & Value Utilities**: Rely on standard library helpers—`std::move`, `std::forward`, `std::exchange`, `std::swap`, `std::as_const`, and `std::to_underlying`—rather than writing custom equivalents.

---

## Callables & Function Wrappers

- **Avoid `std::bind`**: Prefer lambdas for clarity, capture control, and inlining, or use `std::bind_front` (C++20) for simple leading-argument binding.
- **Type-Erased Callables (`std::function` & `std::move_only_function`)**: Because `std::function` can heap-allocate and inhibit inlining—and requires copyability—restrict it to interface boundaries, and use `std::move_only_function` (C++23) when storing move-only callables.
