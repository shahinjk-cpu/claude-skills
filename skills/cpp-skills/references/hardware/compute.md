# Hardware Acceleration & Low-Level Compute Reference

## Overview

Guidelines for exploiting modern hardware capabilities in C++23, covering CPU vectorization (SIMD), cache-friendly memory access, and heterogeneous GPU compute offloading.

## CPU Optimization & Vectorization (SIMD)

* **Portable SIMD (`std::experimental::simd` / C++26 `std::simd`)**: Prefer standard portable data-parallel types (`std::simd`, `std::simd_mask`) over raw platform intrinsics to write cross-architecture vectorized algorithms (AVX2, AVX-512, ARM NEON) cleanly.
* **Auto-Vectorization Friendly Loops**: Write simple, contiguous loops without loop-carried dependencies, pointer aliasing (use `__restrict` where validated), or complex branching so compilers can auto-vectorize effectively (`-O3 -march=native`).
* **Explicit Intrinsics & Libraries**: When hardware-specific instructions are required, encapsulate intrinsics (`<immintrin.h>`, `<arm_neon.h>`) behind clean abstraction layers or use portable libraries like **Highway** or **EVE**.
* **Memory Alignment & Cache Lines**: Align hot data buffers to SIMD register widths or cache-line boundaries (`alignas(64)` / `std::hardware_destructive_interference_size`) to prevent split loads and false sharing across cores.
* **Parallel Execution Policies**: Leverage `<execution>` policies (`std::execution::par_unseq`) with standard algorithms (`std::transform`, `std::reduce`) to combine multi-core threading with SIMD vectorization.

## GPU Compute & Heterogeneous Offloading

* **Portable Compute Frameworks**: Prefer cross-platform abstractions such as **SYCL**, **Kokkos**, **Halide**, or **Vulkan Compute** when targeting multi-vendor GPUs (NVIDIA, AMD, Intel, Apple Silicon).
* **Vendor-Specific Kernels**: Use **CUDA** (NVIDIA), **HIP** (AMD), or **Metal** (Apple) when maximum low-level hardware throughput, tensor cores, or vendor-specific libraries (cuBLAS, rocBLAS) are required.
* **Host-Device Memory Management**:
  * Minimize PCIe / host-to-device memory transfers by batching workloads and keeping persistent buffers on device memory.
  * Use pinned (page-locked) host memory or Unified/Shared Memory (`cudaMallocManaged` / Apple Unified Memory) carefully to overlap data transfers with kernel execution via asynchronous streams/queues.
* **Kernel Execution & Occupancy**:
  * Structure memory accesses for **coalesced global memory reads/writes** across warps/wavefronts.
  * Leverage fast on-chip **shared/local memory** for data reuse and minimize thread divergence within warps.