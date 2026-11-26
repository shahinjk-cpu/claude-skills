# C++11

## Overview

C++11 is the second major version of C++ and the most important update since C++98, introducing move semantics, lambdas, smart pointers, concurrency support, variadic templates, and uniform initialization.

## Merged Technical Specifications & Libraries

* **From TR1**: All of TR1 except Special Functions.
* **From Boost**: The thread library, `std::exception_ptr`, `std::error_code`, `std::error_condition`, range-based for loop, `static_assert`, and iterator improvements (`begin`, `end`, `next`, `prev`).
* **From C**: C-style Unicode conversion functions.

## Core Language Features

* `auto` type deduction and `decltype`
* Rvalue references (`&&`), move constructors, and move assignment operators
* Lambda expressions
* Variadic templates
* Strongly-typed scoped enums (`enum class`)
* `constexpr` and literal types
* Uniform list initialization and initializer lists (`std::initializer_list`)
* Delegating and inheriting constructors
* Defaulted and deleted functions (`= default`, `= delete`)
* `nullptr` keyword
* `long long` integer type
* `char16_t` and `char32_t` character types
* Type aliases (`using`)
* Unicode string literals and raw string literals
* User-defined literals
* `noexcept` specifier and operator
* `alignof` and `alignas`
* Multithreaded memory model and thread-local storage (`thread_local`)
* Range-based for loops
* `static_assert`
* `override` and `final` specifiers for virtual functions
* Attributes (`[[noreturn]]`, etc.)

## New Headers

* `<array>`
* `<atomic>`
* `<chrono>`
* `<condition_variable>`
* `<forward_list>`
* `<future>`
* `<initializer_list>`
* `<mutex>`
* `<random>`
* `<ratio>`
* `<regex>`
* `<scoped_allocator>`
* `<system_error>`
* `<thread>`
* `<tuple>`
* `<type_index>`
* `<type_traits>`
* `<unordered_map>`
* `<unordered_set>`

## New Library Features

* Concurrency support library (`std::thread`, `std::mutex`, `std::future`)
* Smart pointers: `std::unique_ptr` (and `std::shared_ptr` enhancements)
* `std::move_iterator`
* Stateful and scoped allocators
* `std::forward_list` (singly-linked list)
* Chrono library (`std::chrono`)
* Ratio library (`std::ratio`)
* `std::function` (polymorphic function wrapper)
* `std::exception_ptr`, `std::error_code`, and `std::error_condition`
* New algorithms: `std::all_of`, `std::any_of`, `std::none_of`, `std::find_if_not`, `std::copy_if`, `std::move`, `std::shuffle`, `std::is_sorted`, `std::minmax`, `std::iota`, etc.
* Disallowing Copy-On-Write (COW) for `std::basic_string`

## Compiler Support

### C++11 Core Language Features

| Feature | GCC | Clang | MSVC | Apple Clang | EDG eccp | Intel C++ | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| C99 preprocessor | 4.3 | Yes | 19.0 | Yes | 4.1 | 11.1 | 
| `static_assert` | 4.3 | 2.9 | 16.0 | Yes | 4.1 | 11.0 | 
| Right angle brackets | 4.3 | Yes | 14.0 | Yes | 4.1 | 11.0 | 
| `long long` | Yes | Yes | 14.0 | Yes | Yes | Yes | 
| `auto` | 4.4 | Yes | 16.0 | Yes | 3.9 | 11.0 | 
| Delegating constructors | 4.7 | 3.0 | 18.0 | Yes | 4.7 | 14.0 | 
| `constexpr` | 4.6 | 3.1 | 19.0 | Yes | 4.6 | 13.0 | 
| `char16_t` and `char32_t` | 4.4 | 2.9 | 19.0 | Yes | 4.4 | 12.1 | 
| Template aliases | 4.7 | 3.0 | 18.0 | Yes | 4.2 | 12.1 | 
| `alignas` / `alignof` | 4.8 | 3.0 | 19.0 | Yes | 4.8 | 15.0 | 
| Defaulted and deleted functions | 4.4 | 3.0 | 18.0 | Yes | 4.1 | 12.0 | 
| Strongly-typed enum | 4.4 | 2.9 | 16.0 | Yes | 4.0 | 13.0 | 
| Atomic operations | 4.4 | 3.1 | 17.0 | Yes | Yes | 13.0 | 
| `nullptr` | 4.6 | 2.9 | 16.0 | Yes | 4.2 | 12.1 | 
| Explicit conversion operators | 4.5 | 3.0 | 18.0 | Yes | 4.4 | 13.0 | 
| Ref-qualifiers | 4.8.1 | 2.9 | 19.0 | Yes | 4.7 | 14.0 | 
| Unicode string literals | 4.4 | 3.0 | 19.0 | Yes | 4.7 | 11.0 | 
| Raw string literals | 4.5 | Yes | 18.0 | Yes | 4.7 | 14.0 | 
| Inline namespaces | 4.4 | 2.9 | 19.0 | Yes | 4.5 | 14.0 | 
| Inheriting constructors | 4.8 | 3.3 | 19.0 | Yes | 4.8 | 15.0 | 
| Trailing function return types | 4.4 | 2.9 | 16.0 | Yes | 4.1 | 12.0 | 
| Unrestricted unions | 4.6 | 3.0 | 19.0 | Yes | 4.6 | 14.0 | 
| Variadic templates | 4.3 | 2.9 | 18.0 | Yes | 4.3 | 12.1 | 
| Thread-local storage | 4.8 | 3.3 | 16.0 | Yes | 4.8 | 11.1 | 
| Initializer lists | 4.4 | 3.1 | 18.0 | Yes | 4.5 | 13.0 | 
| User-defined literals | 4.7 | 3.1 | 19.0 | Yes | 4.8 | 15.0 | 
| Rvalue references | 4.5 | 2.9 | 16.0 | Yes | 4.5 | 11.1 | 
| Lambda expressions | 4.5 | 3.1 | 16.0 | Yes | 4.1 | 12.0 | 
| Range-for loop | 4.6 | 3.0 | 17.0 | Yes | 4.5 | 13.0 | 
| `noexcept` | 4.6 | 3.0 | 19.0 | Yes | 4.5 | 14.0 | 
| `override` and `final` | 4.7 | 2.9 | 14.0 | Yes | 4.8 | 12.0 | 
| `decltype` | 4.3 | 2.9 | 16.0 | Yes | 4.2 | 11.0 | 

### C++11 Library Features

| Feature | GCC libstdc++ | Clang libc++ | MSVC STL | Apple Clang | 
| ----- | ----- | ----- | ----- | ----- | 
| Regular expressions library | 4.9 | 2.8 | Yes | Yes | 
| Type traits | 4.8 | 3.0 | 19.0 | Yes | 
| Container iterator methods (`cbegin`, etc.) | 4.5 | Yes | 16.0 | Yes | 
| Disallowing COW `std::basic_string` | 5 | Yes | Yes | Yes | 
