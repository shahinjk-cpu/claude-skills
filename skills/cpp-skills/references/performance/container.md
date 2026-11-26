# Containers and Memory Safety Reference

## Overview
Guidelines for safe buffer management, standard sequence and associative containers, string handling, and modern C++23 container extensions designed for performance and cache-friendliness.

---

## Container Selection by Workload

| Workload / Need | Container Choice |
|---|---|
| Default sequential storage | `std::vector` |
| Compile-time fixed capacity | `std::array` |
| Front/back growth with stable element addresses | `std::deque` |
| Element and iterator stability across mutations, or node splicing | `std::list`, `std::forward_list` |
| Sorted keys, ordered traversal, or range lookups | `std::map`, `std::set` |
| Average constant-time lookup without ordering | `std::unordered_map`, `std::unordered_set` |
| Read-heavy lookups, rare insertions, cache locality | Sorted `std::vector`, or `std::flat_map` / `std::flat_set` (C++23) |
| Small, bounded capacity on hot paths | Fixed `std::array` with an explicit count, or a small-buffer container |

---

## Buffer and Memory Safety
- **Fixed-Size Arrays**: Use `std::array` instead of raw C-style arrays for compile-time size safety and bounds management.
- **Dynamic Sequences**: Use `std::vector` as the default dynamic container; prefer `.at()` when out-of-range indices are possible and reserve `operator[]` for proven in-range hot paths.
- **`std::vector<bool>` Caveat**: Avoid `std::vector<bool>` when standard element references (`bool&`) or direct byte semantics are required, as it packs bits via proxy references; prefer `std::vector<char>` or `std::bitset`.
- **Contiguous Views**: Use `std::span` for safe, non-owning views over contiguous sequences of objects.
- **Multidimensional Views (C++23)**: Use `std::mdspan` for non-owning multidimensional array views, ideal for matrix and tensor computations without heap allocation overhead.

---

## Strings, Formatting & Number Conversions
- **Ownership vs. Observation**: `std::string` owns its characters, whereas `std::string_view` is a non-owning view and is **not** guaranteed to be null-terminated.
- **Parameter Passing**: Accept `std::string_view` when a function only reads text, and take `std::string` by value when the function needs to store or sink an owned copy.
- **Loop Construction**: Pre-allocate with `reserve()` and append in loops rather than concatenating with `+`, avoiding repeated reallocations and temporary string copies.
- **Formatting & Output**: Prefer `std::format` (C++20) and `std::print` (C++23) over type-unsafe `printf` or heavy stream chains; fall back to `fmt` (if already in the project) or iostreams on older standards.
- **Custom Formatters (C++20)**: Specialize `std::formatter` for custom project types by implementing `parse()` (throwing `std::format_error` on invalid format specifiers) and `format()`.
- **Locale-Free Conversions (`<charconv>`)**: Prefer `std::from_chars` and `std::to_chars` (C++17) for fast, allocation-free, locale-independent conversions over `stoi`, `atoi`, or `std::stringstream`. For exact floating-point round-trips, format with `max_digits10` precision, parse with `from_chars`, and verify that the returned pointer consumed the full token.
- **Line Breaks & Locales**: Emit `'\n'` instead of `std::endl` to avoid unnecessary buffer flushes, and explicitly specify or avoid locale-dependent operations during data processing.

---

## Standard Sequence Containers
- **`std::vector`**: Default choice for dynamic arrays with contiguous memory layout and hardware prefetch locality, often outperforming node-based containers even on iteration-heavy workloads.
- **`std::deque`**: Double-ended queue providing amortized constant-time insertions and deletions at both ends plus random access, at the cost of an extra pointer indirection per lookup.
- **`std::list` / `std::forward_list`**: Doubly and singly linked lists for constant-time insertions/removals anywhere when pointer/iterator stability or node splicing is strictly required; profile first due to per-node heap allocations.

---

## Associative & Unordered Containers
- **Ordered (`std::map`, `std::set`)**: Balanced binary search trees maintaining sorted element order with logarithmic lookup times and per-node allocations.
- **Unordered (`std::unordered_map`, `std::unordered_set`)**: Hash-based tables providing average constant-time complexity for insertions, deletions, and lookups; benchmark default hashers on hot paths.
- **Deterministic Output**: Never rely on the iteration order of unordered containers when output must be deterministic—sort with a strict total order across all relevant fields and test with shuffled inputs to catch hidden order dependencies.

---

## Flat Containers (C++23)
- **`std::flat_map` & `std::flat_set`**: Container adaptors providing associative container interfaces backed by sorted contiguous containers (like `std::vector`), ensuring superior cache locality and memory density at the cost of linear insertion/deletion performance.

---

## Allocation, Lookup & Mutation Patterns
- **Pre-allocation**: Call `reserve()` ahead of known insertion counts on `std::vector` and `std::unordered_*` containers to prevent repeated reallocations and pointer/iterator invalidation.
- **Single-Lookup Insertion**: Prefer `emplace`, `try_emplace`, and `insert_or_assign` over separate find-then-insert double lookups.
- **Unordered Removal**: When element order does not matter in a contiguous sequence, swap the target element with `back()` and call `pop_back()` for constant-time erasure without shifting elements.
- **Extrema & Partitioning**: Use a heap/priority queue (`std::priority_queue` or `std::make_heap`) over a contiguous container when only the extremum is needed, or `std::nth_element` when partial partitioning around a rank suffices instead of a full sort.
