---
name: typegpu
description: >-
  TypeScript-first type-safe WebGPU development library for writing typed WGSL compute shaders, render pipelines, and buffer layouts directly in TypeScript.
---

# TypeGPU — TypeScript-First Type-Safe WebGPU

TypeGPU brings TypeScript's strong static type system to GPU compute and graphics rendering using WebGPU.

## Features
- **Type-safe WGSL**: Write shaders with TypeScript syntax validation and intellisense.
- **Zero-cost Buffer Schemas**: Automatically layout uniform and storage buffers with exact WGSL alignment.
- **Composable Pipelines**: Modular shader functions and data structures.

## Quickstart
```typescript
import tgpu from 'typegpu';
import * as d from 'typegpu/data';

// Define buffer layout
const Particle = d.struct({
  position: d.vec3f,
  velocity: d.vec3f,
  life: d.f32,
});

// Create typed GPU buffer
const root = await tgpu.init();
const particleBuffer = root.createBuffer(d.arrayOf(Particle, 10000));

// Type-safe compute shader
const updateParticles = tgpu['~compute']({ workgroupSize: [64] })
  .with(particleBuffer)
  .implement(({ workgroupIndex }) => {
    // WGSL logic with TypeScript intellisense
  });
```
