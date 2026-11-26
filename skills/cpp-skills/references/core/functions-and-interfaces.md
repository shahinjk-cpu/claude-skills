# Functions, Interfaces, Overloads, Operators & Lambdas

## Overview
Guidelines for designing clean, type-safe, and zero-overhead C++ functions, public APIs, overload sets, operators, and lambdas/callables across modern C++ standards (C++11 to C++23).

## Parameter Passing
- **Choosing Parameter Forms**:
  - Pass small, cheap-to-copy inputs (built-ins, small trivially copyable types, `std::string_view`, `std::span`) by value.
  - Pass larger or non-trivial read-only inputs by `const T&` (avoiding `const T&` for types that fit comfortably in one or two registers).
  - Pass in-out parameters by non-const reference (`T&`) when mutation is part of the contract, keeping call-site intent clear.
  - Use rvalue references (`T&&`) with `std::move` in sink overloads, and forwarding references (`TP&&`) with `std::forward<TP>` only when preserving value category is required.
- **Ownership & Containers**:
  - Take `std::shared_ptr` by value only when sharing or transferring ownership; otherwise pass a reference to the underlying object.
  - Never transfer ownership via raw pointers or references—return `std::unique_ptr`.
  - Avoid passing arrays as a single pointer; prefer `std::span` or container references.
- **Optional & Default Parameters**:
  - Prefer `std::optional<T>` or explicit overloads over sentinel/magic values for optional arguments.
  - Avoid default arguments when behavior differs across variants or when virtual overriding is involved; prefer explicit overloads.

## Return Values
- **Return Instead of Out-Parameters**: Prefer returning values (or a small named struct for multiple values, or `std::optional` / `std::expected` for fallible operations) over output parameters and `bool` status flags.
- **`[[nodiscard]]` & Lifetime Safety**: Annotate pure queries, factories, error results, and `try_*` helpers with `[[nodiscard]]`. Never return references or pointers to local variables, views over temporaries, or `const T&` bound to a parameter that may dangle at the end of a full expression.
- **ABI & Accessors**: Return `T*` only when signaling a nullable position or optional non-owning reference with documented nullability. Keep in mind that non-trivial return types (such as `std::unique_ptr`) often involve hidden output parameters and destructor bookkeeping at call sites.

## `noexcept`, `explicit`, `const` & Ref-Qualifiers
- **`noexcept` Discipline**: Mark move constructors, move assignment operators, `swap`, and destructors `noexcept` so containers can select safe move paths; apply `noexcept` elsewhere only when the non-throwing guarantee is genuine and permanent, as throwing from a `noexcept` function calls `std::terminate`.
- **`const` & Ref-Qualifiers**: Mark member functions `const` when they do not modify observable logical state (while treating thread safety separately). Use ref-qualified members (such as `&&`) when rvalue objects can transfer internal state without copying.

## Overload Resolution, ADL & Name Lookup
- **Coherent Overload Sets**: Keep overloads within a set performing the same logical operation on different types; use distinct function names when semantics differ. Delete `const T&&` overloads when rejecting temporaries is desired.
- **ADL & Hidden Friends**: Rely on Argument-Dependent Lookup (ADL) and `using std::swap;` before unqualified `swap` calls. Define free operators or type-specific helpers as hidden friends inside the class to keep name lookup fast and scoped.
- **Inheritance, Templates & Constraints**: Use `using Base::f;` when derived classes introduce overloads of the same name to avoid hiding base overloads. Avoid mixing default arguments or ordinary overloads with function templates in ways that cause surprising deduction/overload behavior, constrain or guard forwarding references carefully, and prefer `= delete` when surfacing an invalid/dangling call site is clearer than silently picking another overload.

## Value Categories & Move Semantics
- **Lvalues, Prvalues & Xvalues**: Distinguish lvalues (have identity), prvalues (pure values), and xvalues (expiring lvalues). Remember that a named `T&&` parameter is an lvalue inside the function body.
- **`std::move` & `std::forward`**: Use `std::move` on rvalue references or local/sink objects being moved out, and `std::forward` strictly on deduced forwarding parameters. Do not `std::move` a local or by-value parameter in a `return` statement when it inhibits copy elision or duplicates implicit moves; only move explicitly when returning a member or subobject.
- **Post-Move State & `const`**: Do not read from a moved-from object except to assign or destroy it, and note that `std::move` on a `const` object results in a copy rather than a move.

## Operators
- **Conventional & Symmetric Semantics**: Overload operators only with conventional meaning and complete sets (e.g., `==` with `!=` pre-C++20, `+` built on `+=`, or `operator==` and `operator<=>` in C++20—writing custom comparisons when member-wise lexicographical order does not match domain order).
- **Binary, Stream & Restricted Operators**: Implement binary arithmetic and stream operators (`operator<<` / `operator>>`) as non-members (hidden friends when appropriate), compound assignments as members, and never overload `&&`, `||`, or `,`. Document and check preconditions (such as bounds/validity on `operator[]` or `operator*`) in debug builds.

## Lambdas & Callables

### Syntax & Capture Modes
```cpp
[capture_clause](`parameters`) specifiers -> return_type {
    // Function body
};
```
