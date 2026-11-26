# Design Patterns & Architectural Guidelines

## Overview
Guidelines for structuring modular, maintainable, and decoupled C++ architectures using proven design patterns and core software engineering principles.

## Clean Code & Core Principles
- **Modern Standards**: Write clean, idiomatic C++ following modern standards (C++20/C++23), leveraging standard library facilities over custom workarounds.
- **Meaningful Naming**: Choose clear, self-documenting names for variables, functions, and types to minimize the need for redundant comments.
- **Composition Over Inheritance**: Favor assembling behavior through object composition and interfaces rather than deep, rigid inheritance hierarchies.
- **Small & Focused Functions**: Adhere to the Single Responsibility Principle at the function level—keep functions concise, readable, and dedicated to a single task.

## Software Engineering Principles
- **SOLID**:
  - **S**ingle Responsibility Principle
  - **O**pen/Closed Principle
  - **L**iskov Substitution Principle
  - **I**nterface Segregation Principle
  - **D**ependency Inversion Principle
- **DRY (Don't Repeat Yourself)**: Abstract shared logic into reusable templates, functions, or components to eliminate code duplication.
- **KISS (Keep It Simple, Stupid)**: Favor straightforward, readable solutions over unnecessary complexity.
- **YAGNI (You Aren't Gonna Need It)**: Implement features and abstractions only when actually required, avoiding speculative over-engineering.

## Architectural & Design Patterns
- **Behavioral Patterns**:
  - **Strategy**: Encapsulate interchangeable algorithms behind a common interface, callable/function object, or template policy so selection stays decoupled from execution.
  - **Template Method**: Define the skeleton of an algorithm in a base class or template while delegating specific steps to subclasses, hooks, or policy parameters.
- **Creational & Structural Patterns**:
  - **Factory**: Centralize and decouple object instantiation logic from client code, returning concrete types, smart pointers, or `std::expected` / `std::optional` on fallible construction.
  - **Registry**: Maintain lookup tables mapping identifiers (strings, enums, or keys) to factories, handlers, or services without hardcoding branches at call sites.
- **Architectural Patterns**:
  - **MVC (Model-View-Controller)**: Separate core data/business logic (Model), presentation (View), and input/event handling (Controller) to keep domain logic independent of UI or transport layers.
