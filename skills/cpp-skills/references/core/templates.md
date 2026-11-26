# Templates & Concepts Reference

## Overview

Guidelines for writing expressive, type-safe, and maintainable generic C++23 code using function and class templates, variadic parameter packs, compile-time programming (`constexpr` / `consteval`), and C++20/23 `concepts` for compile-time interface constraints.

---

## Template Design & Instantiation Cost

- **Parameterize Once**: Express generic algorithms once over explicit requirements rather than maintaining hand-written specializations per type, size, or architecture that inevitably drift.
- **Function vs. Class Templates**: Prefer a function template (or C++20 abbreviated function template with constrained `auto` parameters) over a class template when there is no state to hold. Remember that function templates cannot be addressed or stored directly—only their concrete instantiations exist.
- **Injected Class Name**: Inside a class template definition, refer to the current instantiation using the bare class name without repeating template arguments.
- **Transparent Dataflow & Small Interfaces**: Keep template interfaces minimal and avoid clever metaprogramming tricks that obscure which code path runs for a given instantiation.
- **Header Organization**: Keep template definitions visible in headers (or `.tpp`/`.inl` files included at the bottom of headers) so the compiler can instantiate them across translation units.
- **Controlling Binary Size & Build Time**: Every distinct template instantiation generates separate machine code and instruction-cache footprint. Factor type-independent logic into non-template helpers or bases, use `extern template` declarations to suppress redundant instantiations across translation units, and watch out for `static` locals inside templates (each instantiation gets its own separate static object).

---

## Variadic Templates & Fold Expressions

- **Parameter Packs (`typename... Args`)**: Use variadic templates to accept arbitrary numbers of type-safe arguments, forwarding them cleanly with `std::forward<Args>(args)...`.
- **Fold Expressions & `index_sequence`**: Prefer C++17 unary and binary fold expressions (`(args + ...)`, `(process(args), ...)`) and `std::index_sequence` over recursive template instantiation to keep compile times fast and code readable.
- **Pack Inspection (`std::tuple`)**: Use `std::forward_as_tuple`, `std::apply`, or `sizeof...(Args)` to inspect and manipulate parameter packs cleanly at compile time.

---

## Concepts & Compile-Time Constraints (C++20/23)

- **Constrain Every Template**: Always constrain template parameters at the entry point so invalid types fail immediately with a single clear diagnostic rather than deep inside nested instantiations. Use `concepts` in C++20+, `if constexpr` with type traits and `static_assert` in C++17, or `std::enable_if` on older standards.
- **Named Concepts Over Ad-Hoc Clauses**: Define reusable, semantic concepts (`template <typename T> concept Serializable = requires(T a) { ... };`) rather than repeating inline `requires` clauses at every declaration, and prefer concepts over tag types or integral flags.
- **Standard Library Concepts**: Leverage built-in concepts from `<concepts>` and `<ranges>` (e.g., `std::integral`, `std::floating_point`, `std::invocable`, `std::ranges::range`) before defining custom ones.
- **Constrain the General Template**: Constrain general forwarding-reference templates rather than adding competing overloads, since an unconstrained `T&&` overload matches any non-exact argument type.
- **Syntax vs. Semantics**: Remember that `requires` expressions verify syntactic validity, not runtime axioms (for instance, `std::totally_ordered` cannot enforce mathematical transitivity at compile time). Inside a `requires` expression, wrap compound expressions in braces before `-> Type`, and introduce nested predicates with their own `requires` keyword.
- **Subsumption & Overloading**: Order constrained template overloads from most specific to least specific concept so overload resolution selects the tighter match unambiguously via concept subsumption.

---

## Compile-Time Branching & Evaluation

- **`if constexpr` (C++17)**: Use `if constexpr` as the default mechanism for compile-time branching inside templates, replacing tag dispatch and most SFINAE chains. Note that branches are only discarded inside templates—in non-template functions, both branches must still compile.
- **`constexpr`, `consteval` & `constinit` (C++20/23)**:
  - `constexpr` indicates a function or variable *may* be evaluated at compile time.
  - `consteval` (C++20) enforces compile-time evaluation, preventing silent runtime fallbacks.
  - `constinit` guarantees static compile-time initialization while leaving the variable mutable.
  - `if consteval` (C++23) cleanly selects a compile-time implementation path (replacing `std::is_constant_evaluated()`, which must never be placed inside an `if constexpr` condition where it always evaluates to `true`).
- **Precomputing Compile-Time Data**: Move known-input computations—lookup tables, format string parsing, literal hashes, bitmasks, or dispatch tables—to compile time using `constexpr` arrays or `consteval` generators, and use compile-time constants directly without re-wrapping them at runtime.
- **Type Traits & Non-Type Template Parameters**: Query type traits with `_v` and `_t` aliases (preferring concepts when expressing constraints), and favor C++20 `auto` non-type template parameters or templated lambdas (`[]<typename T>(T x) { ... }`) over `std::integral_constant` tag objects.

---

## Type Deduction, Forwarding & Customization

- **Forwarding References (`T&&`)**: `T&&` is a forwarding reference only when `T` is deduced in that exact declaration; inside a class template member function where `T` is already a class template parameter, `T&&` is a plain rvalue reference.
- **Single Forwarding & Generic Lambdas**: Forward parameters with `std::forward<T>(x)` (or `std::forward<decltype(x)>(x)` for `auto` parameters in generic lambdas) at most once at the point of final use.
- **CTAD & Deduction Guides**: Leverage Class Template Argument Deduction (CTAD) alongside explicit deduction guides for custom project templates, keeping in mind that deduction ignores implicit conversions and fails on braced initializer lists unless explicitly supported.
- **Return Type Deduction**: Prefer `auto` over assuming a template parameter `T` as the return type when expressions may yield a distinct type (e.g., concatenating two `std::string_view` instances yields `std::string`).
- **Overloading Over Function Specialization**: Prefer overloading function templates (or using trait classes, customization point objects, or concept-constrained ADL overloads) rather than specializing function templates, since function template specializations do not participate intuitively in overload resolution and partial function specialization is illegal.
- **Standard Library Extension Rules**: Only specialize permitted standard customization points (such as `std::hash` or `std::formatter`) for user-defined types; never add declarations, specializations, or forward declarations inside `namespace std` otherwise.
- **Two-Phase Name Lookup**: Prefix dependent nested types with `typename` and dependent member templates with `template` inside template definitions.

---

## Compile-Time Diagnostics

- **Actionable `static_assert` Messages**: Place a `static_assert` with a clear explanation at the top of a template when a requirement cannot be expressed cleanly as a concept, and never put `static_assert` inside a function body that a `requires` expression must probe.
- **Dependent `static_assert` Conditions (C++17)**: Ensure a `static_assert` inside a discarded `if constexpr` branch depends on a template parameter (for example via a `dependent_false<T>` helper) so it fires only when that branch is instantiated rather than unconditionally at parse time.
- **Isolating Instantiation Errors**: When diagnosing deep template error chains, explicitly instantiate the failing template with the problematic type in a minimal translation unit.
