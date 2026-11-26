# Classes, Hierarchies, Paradigms & Polymorphism

Load when designing a type, adding a virtual function, reviewing an inheritance tree, choosing between static and dynamic polymorphism, or inspecting memory layout and comparisons.

## Programming Paradigms in C++
- **Object-Oriented Programming (OOP)**: Encapsulate state and behavior cleanly using RAII, access specifiers, and controlled polymorphism:
  - **Polymorphic Base Destructors & `override`**: Always declare a `virtual` destructor (e.g., `virtual ~Base() = default;`) in polymorphic base classes so deleting through a base pointer does not cause undefined behavior. Mark every overriding method in derived classes with `override` (do not repeat `virtual` on overrides; use `final` on classes or overrides where further extension is invalid).
  - **Rule of Zero, Rule of Three, and Rule of Five**:
    - *Rule of Zero (Default)*: Prefer types composed of RAII members (`std::unique_ptr`, `std::vector`, `std::string`, custom RAII handles) without custom copy/move constructors, copy/move assignment operators, or destructors.
    - *Rule of Three*: If a class requires a custom destructor, copy constructor, or copy assignment operator (typically for legacy resource management), define all three.
    - *Rule of Five*: If a class defines a custom destructor or copy operation and supports move semantics, explicitly declare or `= delete` all five special member functions (destructor, copy constructor, copy assignment, move constructor, move assignment) to avoid unintended copies or moved-from state bugs.
  - **Scope Guards & RAII (`scope_exit`)**: Tie resource release, lock handling, and rollback actions to object lifetimes via RAII. Use scope-guard idioms (`scope_exit` / `scope_fail` / `scope_success` or dedicated RAII guard types) to guarantee cleanup on all exit paths, including early returns and exceptions.
  - **Dynamic vs. Static Polymorphism**:
    - *Dynamic Polymorphism*: Uses `virtual` dispatch (vtable indirection) or runtime type erasure (`std::function`, custom erased wrappers) when concrete types are chosen at runtime or cross a plugin/ABI boundary.
    - *Static Polymorphism*: Uses templates, C++20 `concepts`, CRTP (Curiously Recurring Template Pattern), or `std::variant` + `std::visit` to resolve dispatch at compile time, enabling inlining, zero vtable overhead, and value semantics when the type set is known at compile time.
- **Generic Programming**: Use C++ templates and C++20 `concepts` to write type-safe, reusable algorithms and data structures without runtime overhead.
- **Metaprogramming**: Leverage `constexpr`, `consteval`, and `<type_traits>` for compile-time computation and static introspection.
- **Functional Programming**: Utilize pure functions, immutability (`const`), lambdas, and `<ranges>` pipelines to minimize side effects.
- **Data-Oriented Design (DOD)**: Organize data layouts around CPU cache lines and memory access patterns (e.g., Structure of Arrays) for high-throughput workloads.
- **Procedural & Recursion**: Use straightforward procedural flows for linear tasks and controlled recursion (or tail-recursive patterns) for naturally hierarchical problems.

## What Kind of Type Is This
- A value type behaves like an `int`: copyable, comparable, no identity beyond its value. Most types should be value types. Aim for Regular: value semantics with copy, assignment and equality coherent.
- An entity type has identity and a lifetime. It is usually non-copyable and held by reference or by a smart pointer.
- A bundle of data with no invariant is a `struct` with public members and no member functions beyond construction. No getters and setters that only forward.
- `std::monostate`, `std::nullopt_t` and `std::ignore` (C++17) are bottom types that signal a defined absence; reach for them over invented sentinel member values.
- An invariant-holding type keeps data private, establishes the invariant in every constructor, and preserves it in every public member function. State the invariant once, in a comment or a debug `assert`.
- Provide no default constructor when a value-less object has no meaning.
- Never blend the two. A class with public data and an invariant has no invariant.

## Prefer the Simpler Mechanism
Order of preference for varying behaviour:
1. A parameter or a function object, with no new type.
2. A template, when the set of types is known at compile time.
3. A closed set of alternatives: `std::variant` plus `std::visit` (C++17).
4. An abstract interface and virtual dispatch, when the set is open or crosses a plugin or ABI boundary.
5. Inheritance of implementation, as a last resort.

Prefer composition to inheritance. Inherit to model a substitutable interface, not to reuse code. A member gives the reuse without the coupling.
- Avoid multiple and non-public inheritance of implementation; at most, interface bases multiply. When reuse without is-a is forced, private inheritance plus using-declarations keeps clients from converting derived to base, which also prevents slicing.

## Constructors and Invariants
- Establish the invariant in the constructor. A two-phase `init()` creates a window where the object is invalid and every method must check.
- Delegate between constructors instead of duplicating the body.
- Bases and members are constructed inside-out and destroyed outside-in, in reverse order of construction.
- Mark single-argument constructors `explicit`. `explicit(bool)` (C++20) makes the decision conditional in a template.
- Never call a virtual function from a constructor or a destructor. The dynamic type is not yet, or no longer, the derived one.
- A constructor that can fail throws, or a factory returns `optional` or `expected`. Never leave a "valid" flag for the caller to check.

## Virtual Functions
- A base class destructor is either public and virtual, which allows deletion through the base, or protected and non-virtual, which forbids it.
- Adding, removing or reordering virtual functions, members or bases breaks the class's ABI. A type crossing a wire or a mapped file excludes virtual functions, multiple inheritance and RTTI; reach for composition.
- Mark every override `override`, and `final` when further overriding would break the design. Never repeat `virtual` on an override.
- A member function template cannot be virtual: the vtable size cannot depend on how many specializations exist.
- An override must not change the default arguments or the accessibility. Both resolve statically and surprise the reader.
- An override must stay substitutable: preconditions no stronger, postconditions no weaker. A contract check sees both the static and the dynamic contract.
- Keep the virtual interface small. When the invariant must hold across overrides, use the non-virtual interface idiom: public non-virtual functions check the pre- and postconditions and call private virtual hooks.
- An abstract interface has no data members and no state.
- `dynamic_cast` in application code usually means the interface is missing a function. It is legitimate at a plugin or deserialization boundary.

## Slicing and Copying
- Copying a derived object through a base value slices it. Prevent it by making the base abstract, by deleting its copy operations, or by holding derived objects only through pointers.
- A polymorphic type that must be copied provides a virtual `clone()` returning `std::unique_ptr<Base>`.

## Layout, Size and Access
- Order members to reduce padding when the type is stored in bulk: largest alignment first. Verify with a `static_assert` on `sizeof` when the layout is part of a contract.
- A pointer to the first member of a standard-layout class interconverts with a pointer to the object itself.
- `alignas` for over-aligned types, taken from the property that requires it, never from a hardcoded literal.
- Pin a wire or ABI layout with `static_assert` (C++11) on size, alignment and offsets: a layout drift fails the build instead of corrupting exchanged data.
- Prefer `private` by default, and `protected` only for a hook a derived class must reach.
- A `friend` is part of the interface. Prefer a hidden friend for a type's operators.
- Expose behaviour, not storage. No getter and setter for every member.
- Empty base optimization and `[[no_unique_address]]` (C++20) remove the cost of stateless policy members.

## Class Templates
- Keep the non-dependent parts of a class template in a non-template base, so they instantiate once instead of per parameter.
- Prefer a member function template over a converting constructor set for related instantiations.
- A class template's static data member is one object per instantiation.

## Comparison and Hashing
- In C++20, default `operator==` and `operator<=>` when member-wise semantics are right, and write them when they are not.
- Before C++20, define `==` and `<` and derive the rest, or compare the members with `std::tie`.
- A key type for an unordered container needs a `std::hash` specialization consistent with its equality. Equal objects must hash equally. Combine member hashes through the hash algorithm itself: initialize and finalize once per aggregate, feed bases and members in one pass. A fixed numeric combine recipe pollutes the hash and can be unsound. `std::pair` and `std::tuple` have no `std::hash` specialization (C++11); write one for a key of that shape.
- Comparison must be a strict weak ordering. A comparator that returns true for equal elements corrupts a sort and is undefined behaviour.
- For a partial order, `a >= b` is `a > b || a == b`, never `!(a < b)`; write equivalence as `!(a < b) && !(b < a)`. Never define an ordering just to store a type in a map, never subtract operands, and never run `<` twice for a three-way result.
