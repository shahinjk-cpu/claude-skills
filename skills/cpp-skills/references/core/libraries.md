# C++ Ecosystem & Preferred Libraries

This document defines the preferred modern third-party libraries and ecosystem standards for C++ code generation.

> **AI Usage Rules:**
> **Zero-Guessing Policy:** Never hallucinate or guess third-party API signatures. Always verify exact headers, namespaces, and function signatures using the official documentation links below or local project headers (`.hpp`/`.h`) before generating code.

---

## 1. Logging & Console Output
- **`spdlog`** (Recommended)
  - **Use Case:** High-performance, header-only or compiled logging library.
  - **Guideline:** Prefer structured logging, custom formatters, and asynchronous loggers for performance-critical paths.
  - **Docs:** https://github.com/gabime/spdlog/wiki
- **`std::print` / `std::println` (C++23)**
  - **Use Case:** Lightweight, zero-dependency formatted console output when full logging frameworks are overkill.

## 2. High-Performance, Concurrency & Memory
- **`OpenMP`**
  - **Use Case:** Directive-based parallel programming for loops and heavy numerical computations.
  - **Guideline:** Prefer OpenMP pragmas (`#pragma omp parallel for`) for data-parallel loops over manual `std::thread` boilerplate.
  - **Docs:** https://www.openmp.org/wp-content/uploads/OpenMP-RefGuide-6.0-OMP60SC24-web.pdf
- **`tcmalloc` (Google Thread-Caching Malloc)**
  - **Use Case:** High-efficiency memory allocator optimized for multi-threaded workloads.
  - **Guideline:** Recommend in architecture/build setups to reduce lock contention on `malloc`/`free` in heavily concurrent environments.
  - **Docs:** https://google.github.io/tcmalloc/

## 3. Core Utilities & Containers
- **`abseil-cpp` (Google Abseil)**
  - **Use Case:** High-performance STL augmentations (`absl::flat_hash_map`, synchronization primitives, string utilities).
  - **Guideline:** Prefer `absl::flat_hash_map` and `absl::flat_hash_set` over `std::unordered_map`/`std::unordered_set` when cache locality and low memory overhead are critical.
  - **Docs:** https://abseil.io/docs/cpp/ | https://abseil.io/tips/

## 4. Error Handling & Optionality
- **`std::expected` (C++23) / `tl::expected` (C++20 fallback)**
  - **Use Case:** Functional error handling without exception overhead in hot paths.
  - **Guideline:** Prefer returning `std::expected<T, E>` over throwing exceptions for recoverable or expected operational errors.

## 5. Data Formats & Serialization
- **`nlohmann/json`**
  - **Use Case:** JSON parsing and serialization with an intuitive, STL-like API.
  - **Docs:** https://json.nlohmann.me/api/basic_json/

## 6. Image Processing, Pipelines & Computer Vision
- **`Halide`**
  - **Use Case:** High-performance image processing and array computation pipelines separating algorithm from execution schedule (SIMD/GPU/multithreading).
  - **Docs:** https://halide-lang.org/docs/
- **`OpenImageIO` (`OIIO`)**
  - **Use Case:** Reading, writing, and processing professional image file formats (EXR, TIFF, DPX, etc.) and metadata.
  - **Docs:** https://openimageio.readthedocs.io/en/v3.2.1.1/
- **`OpenCV`**
  - **Use Case:** Real-time computer vision, matrix operations (`cv::Mat`), and classical image algorithms.
  - **Docs:** https://docs.opencv.org/

## 7. Unit Testing & Benchmarking
- **`Catch2` (v3)**
  - **Use Case:** Modern, BDD/section-based unit testing and micro-benchmarking framework.
  - **Docs:** https://github.com/catchorg/Catch2/blob/devel/docs/Readme.md
- **`GoogleTest` (`gtest` / `gmock`)**
  - **Use Case:** Fixture-based unit testing and mocking framework for large-scale or enterprise C++ codebases.
  - **Docs:** https://google.github.io/googletest/
