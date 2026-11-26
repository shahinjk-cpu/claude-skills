# C++ Complete Reference Index

## Core Language

### Lexical & General Rules
- Preprocessor & comments
- ASCII chart
- Keywords & name lookup
- Fundamental types
- The `main` function
- Freestanding implementations

### Expressions & Control Flow
- Value categories & evaluation order
- Operators & precedence
- Conversions & literals
- Constant expressions
- Declarations & initialization
- Statements (`if`, `switch`, `for`, range-based `for` [C++11], `while`, `do-while`)

### Functions, Classes, Templates & Modern Language Features
- Functions & overloading
- Classes & unions
- Templates & exceptions
- Coroutines (C++20)
- Modules (C++20)
- Contracts (C++26)

---

## Standard Library

### Language Support & Diagnostics
- Standard library headers & named requirements
- Feature-test macros (C++20: language, library, headers)
- Type support (`type_info`, `numeric_limits`, `exception`), `initializer_list` (C++11), variadic functions & `source_location` (C++20)
- Comparison utilities (C++20) & concepts library (C++20)
- Coroutine support (C++20), contract support (C++26) & execution support library (C++26)
- Program utilities (signals, non-local jumps) & basic memory management
- Diagnostics: assertions, error numbers, `<system_error>` (C++11), `basic_stacktrace` (C++23) & debugging support (C++26)

### Memory, Metaprogramming & General Utilities
- Memory management: allocators, smart pointers & memory resources (`<memory_resource>`, C++17)
- Metaprogramming (C++11): type traits, `<ratio>`, `integer_sequence` (C++14) & reflection (C++26)
- General utilities: function objects, hashing & swap/type operations (C++11)
- Integer comparison utilities (C++20), `bitset` & bit manipulation (`<bit>`, C++20)
- Vocabulary & tuple types: `pair` & `tuple` (C++11), `optional` (C++17), `variant` & `any` (C++17), `expected` (C++23)

### Containers, Iterators, Ranges & Algorithms
- Sequence containers: `vector`, `deque`, `array` (C++11), `list`, `forward_list` (C++11) & `inplace_vector` (C++26)
- Associative & unordered containers: `map`, `multimap`, `set`, `multiset` & `unordered_map` / `unordered_multimap` / `unordered_set` / `unordered_multiset` (C++11)
- Specialized containers & views: `hive` (C++26), container adaptors, `span` (C++20) & `mdspan` (C++23)
- Iterators library
- Ranges library (C++20): range factories, range adaptors & `generator` (C++23)
- Algorithms library: numeric algorithms, execution policies (C++17) & constrained algorithms (C++20)

### Strings & Text Processing
- Strings: `basic_string`, `char_traits` & `basic_string_view` (C++17)
- Primitive numeric conversions (`<charconv>`, C++17), formatting (`<format>`, C++20), localization & `text_encoding` (C++26)
- Regular expressions (C++11): `basic_regex`, algorithms & default grammar
- Null-terminated sequence utilities (byte, multibyte, wide)

### Numerics, Date/Time & Input/Output
- Numerics: common math functions, special functions (C++17), mathematical constants (C++20) & basic linear algebra algorithms (C++26)
- Data-parallel types / SIMD (C++26), pseudo-random number generation, floating-point environment (C++11), `complex` & `valarray`
- Date and time (`<chrono>`): calendar (C++20) & time zones (C++20)
- Input/output: `<print>` functions (C++23), stream-based I/O, manipulators, `basic_istream` / `basic_ostream`, synchronized output (C++20) & filesystem (C++17)

### Concurrency Support (C++11)
- Threads & cancellation: `thread` & `jthread` (C++20)
- Atomics & memory model: `atomic`, `atomic_flag`, `atomic_ref` (C++20), `memory_order` & safe reclamation (C++26)
- Synchronization & coordination: mutexes, condition variables, futures, semaphores (C++20), `latch` (C++20) & `barrier` (C++20)

---

## Technical Specifications (TS)
- **Library Fundamentals TS:** `resource_adaptor` & `invocation_type`
- **Library Fundamentals TS v2:** `propagate_const`, `ostream_joiner`, `randint`, `observer_ptr` & detection idiom
- **Library Fundamentals TS v3:** `scope_exit`, `scope_fail`, `scope_success` & `unique_resource`
- **Parallelism TS v2:** `simd`
- **Concurrency TS** & **Transactional Memory TS**
