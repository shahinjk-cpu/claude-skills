---
name: react-expert
description: Master React development suite covering hooks, server components, bundle optimization, state management, testing, and UI patterns.
---

# React Master Architecture & Performance Suite


## Advanced React Architecture & Performance Guidelines

### Module: react-best-practices
---
name: react-best-practices
description: React and Next.js performance optimization guidelines from Vercel Engineering. This skill should be used when writing, reviewing, or refactoring React/Next.js code to ensure optimal performance patterns. Triggers on tasks involving React components, Next.js pages, data fetching, bundle optimization, or performance improvements.
---

# Vercel React Best Practices

Comprehensive performance optimization guide for React and Next.js applications, maintained by Vercel. Contains 45 rules across 8 categories, prioritized by impact to guide automated refacto

### Module: react-bits
---
name: react-bits
description: Production-grade animated, interactive, and customizable React & Next.js components library (216+ components across Text Animations, Backgrounds, UI Components, Micro Interactions, and Animations). Use when the user asks to build animated web interfaces, hero sections, interactive cards, particle/shader backgrounds, cursor trails, or modern micro-interactions in React/Next.js with Tailwind or CSS.
---

# React Bits Component Library

[React Bits](https://www.reactbits.dev) is the largest open-source collection of animated, interactive, and customizable UI comp

### Module: react-component-performance
---
name: react-component-performance
description: Diagnose slow React components and suggest targeted performance fixes.
metadata:
  risk: safe
  source: "Dimillian/Skills (MIT)"
  date_added: "2026-03-25"
---

# React Component Performance

## Overview

Identify render hotspots, isolate expensive updates, and apply targeted optimizations without changing UI behavior.

## When to Use

- When the user asks to profile or improve a slow React component.
- When you need to reduce re-renders, list lag, or expensive render work in React UI.

## Workflow

1. Reproduce or describe the slowdown.
2. Id

### Module: react-dev
---
name: react-dev
version: 1.0.0
description: This skill should be used when building React components with TypeScript, typing hooks, handling events, or when React TypeScript, React 19, Server Components are mentioned. Covers type-safe patterns for React 18-19 including generic components, proper event typing, and routing integration (TanStack Router, React Router).
---

# React TypeScript

Type-safe React = compile-time guarantees = confident refactoring.

<when_to_use>

- Building typed React components
- Implementing generic components
- Typing event handlers, forms, refs
- Using React 1

### Module: react-modernization
---
name: react-modernization
description: Upgrade React applications to latest versions, migrate from class components to hooks, and adopt concurrent features. Use when modernizing React codebases, migrating to React Hooks, or upgrading to latest React versions.
---

# React Modernization

Master React version upgrades, class to hooks migration, concurrent features adoption, and codemods for automated transformation.

## When to Use This Skill

- Upgrading React applications to latest versions
- Migrating class components to functional components with hooks
- Adopting concurrent React feature

### Module: react-native-architecture
---
name: react-native-architecture
description: "Production-ready patterns for React Native development with Expo, including navigation, state management, native modules, and offline-first architecture."
metadata:
  risk: safe
  source: community
  date_added: "2026-02-27"
---

# React Native Architecture

Production-ready patterns for React Native development with Expo, including navigation, state management, native modules, and offline-first architecture.

## Use this skill when

- Starting a new React Native or Expo project
- Implementing complex navigation patterns
- Integrating native mo

### Module: react-native-design
---
name: react-native-design
description: Master React Native styling, navigation, and Reanimated animations for cross-platform mobile development. Use when building React Native apps, implementing navigation patterns, or creating performant animations.
---

# React Native Design

Master React Native styling patterns, React Navigation, and Reanimated 3 to build performant, cross-platform mobile applications with native-quality user experiences.

## When to Use This Skill

- Building cross-platform mobile apps with React Native
- Implementing navigation with React Navigation 6+
- Creating perf

### Module: react-native-expo
---
name: react-native-expo
description: Expo managed workflow, navigation, state management, EAS Build, OTA updates
metadata:
  type: skill
  triggers: ["react native", "expo", "react-native", "mobile react", "eas build", "expo router"]
---

# React Native + Expo

## Setup
```bash
npx create-expo-app MyApp --template
cd MyApp && npx expo start
```

## Expo Router (file-based navigation)
```
app/
  _layout.tsx     # root layout
  index.tsx       # home screen
  (tabs)/
    _layout.tsx   # tab bar layout
    home.tsx
    profile.tsx
  [id].tsx        # dynamic route
```

## State (Zustand)
```t

### Module: react-native-patterns
---
name: react-native-patterns
description: React Native and Expo app patterns — Expo Router navigation, state separation (server/client/route/form), TanStack Query data fetching with Zod, performant lists, NativeWind/StyleSheet styling, native APIs, and secure storage. Use when building or editing React Native / Expo screens, components, navigation, or data layers.
origin: ECC
---

# React Native / Expo Patterns

Practical patterns for building production React Native apps with Expo. Covers navigation, state, data fetching, lists, styling, and native APIs. Pairs with the `rules/react-native/

### Module: react-patterns
---
name: react-patterns
description: React 18/19 patterns including hooks discipline, server/client component boundaries, Suspense + error boundaries, form actions, data fetching, state management decision trees, and accessibility-first composition. Use when writing or reviewing React components.
metadata:
  origin: ECC
---

# React Patterns

Idiomatic React 18/19 patterns for building robust, accessible, performant component trees.

## When to Activate

- Writing or modifying React function components, custom hooks, or component trees
- Reviewing JSX/TSX files
- Designing state shape or comp

### Module: react-performance
---
name: react-performance
description: React and Next.js performance optimization patterns adapted from Vercel Engineering's React Best Practices (https://github.com/vercel-labs/agent-skills). Organizes 70+ rules across 8 priority categories — waterfalls, bundle size, server-side, client fetching, re-render, rendering, JS micro-perf, advanced. Use when writing, reviewing, or refactoring React/Next.js code for performance.
metadata:
  origin: ECC
---

# React Performance

Performance optimization patterns for React 18/19 and Next.js, adapted from [Vercel Labs `react-best-practices`](https://g

### Module: react-spring
---
name: react-spring
description: >-
  A physics-based animation library for React applications.
---

# React Spring

## Overview
A physics-based animation library for React applications.
- **Category**: Frontend

## Best Practices & Workflows
1. Integrate React Spring following standard production patterns.
2. Maintain high reliability and environment configuration.


### Module: react-state-management
---
name: react-state-management
description: "Master modern React state management with Redux Toolkit, Zustand, Jotai, and React Query. Use when setting up global state, managing server state, or choosing between state management solutions."
metadata:
  risk: unknown
  source: community
  date_added: "2026-02-27"
---

# React State Management

Comprehensive guide to modern React state management patterns, from local component state to global stores and server state synchronization.

## Do not use this skill when

- The task is unrelated to react state management
- You need a different domain 

### Module: react-testing
---
name: react-testing
description: React component testing with React Testing Library, Vitest/Jest, MSW for network mocking, accessibility assertions with axe, and the decision boundary between component tests and Playwright/Cypress end-to-end runs. Use when writing or fixing tests for React components, hooks, or pages.
metadata:
  origin: ECC
---

# React Testing

Comprehensive React testing patterns for behavior-focused component tests, custom hook tests, accessibility assertions, and network-level mocking.

## When to Activate

- Writing tests for React components, custom hooks, or pages


### Module: react-ui-patterns
---
name: react-ui-patterns
description: Modern React UI patterns for loading states, error handling, and data fetching. Use when building UI components, handling async data, or managing UI states.
---

# React UI Patterns

## Core Principles

1. **Never show stale UI** - Loading spinners only when actually loading
2. **Always surface errors** - Users must know when something fails
3. **Optimistic updates** - Make the UI feel instant
4. **Progressive disclosure** - Show content as it becomes available
5. **Graceful degradation** - Partial data is better than no data

## Loading State Patterns


### Module: react-useeffect
---
name: react-useeffect
description: React useEffect best practices from official docs. Use when writing/reviewing useEffect, useState for derived values, data fetching, or state synchronization. Teaches when NOT to use Effect and better alternatives.
---

# You Might Not Need an Effect

Effects are an **escape hatch** from React. They let you synchronize with external systems. If there is no external system involved, you shouldn't need an Effect.

## Quick Reference

| Situation | DON'T | DO |
|-----------|-------|-----|
| Derived state from props/state | `useState` + `useEffect` | Calculat

