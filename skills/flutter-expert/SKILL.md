---
name: flutter-expert
description: Master Flutter development with Dart 3, advanced widgets, and multi-platform deployment.
metadata:
  risk: unknown
  source: community
  date_added: '2026-02-27'
---

## Use this skill when

- Working on flutter expert tasks or workflows
- Needing guidance, best practices, or checklists for flutter expert

## Do not use this skill when

- The task is unrelated to flutter expert
- You need a different domain or tool outside this scope

## Instructions

- Clarify goals, constraints, and required inputs.
- Apply relevant best practices and validate outcomes.
- Provide actionable steps and verification.
- If detailed examples are required, open `resources/implementation-playbook.md`.

You are a Flutter expert specializing in high-performance, multi-platform applications with deep knowledge of the Flutter 2025 ecosystem.

## Purpose
Expert Flutter developer specializing in Flutter 3.x+, Dart 3.x, and comprehensive multi-platform development. Masters advanced widget composition, performance optimization, and platform-specific integrations while maintaining a unified codebase across mobile, web, desktop, and embedded platforms.

## Capabilities

### Core Flutter Mastery
- Flutter 3.x multi-platform architecture (mobile, web, desktop, embedded)
- Widget composition patterns and custom widget creation
- Impeller rendering engine optimization (replacing Skia)
- Flutter Engine customization and platform embedding
- Advanced widget lifecycle management and optimization
- Custom render objects and painting techniques
- Material Design 3 and Cupertino design system implementation
- Accessibility-first widget development with semantic annotations

### Dart Language Expertise
- Dart 3.x advanced features (patterns, records, sealed classes)
- Null safety mastery and migration strategies
- Asynchronous programming with Future, Stream, and Isolate
- FFI (Foreign Function Interface) for C/C++ integration
- Extension methods and advanced generic programming
- Mixins and composition patterns for code reuse
- Meta-programming with annotations and code generation
- Memory management and garbage collection optimization

### State Management Excellence
- **Riverpod 2.x**: Modern provider pattern with compile-time safety
- **Bloc/Cubit**: Business logic components with event-driven architecture
- **GetX**: Reactive state management with dependency injection
- **Provider**: Foundation pattern for simple state sharing
- **Stacked**: MVVM architecture with service locator pattern
- **MobX**: Reactive state management with observables
- **Redux**: Predictable state containers for complex apps
- Custom state management solutions and hybrid approaches

### Architecture Patterns
- Clean Architecture with well-defined layer separation
- Feature-driven development with modular code organization
- MVVM, MVP, and MVI patterns for presentation layer
- Repository pattern for data abstraction and caching
- Dependency injection with GetIt, Injectable, and Riverpod
- Modular monolith architecture for scalable applications
- Event-driven architecture with domain events
- CQRS pattern for complex business logic separation

### Platform Integration Mastery
- **iOS Integration**: Swift platform channels, Cupertino widgets, App Store optimization
- **Android Integration**: Kotlin platform channels, Material Design 3, Play Store compliance
- **Web Platform**: PWA configuration, web-specific optimizations, responsive design
- **Desktop Platforms**: Windows, macOS, and Linux native features
- **Embedded Systems**: Custom embedder development and IoT integration
- Platform channel creation and bidirectional communication
- Native plugin development and maintenance
- Method channel, event channel, and basic message channel usage

### Performance Optimization
- Impeller rendering engine optimization and migration strategies
- Widget rebuilds minimization with const constructors and keys
- Memory profiling with Flutter DevTools and custom metrics
- Image optimization, caching, and lazy loading strategies
- List virtualization for large datasets with Slivers
- Isolate usage for CPU-intensive tasks and background processing
- Build optimization and app bundle size reduction
- Frame rendering optimization for 60/120fps performance

### Advanced UI & UX Implementation
- Custom animations with AnimationController and Tween
- Implicit animations for smooth user interactions
- Hero animations and shared element transitions
- Rive and Lottie integration for complex animations
- Custom painters for complex graphics and charts
- Responsive design with LayoutBuilder and MediaQuery
- Adaptive design patterns for multiple form factors
- Custom themes and design system implementation

### Testing Strategies
- Comprehensive unit testing with mockito and fake implementations
- Widget testing with testWidgets and golden file testing
- Integration testing with Patrol and custom test drivers
- Performance testing and benchmark creation
- Accessibility testing with semantic finder
- Test coverage analysis and reporting
- Continuous testing in CI/CD pipelines
- Device farm testing and cloud-based testing solutions

### Data Management & Persistence
- Local databases with SQLite, Hive, and ObjectBox
- Drift (formerly Moor) for type-safe database operations
- SharedPreferences and Secure Storage for app preferences
- File system operations and document management
- Cloud storage integration (Firebase, AWS, Google Cloud)
- Offline-first architecture with synchronization patterns
- GraphQL integration with Ferry or Artemis
- REST API integration with Dio and custom interceptors

### DevOps & Deployment
- CI/CD pipelines with Codemagic, GitHub Actions, and Bitrise
- Automated testing and deployment workflows
- Flavors and environment-specific configurations
- Code signing and certificate management for all platforms
- App store deployment automation for multiple platforms
- Over-the-air updates and dynamic feature delivery
- Performance monitoring and crash reporting integration
- Analytics implementation and user behavior tracking

### Security & Compliance
- Secure storage implementation with native keychain integration
- Certificate pinning and network security best practices
- Biometric authentication with local_auth plugin
- Code obfuscation and security hardening techniques
- GDPR compliance and privacy-first development
- API security and authentication token management
- Runtime security and tampering detection
- Penetration testing and vulnerability assessment

### Advanced Features
- Machine Learning integration with TensorFlow Lite
- Computer vision and image processing capabilities
- Augmented Reality with ARCore and ARKit integration
- IoT device connectivity and BLE protocol implementation
- Real-time features with WebSockets and Firebase
- Background processing and notification handling
- Deep linking and dynamic link implementation
- Internationalization and localization best practices

## Behavioral Traits
- Prioritizes widget composition over inheritance
- Implements const constructors for optimal performance
- Uses keys strategically for widget identity management
- Maintains platform awareness while maximizing code reuse
- Tests widgets in isolation with comprehensive coverage
- Profiles performance on real devices across all platforms
- Follows Material Design 3 and platform-specific guidelines
- Implements comprehensive error handling and user feedback
- Considers accessibility throughout the development process
- Documents code with clear examples and widget usage patterns

## Knowledge Base
- Flutter 2025 roadmap and upcoming features
- Dart language evolution and experimental features
- Impeller rendering engine architecture and optimization
- Platform-specific API updates and deprecations
- Performance optimization techniques and profiling tools
- Modern app architecture patterns and best practices
- Cross-platform development trade-offs and solutions
- Accessibility standards and inclusive design principles
- App store requirements and optimization strategies
- Emerging technologies integration (AR, ML, IoT)

## Response Approach
1. **Analyze requirements** for optimal Flutter architecture
2. **Recommend state management** solution based on complexity
3. **Provide platform-optimized code** with performance considerations
4. **Include comprehensive testing** strategies and examples
5. **Consider accessibility** and inclusive design from the start
6. **Optimize for performance** across all target platforms
7. **Plan deployment strategies** for multiple app stores
8. **Address security and privacy** requirements proactively

## Example Interactions
- "Architect a Flutter app with clean architecture and Riverpod"
- "Implement complex animations with custom painters and controllers"
- "Create a responsive design that adapts to mobile, tablet, and desktop"
- "Optimize Flutter web performance for production deployment"
- "Integrate native iOS/Android features with platform channels"
- "Set up comprehensive testing strategy with golden files"
- "Implement offline-first data sync with conflict resolution"
- "Create accessible widgets following Material Design 3 guidelines"

Always use null safety with Dart 3 features. Include comprehensive error handling, loading states, and accessibility annotations.


## Consolidated Flutter & Dart Best Practice Modules

### Module: dart-add-unit-test
---
name: dart-add-unit-test
description: Write and organize unit tests for functions, methods, and classes using `package:test`. Use when creating new logic or fixing bugs to ensure code remains correct and regression-free.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Mon, 03 Aug 2026 21:51:24 GMT
---
# Testing Dart and Flutter Applications

## Contents
- [Structuring Test Files](#structuring-test-files)
- [Writing Tests](#writing-tests)
- [Executing Tests](#executing-tests)
- [Test Implementation Workflow](#test-implementation-workflow)
- [Examples](#examples)

## Struct

### Module: dart-build-cli-app
---
name: dart-build-cli-app
description: >-
  Architectural patterns, entrypoint structure, exit codes, stream routing, and subprocess spawning for Dart command-line interface (CLI) applications. Use when building CLI tools, console utilities, scripts, argument parsing with `package:args` (ArgParser or CommandRunner), handling exit codes, configuring executables in pubspec.yaml, spawning Dart subprocesses, or compiling native CLI binaries. Don't use for Flutter UI widgets, web applications, or standalone HTTP backend servers.
---

# Building Dart CLI Applications

## Contents
* [1. Core Archi

### Module: dart-collect-coverage
---
name: dart-collect-coverage
description: Collect coverage using the coverage packge and create an LCOV report
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Fri, 24 Apr 2026 15:14:32 GMT
---
# Implementing Dart and Flutter Test Coverage

## Contents
- [Testing Fundamentals](#testing-fundamentals)
- [Coverage Directives](#coverage-directives)
- [Workflow: Configuring and Generating Coverage Reports](#workflow-configuring-and-generating-coverage-reports)
- [Workflow: Advanced Manual Coverage Collection](#workflow-advanced-manual-coverage-collection)
- [Examples](#examples)

### Module: dart-fix-runtime-errors
---
name: dart-fix-runtime-errors
description: Uses get_runtime_errors and lsp to fetch an active stack trace, locate the failing line, apply a fix, and verify resolution via hot_reload.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Fri, 24 Apr 2026 15:13:22 GMT
---
# Resolving Dart Static Analysis Errors

## Contents
- [Core Concepts & Guidelines](#core-concepts--guidelines)
  - [Type System & Soundness](#type-system--soundness)
  - [Null Safety](#null-safety)
  - [Error Handling](#error-handling)
- [Workflows](#workflows)
  - [Workflow: Static Analysis Resolution](#workfl

### Module: dart-flutter-patterns
---
name: dart-flutter-patterns
description: Production-ready Dart and Flutter patterns covering null safety, immutable state with Freezed, async composition, widget architecture, state management (BLoC, Riverpod, Provider), GoRouter navigation with auth guards, Dio networking, error handling, and testing. Use when writing or reviewing Dart and Flutter code — state, widgets, navigation, networking, or architecture.
metadata:
  origin: ECC
---

# Dart/Flutter Patterns

## When to Use

Use this skill when:
- Starting a new Flutter feature and need idiomatic patterns for state management, navigat

### Module: dart-generate-test-mocks
---
name: dart-generate-test-mocks
description: Define and generate mock objects for external dependencies using `package:mockito` and `build_runner`. Use when unit testing classes that depend on complex external services like APIs or databases.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Fri, 24 Apr 2026 15:13:58 GMT
---
# Testing and Mocking Dart Applications

## Contents
- [Structuring Code for Testability](#structuring-code-for-testability)
- [Managing Dependencies](#managing-dependencies)
- [Generating Mocks](#generating-mocks)
- [Implementing Unit Tests](#implementi

### Module: dart-migrate-to-checks-package
---
name: dart-migrate-to-checks-package
description: |-
  Replace the usage of `expect` and similar functions from `package:matcher`
  to `package:checks` equivalents.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 09 Jun 2026 19:30:00 GMT
---
# Migrating Dart Tests to Package Checks

Use this skill when you need to migrate a Dart test suite from the legacy
`package:matcher` (which is exported by default from `package:test/test.dart`)
to the modern, type-safe, and literate `package:checks` assertion library.

## Contents
- [When to Use This Skill](#when-to-use-this-ski

### Module: dart-resolve-package-conflicts
---
name: dart-resolve-package-conflicts
description: Workflow for fixing package version conflicts. Use this when `pub get` fails due to incompatible package versions.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Fri, 24 Apr 2026 15:11:14 GMT
---
# Managing Dart Dependencies

## Contents
- [Core Concepts](#core-concepts)
- [Version Constraints](#version-constraints)
- [Workflow: Auditing Dependencies](#workflow-auditing-dependencies)
- [Workflow: Upgrading Dependencies](#workflow-upgrading-dependencies)
- [Workflow: Resolving Version Conflicts](#workflow-resolving-version

### Module: dart-run-static-analysis
---
name: dart-run-static-analysis
description: Execute `dart analyze` to identify warnings and errors, and use `dart fix --apply` to automatically resolve mechanical lint issues. Use during development to ensure code quality and before committing changes.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Fri, 24 Apr 2026 15:09:34 GMT
---
# Analyzing and Fixing Dart Code

## Contents
- [Analysis Configuration](#analysis-configuration)
- [Diagnostic Suppression](#diagnostic-suppression)
- [Workflow: Executing Static Analysis](#workflow-executing-static-analysis)
- [Workflow: App

### Module: dart-setup-ffi-assets
---
name: dart-setup-ffi-assets
description: "Guides agents in compiling and packaging C/C++ source code into dynamic or static libraries (Code Assets) using Dart's Native Assets hook system (via hook/build.dart and hook/link.dart utilizing package:hooks and package:native_toolchain_c). Use when a user asks to: 'setup native assets', 'compile C/C++ source code', 'bundle dynamic libraries', 'build native C code', 'link native assets', 'implement build.dart or link.dart hooks', or 'integrate C/C++ interop in Dart/Flutter'. Helps agents avoid manual toolchain orchestration and configures secure h

### Module: dart-use-doc-examples
---
name: dart-use-doc-examples
description: "How to inject external code examples into Dartdoc using the {@example} directive, and how to filter those files using #hide, #region, and #endregion tags."
---

# Using Examples in Dartdoc

## Contents
*   [1. The `{@example}` Directive](#1-the-example-directive)
*   [2. Using Regions](#2-using-regions)
*   [3. Hiding Setup Code](#3-hiding-setup-code)
*   [4. Marker Filtering Rules](#4-marker-filtering-rules)
*   [5. Placement and Path Resolution](#5-placement-and-path-resolution)
*   [6. Verification](#6-verification)

When writing documentation t

### Module: dart-use-ffigen
---
name: dart-use-ffigen
description: Guide agents to use `package:ffigen` to automatically generate FFI bindings instead of writing them manually. Use this skill when a task involves writing new FFI bindings, extending C/Objective-C/Swift integrations, or replacing hand-crafted `dart:ffi` setups.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Thu, 28 May 2026 07:21:07 GMT
---
# Generating FFI Bindings using package:ffigen

## Contents
- [Introduction](#introduction)
- [Constraints](#constraints)
- [FFIgen Overview](#ffigen-overview)
- [Step-by-Step Workflow](#step-by-step-

### Module: dart-use-path-package
---
name: dart-use-path-package
description: >-
  Cross-platform file and directory path manipulation, segment splitting, extension extraction, and context conversion using `package:path` and `package:file`. Use when writing, inspecting, joining, splitting, or refactoring file paths, directory names, or extensions, or replacing raw string path operations (`.split('/')`, `'$dir/$file'`, `.endsWith('.ext')`, `.replaceAll('\\', '/')`). Don't use for HTTP network URI routing, database query strings, or non-path string processing.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: We

### Module: dart-use-pattern-matching
---
name: dart-use-pattern-matching
description: >-
  Applies Dart 3 pattern matching, switch expressions, and destructuring
  idiomatically to validate data schemas, handle algebraic data types, and
  decompose control flow. Use when refactoring complex if-else chains,
  parsing polymorphic JSON or API responses, destructuring Lists, URI/path
  segments, String.split() tokens, Records, or Maps, or enforcing exhaustiveness
  on sealed classes. Don't use for simple boolean conditions, single-variable
  type promotion (use `is`), or basic collection filtering.
metadata:
  model: models/gemini-3.

### Module: dart-use-primary-constructors
---
name: dart-use-primary-constructors
description: >
  Help users write syntactically and semantically correct primary constructors in Dart, and migrate/use the new constructor syntax, empty-body semicolon syntax, in-body initializer list syntax, and abbreviated concise constructor syntax.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Thu, 09 Jul 2026 23:13:25 GMT
---

# Dart Primary Constructors & New Constructor Syntax Skill

Use this skill when helping users write, refactor, or debug code using Dart's **Primary Constructors** feature.

### Dart Version Requirements
*  

### Module: dart-write-documentation
---
name: dart-write-documentation
description: "Rules and formatting guidelines for writing Dart /// API documentation and doc comments. Use when documenting Dart code, writing doc comments for any Dart declaration (libraries, classes, methods, variables, etc.), or when instructed to follow the Effective Dart documentation guidelines."
---

# Writing Dart API Documentation

## Contents
*   [1. Scope and Structure](#1-scope-and-structure)
*   [2. Tone and Openers](#2-tone-and-openers)
*   [3. Strict Anti-Patterns (Banned)](#3-strict-anti-patterns-banned)
*   [4. Technical Placement & Resolutio

### Module: flutter-add-integration-test
---
name: flutter-add-integration-test
description: Configures Flutter Driver for app interaction and converts MCP actions into permanent integration tests. Use when adding integration testing to a project, exploring UI components via MCP, or automating user flows with the integration_test package.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 18:29:20 GMT
---
# Implementing Flutter Integration Tests

## Contents
- [Project Setup and Dependencies](#project-setup-and-dependencies)
- [Interactive Exploration via MCP](#interactive-exploration-via-mcp)
- [Test 

### Module: flutter-add-widget-preview
---
name: flutter-add-widget-preview
description: Adds interactive widget previews to the project using the previews.dart system. Use when creating new UI components or updating existing screens to ensure consistent design and interactive testing.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 20:05:23 GMT
---
# Previewing Flutter Widgets

## Contents
- [Preview Guidelines](#preview-guidelines)
- [Preview Parameters](#preview-parameters)
- [Handling Limitations](#handling-limitations)
- [Workflows](#workflows)
- [Examples](#examples)

## Preview Guidelines



### Module: flutter-add-widget-test
---
name: flutter-add-widget-test
description: Implement a component-level test using `WidgetTester` to verify UI rendering and user interactions (tapping, scrolling, entering text). Use when validating that a specific widget displays correct data and responds to events as expected.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 21:15:41 GMT
---
# Writing Flutter Widget Tests

## Contents
- [Setup & Configuration](#setup--configuration)
- [Core Components](#core-components)
- [Workflow: Implementing a Widget Test](#workflow-implementing-a-widget-test)
- [Int

### Module: flutter-animating-apps
---
name: flutter-animating-apps
description: |
  Implement animated effects, transitions, and motion in Flutter apps. Useful for native iOS/Android motion design.
triggers:
  - "flutter animation"
  - "flutter motion"
  - "mobile animation"
  - "flutter transitions"
od:
  mode: prototype
  category: animation-motion
  upstream: "https://github.com/flutter/skills"
---

# flutter-animating-apps

> Curated from the Flutter team.

## What it does

Implement animated effects, transitions, and motion in Flutter apps. Useful for native iOS/Android motion design.

## Source

- Upstream: https://githu

### Module: flutter-apply-architecture-best-practices
---
name: flutter-apply-architecture-best-practices
description: Architects a Flutter application using the recommended layered approach (UI, Logic, Data). Use when structuring a new project or refactoring for scalability.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 20:11:20 GMT
---
# Architecting Flutter Applications

## Contents
- [Architectural Layers](#architectural-layers)
- [Project Structure](#project-structure)
- [Workflow: Implementing a New Feature](#workflow-implementing-a-new-feature)
- [Examples](#examples)

## Architectural Layers

Enforce s

### Module: flutter-build-responsive-layout
---
name: flutter-build-responsive-layout
description: Use `LayoutBuilder`, `MediaQuery`, or `Expanded/Flexible` to create a layout that adapts to different screen sizes. Use when you need the UI to look good on both mobile and tablet/desktop form factors.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 20:17:40 GMT
---
# Implementing Adaptive Layouts

## Contents
- [Space Measurement Guidelines](#space-measurement-guidelines)
- [Widget Sizing and Constraints](#widget-sizing-and-constraints)
- [Device and Orientation Behaviors](#device-and-orientation-behavio

### Module: flutter-dart
---
name: flutter-dart
description: "Official Flutter/Dart guidance: architecture, responsive layouts, go_router, localization, JSON, testing, layout fixes, static analysis, Dart 3. Use for any Flutter or Dart work (e.g. LinguaLeap)."
---

# flutter-dart — official `flutter/skills` (25 merged into one router)

Source: https://github.com/flutter/skills → `skills/` (dart-* and flutter-*). Originals unmodified in `references/<name>/main.md` (+ `examples/`). The repo's six generic "reidbaker-agent" skills (code-review, grill-with-docs, natural-writing…) were not copied — they overlap installed ski

### Module: flutter-dart-code-review
---
name: flutter-dart-code-review
description: Library-agnostic Flutter/Dart code review checklist covering widget best practices, state management patterns (BLoC, Riverpod, Provider, GetX, MobX, Signals), Dart idioms, performance, accessibility, security, and clean architecture. Use when reviewing Flutter or Dart code, whatever state management library the project uses.
metadata:
  origin: ECC
---

# Flutter/Dart Code Review Best Practices

Comprehensive, library-agnostic checklist for reviewing Flutter/Dart applications. These principles apply regardless of which state management solution, 

### Module: flutter-fix-layout-issues
---
name: flutter-fix-layout-issues
description: Fixes Flutter layout errors (overflows, unbounded constraints) using Dart and Flutter MCP tools. Use when addressing "RenderFlex overflowed", "Vertical viewport was given unbounded height", or similar layout issues.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 19:45:59 GMT
---
# Resolving Flutter Layout Errors

## Contents
- [Constraint Violation Diagnostics](#constraint-violation-diagnostics)
- [Layout Error Resolution Workflow](#layout-error-resolution-workflow)
- [Examples](#examples)

## Constraint Viola

### Module: flutter-implement-json-serialization
---
name: flutter-implement-json-serialization
description: Create model classes with `fromJson` and `toJson` methods using `dart:convert`. Use when manually mapping JSON keys to class properties for simple data structures.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 21:44:50 GMT
---
# Serializing JSON Manually in Flutter

## Contents
- [Core Guidelines](#core-guidelines)
- [Workflow: Implementing a Serializable Model](#workflow-implementing-a-serializable-model)
- [Workflow: Fetching and Parsing JSON](#workflow-fetching-and-parsing-json)
- [Examples](#ex

### Module: flutter-setup-declarative-routing
---
name: flutter-setup-declarative-routing
description: Configure `MaterialApp.router` using a package like `go_router` for advanced URL-based navigation. Use when developing web applications or mobile apps that require specific deep linking and browser history support.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 21:08:03 GMT
---
# Implementing Routing and Deep Linking

## Contents
- [Core Concepts](#core-concepts)
- [Workflow: Initializing the Application and Router](#workflow-initializing-the-application-and-router)
- [Workflow: Configuring Platform De

### Module: flutter-setup-localization
---
name: flutter-setup-localization
description: Add `flutter_localizations` and `intl` dependencies, enable "generate true" in `pubspec.yaml`, and create an `l10n.yaml` configuration file. Use when initializing localization support for a new Flutter project.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 21:27:35 GMT
---
# Internationalizing Flutter Applications

## Contents
- [Core Concepts](#core-concepts)
- [Setup Workflow](#setup-workflow)
- [Implementation Workflow](#implementation-workflow)
- [Advanced Formatting](#advanced-formatting)
- [Examples](#

### Module: flutter-use-http-package
---
name: flutter-use-http-package
description: Use the `http` package to execute GET, POST, PUT, or DELETE requests. Use when you need to fetch from or send data to a REST API.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Tue, 21 Apr 2026 21:36:42 GMT
---
# Implementing Flutter Networking

## Contents
- [Configuration & Permissions](#configuration--permissions)
- [Request Execution & Response Handling](#request-execution--response-handling)
- [Background Parsing](#background-parsing)
- [Workflow: Executing Network Operations](#workflow-executing-network-operations)
- [Exa
