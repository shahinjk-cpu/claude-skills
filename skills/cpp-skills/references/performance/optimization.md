# Performance & Optimization Reference

## Overview
Guidelines for writing high-performance, low-latency modern C++ code, emphasizing compile-time computation, efficient memory movement, and zero-overhead abstractions.

## Compile-Time Computation
* **`constexpr` & `consteval`**: Maximize compile-time evaluation using `constexpr` and force immediate evaluation with `consteval` (C++20) for zero runtime overhead.
* **`constinit`**: Ensure static storage duration variables are initialized at compile time to avoid static initialization order fiascos and guarantee fast startup.
* **Immutability**: Use `const` liberally to enable compiler optimizations, improve code clarity, and prevent accidental modifications.

## Move Semantics & Forwarding
* **Move Semantics**: Prefer move over copy operations with `std::move` for types managing heavy resources (like `std::vector` or `std::string`) to transfer ownership without deep copies.
* **Perfect Forwarding**: Use `std::forward` within template functions (universal references `T&&`) to preserve the exact value category (lvalue/rvalue) of arguments.
* **Return Value Optimization (RVO)**: Rely on copy elision (RVO/NRVO) rather than manual `std::move` on local return values, allowing the compiler to construct objects directly in the caller's stack space.

## Memory Efficiency & Copy Reduction
* **Avoid Unnecessary Copies**: Pass large objects by `const&` (constant reference) instead of by value when read-only access is sufficient.
* **Cache Locality**: Design data structures with contiguous memory layouts (such as `std::vector` or C++23 `std::flat_map`) to minimize CPU cache misses compared to node-based pointer-heavy structures.
* **Small Buffer Optimization (SBO)**: Leverage types with built-in SBO (or custom allocators) to avoid heap allocations for small, frequent collections or strings.

## Inlining & Function Design
* **Inlining**: Use `inline` (or let the compiler decide implicitly for member functions defined inside classes) for small, frequently called utility functions to eliminate call-stack overhead.
* **Loop Optimizations**: Write loop-friendly code that vectorizes well, avoiding unnecessary branching or complex side-effects inside tight iteration blocks.

## Measurement & Profiling
* **Profile Before Optimizing**: Never guess performance bottlenecks; use professional profilers (e.g., perf, Valgrind/Callgrind, VTune) to identify actual hotspots before refactoring.
* **Benchmarking**: Use rigorous benchmarking frameworks (such as Google Benchmark) rather than ad-hoc timing loops to measure optimizations accurately under release configurations (`-O3`).