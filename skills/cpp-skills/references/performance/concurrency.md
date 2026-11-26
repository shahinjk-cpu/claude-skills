# Multithreading and Concurrency Reference

## Overview
Guidelines for safe, modern C++ concurrent and parallel programming, covering thread management, synchronization primitives, lock-free operations, parallel algorithms, coroutines, scaling, and testing.

## Design First
- **Prefer No Sharing**: Give each thread its own data and combine results afterward; partitioned computations avoid lock contention.
- **Prefer Immutable Shared Data**: Share `const` objects across threads without synchronization, provided no code casts away `const` or mutates shared state behind it.
- **Prefer Task-Based & Message-Passing Models**: Favor task abstractions (`std::async`, thread pools, parallel algorithms) and message passing over raw threads or shared mutable state. Raw threads are low-level primitives, and retrofitting mutexes onto a sequential design degrades both correctness and scaling.
- **Commit at Module Level**: Choose the concurrency model deliberately for the module rather than mixing ad-hoc synchronization patterns.

## The Hard Rules
- **Data Races Are Undefined Behavior**: Two concurrent accesses to the same memory location from different threads—with at least one write—are undefined behavior unless synchronized via a mutex, atomic operation, or ordering relation that makes them non-concurrent. "Benign" data races do not exist in the C++ memory model.
- **`volatile` Is Not Synchronization**: `volatile` does not provide atomicity or memory ordering; it targets memory-mapped hardware or special volatile accesses, not inter-thread synchronization.
- **`const` Does Not Imply Thread Safety**: `const` restricts observable logical state, not concurrent access. A `mutable` member is appropriate for synchronization primitives (such as a mutex); any other `mutable` member shared across threads warrants scrutiny.

## Thread Management and Tasks
- **`std::jthread` (C++20)**: Default choice for managed threads—joins automatically on destruction and supports cooperative cancellation via `std::stop_token`. Verify toolchain/runtime availability on older platforms (such as older Apple Clang/macOS SDKs).
- **`std::thread` (C++11)**: Requires explicit `join()` or `detach()` before destruction to avoid `std::terminate`. Detached threads must never reference objects whose lifetimes end before program termination.
- **Asynchronous Tasks & Futures**: Use `std::async` (passing `std::launch::async` explicitly when a dedicated thread is required, since the default policy may defer or run synchronously) and combine `std::future`, `std::promise`, and `std::packaged_task` to pass results or propagate exceptions across thread boundaries. Beware that `std::future` from `std::async` blocks in its destructor if not already ready.
- **Thread Pools & Urgency Partitioning**: Never spawn a thread per work item. Size worker pools to hardware and workload constraints, and separate latency-sensitive paths, long-running tasks, and general pool work.

## Synchronization and Coordination
- **Scoped RAII Locks**: Always lock through RAII guards (`std::scoped_lock` in C++17, `std::lock_guard`, `std::unique_lock`, `std::shared_lock`)—never manual `lock()`/`unlock()` pairs or unnamed temporary guards.
- **Deadlock Prevention & Critical Sections**: Acquire multiple locks via a single `std::scoped_lock` or in a documented global lock order. Keep critical sections short and free of blocking I/O, user callbacks, or heavy allocations. Group protected data with its mutex in a single struct to make ownership clear.
- **Choosing Lock Types**:
  - Use `std::mutex` for exclusive access and `std::shared_mutex` (C++17) only when reads clearly outnumber writes and critical sections amortize its higher overhead.
  - Avoid `std::recursive_mutex` when refactoring public vs. private helper methods resolves re-entrancy cleanly.
  - Reserve spinlocks for very brief, low-contention sections or dedicated-core handoffs; prefer sleeping synchronization otherwise.
- **Condition Variables, Latches, Barriers & Semaphores**:
  - Always wait on `std::condition_variable` with a predicate (`cv.wait(lock, pred)`) to handle spurious wakeups safely.
  - Prefer `std::latch`, `std::barrier`, and `std::counting_semaphore` / `std::binary_semaphore` (C++20) for structured phase coordination, signaling, and resource counting instead of custom condition-variable state machines.

## Lock-Free Programming and Atomics
- **`std::atomic<T>` & Memory Ordering**: Default to sequentially consistent operations (`memory_order_seq_cst`) when reasoning simplicity outweighs micro-optimizations. Use `memory_order_acquire` / `memory_order_release` only with a clear synchronization argument and paired operations, and reserve `memory_order_relaxed` for independent counters (such as metrics or reference counts), never for publishing non-atomic data. Avoid `memory_order_consume`.
- **Lock-Free Guarantees & `std::atomic_ref` (C++20)**: Gate hot-path atomics with `static_assert(std::atomic<T>::is_always_lock_free)` when lock-freedom is required, and use `std::atomic_ref` when applying atomic operations to objects that are not exclusively atomic. Do not read multiple atomics separately and assume an atomic snapshot, and never attach a lock to a lock-free structure (which breaks lock-free progress guarantees).
- **Read-Mostly Patterns**: For read-dominated shared structures, consider RCU-style / copy-on-write / Left-Right patterns with scoped read guards, deferring reclamation until a grace period passes and avoiding blocking or coroutine suspension points inside read-side critical sections.

## Parallel Algorithms and Scaling
- **Execution Policies (C++17)**: Use `std::execution::seq`, `unseq`, `par`, and `par_unseq` where appropriate, remembering that execution policies permit—rather than guarantee—parallelism and may require a linked parallel backend.
- **Element & Reduction Rules**: Ensure `par` operations are data-race-free and `par_unseq` bodies avoid locks, allocations, and non-vectorizable side effects. Element callbacks must not throw, and parallel reductions (`std::reduce`, `std::transform_reduce`) require associative, commutative operations—accepting floating-point rounding differences relative to sequential summation.
- **Outer-Loop Parallelism & Chunking**: Parallelize outer loops with contiguous chunks while keeping inner loops vectorizable; use index-based partitioning when per-item cost varies unevenly.
- **Benchmarking & Overhead Thresholds**: Measure sequential baselines and scaling curves. Parallelism has fixed startup cost and can lose below a workload size threshold; profile and measure before claiming speedups.

## True Sharing, False Sharing and Allocation
- **False Sharing**: Separate concurrently modified variables or atomics residing on different cache lines (using alignment/padding such as `std::hardware_destructive_interference_size` when supported) so cores do not bounce cache lines needlessly.
- **True Sharing & Hot-Loop Allocations**: Minimize shared mutable cache lines under heavy contention, and avoid heap allocations inside parallel loops (which serialize on the allocator)—hoist allocations or use per-thread buffers instead.

## Coroutines for Asynchrony
- **Cooperative Execution**: Coroutines (`co_await`) clarify asynchronous control flow, but require an explicit scheduler, event loop, or executor chosen by the project.
- **Lifetimes & Suspension Safety**: Watch for dangling references to temporaries across suspension points, account for coroutine frame allocation/scheduling overhead outside hot numeric loops, and avoid blocking calls or holding locks/thread-affine state across `co_await` suspension points.

## Concurrency Testing and Diagnostics
- **Sanitizers & Stress Runs**: Run ThreadSanitizer (TSan) in CI and execute concurrent tests repeatedly under load rather than relying on single green runs.
- **Deterministic Verification**: Favor deterministic coordination (controlled schedulers or explicit ordering hooks) over fragile timing sleeps when testing concurrency protocols.
