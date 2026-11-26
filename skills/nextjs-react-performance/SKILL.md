---
name: nextjs-react-performance
description: >-
  Applies official Vercel and React engineering best practices for Next.js App Router,
  React Server Components, caching, bundle optimization, and eliminating network waterfalls.
  Inspired by vercel-labs/next-best-practices. Use when building or optimizing React
  and Next.js web applications.
---

# Next.js & React Performance Engineering

Inspired by `vercel-labs/next-best-practices` and `next-cache-components`. Use this skill when creating or optimizing React and Next.js applications.

## 1. Server vs. Client Component Architecture
1. **Default to Server Components (RSC)**:
   - Keep data fetching, heavy markdown/syntax parsing, and secrets on the server.
   - Only add `"use client"` at the leaf interactive nodes (buttons, forms, modals, charts), never at the top-level page or layout unless strictly required.
2. **Eliminate Request Waterfalls**:
   - When fetching multiple independent resources in a Server Component or API route, run them in parallel with `Promise.all([fetchA(), fetchB()])` instead of sequential `await` calls.
   - Use `<Suspense fallback={<Skeleton />}>` boundaries to stream slow sections without blocking the initial page shell.

## 2. State & Rendering Optimization
1. **URL State First**:
   - Store search queries, table filters, pagination, and active tabs in URL `searchParams` so views are bookmarkable, shareable, and SSR-compatible.
2. **Avoid `useEffect` Data Fetching**:
   - Prefer Server Components, Server Actions, or TanStack Query / SWR over raw `useEffect(() => { fetch(...) }, [])`.
3. **Bundle & Asset Hygiene**:
   - Lazy-load heavy client libraries (charts, 3D viewers, rich text editors) with `next/dynamic`.
   - Always specify `width`, `height`, or `fill` on images (`next/image`) to prevent Cumulative Layout Shift (CLS).
