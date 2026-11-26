# Algorithms, Ranges & Execution Policies Reference

## Overview

Guidelines for writing declarative, expressive, and high-performance data processing pipelines in modern C++23 using `<algorithm>`, `<ranges>`, lazy views (`std::views`), and parallel execution policies (`<execution>`).

## Core Algorithm Principles

- **Named Algorithms Over Loops**: Prefer standard library algorithms (`find`, `find_if`, `any_of`, `all_of`, `none_of`, `count_if`, `transform`, `copy_if`, `accumulate` / `reduce`, `sort`, `stable_sort`, `partial_sort`, `nth_element`, `lower_bound`, `equal_range`, `unique`, `rotate`, `partition`, `min_element`, `minmax_element`, `clamp`) over manual loops to make intent explicit and avoid off-by-one boundary bugs.
- **When a Loop Is Acceptable**: Keep raw loops only when trivial—at most two lines, a single condition, and no `continue`. Anything more complex belongs in a standard algorithm or a dedicated helper function.
- **Weakest Sufficient Algorithm**: Pick the least constrained algorithm that satisfies the requirement so intent stays clear (for example, `minmax_element` for both bounds in a single pass, or `nth_element` / `partial_sort` instead of full sorting).
- **Non-Mutating Callables & Short-Circuiting**: Do not mutate elements inside predicates or function objects passed to algorithms. Favor `all_of`, `any_of`, and `none_of` over `std::accumulate` with logical AND/OR when short-circuiting matters.
- **Iterator Discipline**: Never assume container iterators are raw pointers or support `<`; compare iterators with `!=` unless random access is guaranteed.
- **Destination Sizing & Overlapping Ranges**: Ensure output ranges are pre-sized or written through back/insert iterators (such as `std::back_inserter`) for algorithms like `std::transform`. Use `std::copy_backward` instead of `std::copy` when the destination overlaps the tail of the source range.
- **Erase-Remove & `std::erase`**: Remember that `remove` and `remove_if` shift elements and return the new logical end without shrinking the container. Prefer `std::erase` and `std::erase_if` (C++20), or the erase-remove idiom on older standards.

## Standard Algorithms & Range-Based Equivalents

- **Prefer `std::ranges` Algorithms**: Favor constrained range algorithms (`std::ranges::sort`, `std::ranges::find_if`, `std::ranges::transform`) over legacy iterator-pair algorithms (`begin()`, `end()`) to prevent mismatched iterator bugs and support projections directly. Keep compile times and unoptimized debug build speeds in mind when composing heavy range pipelines.
- **Projections**: Use projection callables in `std::ranges` algorithms to sort or search complex structs by a specific member without writing verbose custom comparators.
- **Numeric & Reduction Algorithms**: Prefer `std::reduce`, `std::transform_reduce`, and `std::inclusive_scan` over sequential `std::accumulate` when associative/commutative operations can benefit from parallelization or SIMD vectorization.
- **C++23 Range Algorithms**: Leverage modern additions such as `std::ranges::contains`, `std::ranges::fold_left`, `std::ranges::starts_with`, and `std::ranges::to` (for materializing views back into containers).

## Sorting & Partitioning Strategies

Choose the right sorting algorithm based on complexity, stability, and partial ordering needs:

- **Strict Weak Ordering**: Comparators passed to sorting algorithms must define a strict weak ordering; returning `true` for equal or equivalent elements is undefined behavior.
- **`std::ranges::sort`**: Default $O(N \log N)$ unstable sort (typically Introsort) for general-purpose fast ordering.
- **`std::ranges::stable_sort`**: Preserves the relative order of equivalent elements when secondary ordering matters. For multi-key sorting, `stable_sort` by the least-significant key first.
- **`std::ranges::partial_sort` & `std::ranges::nth_element`**: Use when only the top-$K$ elements or the median are required ($O(N \log K)$ and $O(N)$ average respectively), avoiding the cost of a full sort.
- **`std::ranges::partition`**: Group elements satisfying a predicate in $O(N)$ linear time without full sorting overhead.

## Lazy Evaluation with `std::views` (`<ranges>`)

- **Zero-Allocation Pipelines**: Chain view adaptors using the pipe operator (`|`) to compose transformations lazily without allocating intermediate temporary containers.
- **Common View Adaptors**:
  - Filtering & Transforming: `std::views::filter`, `std::views::transform`, `std::views::take`, `std::views::drop`.
  - C++23 Combinators: `std::views::zip`, `std::views::enumerate`, `std::views::chunk`, `std::views::slide`, `std::views::stride`, and `std::views::join_with`.
- **Materialization (`std::ranges::to`)**: Convert lazy view pipelines into concrete containers (`std::vector`, `std::flat_map`) cleanly in C++23 via `| std::ranges::to<std::vector>()`.
- **Lifetime Awareness**: Remember that views are lazy, lightweight, non-owning descriptors; never construct or return a view over a temporary or a container whose lifetime ends before evaluation.

## Parallel Execution Policies (`<execution>`)

Accelerate standard algorithms across multiple CPU cores and SIMD lanes by passing an execution policy, keeping in mind that some toolchains require linking a parallel backend and predicates must be data-race free:

- **`std::execution::seq`**: Strictly sequential execution on the calling thread.
- **`std::execution::par`**: Parallel execution across multiple worker threads (requires thread-safe, data-race-free element access).
- **`std::execution::par_unseq`**: Parallel and vectorized (SIMD) execution; operations must not acquire locks or rely on thread-local state to avoid deadlocks or undefined behavior.
- **`std::execution::unseq`**: Single-threaded SIMD vectorized execution (C++20).

## Practical Examples

### 1. Declarative Pipeline with `std::views` & `std::ranges::to` (C++23)

```cpp
#include <algorithm>
#include <ranges>
#include <string>
#include <vector>

struct User {
    std::string name;
    int score{0};
    bool is_active{false};
};

[[nodiscard]] std::vector<std::string> getTopActiveUserNames(const std::vector<User>& users) {
    auto pipeline = users
        | std::views::filter([](const User& user) { return user.is_active && user.score >= 50; })
        | std::views::transform(&User::name)
        | std::views::take(5);

    return pipeline | std::ranges::to<std::vector>();
}

### 2. Sorting with Projections & Partial Sort

```cpp
#include <algorithm>
#include <vector>

void sortUsersByScoreDescending(std::vector<User>& users) {
    // Sort using a projection on User::score without a custom lambda comparator
    std::ranges::sort(users, std::ranges::greater{}, &User::score);
}

void getTopThreeUsers(std::vector<User>& users) {
    if (users.size() > 3) {
        std::ranges::partial_sort(users, users.begin() + 3, std::ranges::greater{}, &User::score);
    }
}
```

### 3. Parallel Sort & Transform-Reduce (`std::execution`)

```cpp
#include <algorithm>
#include <execution>
#include <numeric>
#include <vector>

double computeParallelNormSquared(std::vector<double>& values) {
    // Parallel sorting across CPU cores
    std::sort(std::execution::par, values.begin(), values.end());

    // Parallel + SIMD vectorized reduction
    return std::transform_reduce(
        std::execution::par_unseq,
        values.cbegin(),
        values.cend(),
        0.0,
        std::plus<>{},
        [](double val) noexcept { return val * val; }
    );
}
```