# Naming Conventions Reference

## Overview

Consistent naming conventions for the C++ skills repository to ensure code readability, maintainability, and clean separation between types, scopes, and variable roles.

## Identifiers & Casing Rules

* **Classes & Structs**: Use `PascalCase` for all class, struct, union, and concept names (e.g., `ThreadPool`, `DataBuffer`).

* **Functions & Methods**: Use `camelCase` for functions and member methods (e.g., `calculateMetrics`, `processItem`).

* **Local Variables & Parameters**: Use `snake_case` for standard function variables and parameters (e.g., `item_count`, `buffer_size`).

* **Constants & Global Variables**: Use `k_` followed by `camelCase` or `SCREAMING_SNAKE_CASE` for global constants and compile-time constants (e.g., `kMaxBufferSize` or `MAX_BUFFER_SIZE`).

* **Macros**: Use `SCREAMING_SNAKE_CASE` strictly for preprocessor macros (e.g., `ASSERT_VALID`).

* **Namespaces**: Use `snake_case` for namespace identifiers to keep them distinct from class names (e.g., `memory_pool`, `network_protocols`).

## Object-Oriented Programming (OOP) & Variable Scoping Rules

* **Member Variables**: Prefix non-static data members with `m_` (e.g., `m_capacity`, `m_mutex`) to distinguish them clearly from local variables.

* **Static Members**: Prefix static data members with `s_` (e.g., `s_instance_count`) to identify shared static storage across the class.

* **Boolean Variables & Predicates**: Prefix boolean variables, flags, and query methods with `is_` (e.g., `is_ready`, `is_connected`) or use standard boolean naming formats.