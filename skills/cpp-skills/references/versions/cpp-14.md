# C++14

## Overview

C++14 is a minor version following C++11, introducing minor improvements, syntax conveniences, and defect fixes such as generic lambdas, variable templates, binary literals, digit separators, and `std::make_unique`.

## New Language Features

* Variable templates

* Generic lambdas (`auto` parameters)

* Initialized/Generalized lambda captures (init-capture)

* New/delete elision and sized deallocation

* Relaxed restrictions on `constexpr` functions

* Binary literals (e.g., `0b1010`)

* Digit separators using single quotes (e.g., `1'000'000`)

* Return type deduction for functions (`decltype(auto)`)

* Aggregate classes with default non-static member initializers

* `[[deprecated]]` attribute

## New Library Features

* `std::make_unique`

* `std::shared_timed_mutex` and `std::shared_lock`

* `std::integer_sequence`

* `std::exchange`

* `std::quoted`

* Library improvements:
  * Two-range overloads for algorithms (`std::equal`, `std::mismatch`, etc.)
  * Type alias versions of type traits (`_t` suffixes)
  * User-defined literals for `basic_string`, `duration`, and `complex`
  * Heterogeneous associative lookup
  * Addressing tuples by type (`std::get<T>()`)

## Compiler Support

### C++14 Core Language Features

| Feature | GCC | Clang | MSVC | Apple Clang | EDG eccp | Intel C++ | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| Binary literals | 4.3 | 3.1 | 19.0 | Yes | 4.10 | 11.0 | 
| Return type deduction (`decltype(auto)`) | 4.8 | 3.3 | 19.0 | Yes | 4.9 | 15.0 | 
| Lambda init-capture | 4.9 | 3.4 | 19.0 | Yes | 4.10 | 15.0 | 
| Generic lambda expressions | 4.9 | 3.4 | 19.0 | Yes | 4.10 | 16.0 | 
| Variable templates | 5 | 3.4 | 19.0 | Yes | 4.11 | 17.0 | 
| Extended `constexpr` | 5 | 3.4 | 19.10 | Yes | 4.11 | 17.0 | 
| Aggregates with default member initializers | 5 | 3.3 | 19.10 | Yes | 4.9 | 16.0 | 
| `[[deprecated]]` attribute | 4.9 | 3.4 | 19.0 | Yes | 4.9 | 15.0 | 
| Sized deallocation | 5 | 3.4 | 19.0 | Yes | 4.10.1 | 17.0 | 
| Single quote as digit separator | 4.9 | 3.4 | 19.0 | Yes | 4.10 | 16.0 | 

### C++14 Library Features

| Feature | GCC libstdc++ | Clang libc++ | MSVC STL | Apple Clang | 
| ----- | ----- | ----- | ----- | ----- | 
| `std::quoted` | 5 | 3.4 | 19.0 | Yes | 
| `std::make_unique` | 4.9 | 3.4 | 18.0 | Yes | 
| Heterogeneous associative lookup | 5 | 3.4 | 19.0 | Yes | 
| `std::integer_sequence` | 5 | 3.4 | 19.0 | Yes | 
| `std::shared_timed_mutex` | 5 | 3.4 | 19.0 | Yes | 
| `std::exchange` | 5 | 3.4 | 19.0 | Yes | 
