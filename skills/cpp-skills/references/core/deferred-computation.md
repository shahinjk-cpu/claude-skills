# Deferred Computation, Views, Proxies & Generators Reference

## Overview
Guidelines for deferring work until the point of consumption in modern C++ (C++20/C++23), eliminating unnecessary intermediate allocations and unused computations via range views, proxy types, and coroutine generators.

## Core Concept & Mechanism Selection
Evaluate work at the point of use rather than at the point of expression when intermediate temporaries or unconsumed results are avoidable. Choose the lightest mechanism that fits the problem:

1. **Views (`std::ranges`)**: Non-owning lazy ranges that yield elements on demand across a single pass without intermediate containers.
2. **Proxy Objects**: Short-lived intermediate types that capture operands and defer computation or materialization until conversion or assignment.
3. **Generators & Coroutines**: Stateful producers that yield values one by one (`std::generator` in C++23 or equivalent coroutine types), avoiding eager container construction or manual state machines.

## Range Views (`std::views`)
- **Single-Pass Pipelines**: Compose adaptors (`filter`, `transform`, `take`, `drop`, `join`, `chunk`) to evaluate element by element without allocating intermediate collections.
- **Lifetime & Borrowed Safety**: Views do not own underlying storage. Never bind a view pipeline to a temporary container, retain a view past its source's lifetime or reallocation, or pass a non-borrowed temporary pipeline (such as `transform_view`) into parallel range algorithms where iterators can dangle.
- **Proxy References & `std::mdspan`**: Generic range algorithms must handle proxy references rather than assuming real lvalues or taking element addresses. When exposing column-major buffers such as Eigen through `std::mdspan` (C++23), specify `std::layout_left` explicitly instead of relying on `std::layout_right`.
- **Traversal Cost & Materialization**: Be aware that `filter_view::begin()` is not $O(1)$ and caches its initial position, making repeated re-traversal costly. Watch compile times and unoptimized debug performance on hot paths, and materialize explicitly at the end via `std::ranges::to` (C++23) or a target loop.
- **Custom Views & Adaptor Boundaries**: Implement custom views with `begin()`/`end()` and `std::ranges::view_interface` (C++20), specialize `std::iter_swap` for proxy iterators when mutating algorithms are used, and normalize incoming ranges at adaptor boundaries with `std::views::all`.

## Proxy Objects & Expression Templates
- **Deferred Evaluation Use Cases**:
  - Avoid expensive intermediate operations when a cheaper equivalent answers the query—for example, comparing squared norms before computing square roots.
  - Defer string assembly behind a lightweight proxy that answers `size()` or comparisons and writes once into the final buffer.
  - Use expression templates only when profiling proves temporary vectors/matrices are a bottleneck and a single fused pass on assignment is warranted; they add template complexity, slower builds, and noisier diagnostics compared to a straightforward fused loop.
- **Lifetime & Ergonomics Rules**: Design proxies to be converted or consumed immediately rather than stored via `auto x = a + b;` with dangling operand references. Provide transparent conversion to the target type where appropriate, constrain or document usage to discourage unsafe storage, and verify behavior with benchmarks.

## Generators & Coroutines
- **Lazy Sequence Producers**: Use generator coroutines (`std::generator` in C++23, or a project generator type) when state is natural to express sequentially—such as parsers, tree traversals, or record streams—without hand-writing iterator state machines.
- **Frame & Suspension Overhead**: Account for coroutine frame allocation (unless elided) and per-element suspend/resume overhead; this fits I/O and parsing well, but is generally unsuitable inside tight numeric inner loops.
- **Async Execution, Lifetimes & Exceptions**: Coroutines using `co_await` require a committed execution context (executor, event loop, or thread pool) chosen by the project. Never capture references to caller temporaries that outlive the expression, and define explicit exception handling in the promise type rather than swallowing errors inadvertently.

## When Eager Evaluation Is Preferable
Prefer eager evaluation or a plain loop when:
- Every element of the result is required regardless.
- The sequence is traversed multiple times, causing repeated recomputation.
- Elements are cheap and pipelines are short, where a plain loop is simpler and faster.
- Unoptimized debug build speed or code simplicity outweighs lazy pipeline overhead.

Compare lazy and eager implementations with measurements when performance is critical: lazy pipelines reduce allocations and wasted work, while eager code favors simplicity and multi-pass reads.
