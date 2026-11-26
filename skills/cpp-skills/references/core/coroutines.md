# C++20 Coroutines Reference

A coroutine is a function that can suspend execution to be resumed later. Coroutines are stackless: they suspend execution by returning to the caller, and data required to resume execution is stored separately from the stack.

---

## 1. Defining Keywords

A function is a coroutine if its definition contains any of the following:
* **`co_await`**: Suspend execution until resumed.
* **`co_yield`**: Suspend execution and return a value (e.g., generators).
* **`co_return`**: Complete execution and return a value or result to the promise.

### Restrictions
* Coroutines cannot use plain `return` statements or placeholder return types (`auto` or concepts).
* `constexpr` functions, `consteval` functions, constructors, destructors, vararg functions, and `main()` cannot be coroutines.

---

## 2. Architecture: State, Promise, and Handle

Each coroutine is associated with three main entities:
1. **Promise Object**: Manipulated from *inside* the coroutine to submit results or exceptions.
2. **Coroutine Handle**: A non-owning handle (`std::coroutine_handle<Promise>`) manipulated from *outside* to resume or destroy the coroutine state.
3. **Coroutine State**: Internal, dynamically-allocated storage holding the promise, parameter copies, suspension point representation, and local variables whose lifetime spans suspension points.

---

## 3. Core Mechanics & Lifecycle

### Execution Flow
1. Allocates coroutine state via `operator new`.
2. Copies function parameters into the coroutine state (by-value parameters are copied/moved; by-reference parameters remain references—watch out for dangling references!).
3. Constructs the promise object.
4. Calls `promise.get_return_object()` and stores the result locally.
5. Calls `promise.initial_suspend()` and `co_awaits` its result (`std::suspend_always` for lazy start, `std::suspend_never` for eager start).
6. Executes the coroutine body.

### Suspension & Resumption
* Reaching `co_await` or `co_yield` suspends the coroutine and returns control to the caller/resumer.
* Resuming is performed via `handle.resume()` or the function call operator `handle()`.

### Completion & Destruction
* Reaching `co_return` or falling off the end passes the result to the promise, destroys automatic variables in reverse order, calls `promise.final_suspend()`, and cleans up state memory.

---

## 4. `co_await` Mechanics

The unary operator `co_await expr` operates as follows:
1. **Conversion**: `expr` is converted to an awaitable (via `promise.await_transform(expr)` if available).
2. **Awaiter Obtention**: Via `operator co_await` member or non-member overloads.
3. **`await_ready()`**: If `true`, the coroutine proceeds without suspension. If `false`, execution suspends.
4. **`await_suspend(handle)`**: Schedules the coroutine resumption or destruction.
5. **`await_resume()`**: Executes upon resumption and yields the result of the `co_await` expression.

---

## 5. `co_yield` & Generators

`co_yield expr` is syntactic sugar for:
```cpp
co_await promise.yield_value(expr)
```
Used primarily for lazy sequences and generator patterns (standardized via `std::generator` in C++23).

---

## 6. Performance & Best Practices

1. **Avoid Dynamic Allocation Overhead**: The compiler can optimize out coroutine state dynamic allocation if its lifetime is strictly nested within the caller and its size is known at compile time (embedded in the caller's stack frame).
2. **Lifetime Safety with Parameters**: Pass parameters by value if the coroutine outlives the immediate caller scope, preventing dangling reference issues.
3. **Use Standard Types**: Prefer standard library types like `std::generator` (C++23) over custom implementations for sequence generation.