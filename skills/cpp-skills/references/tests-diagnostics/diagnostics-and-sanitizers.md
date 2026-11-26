# Diagnostics and Sanitizers

## Overview

Recommended runtime diagnostic tools and sanitizers organized by operating system and defect class to catch memory corruption, leaks, data races, and undefined behavior early during development and testing.

## General Practices

- **Keep Sanitizers Isolated When Needed:** Avoid mixing mutually incompatible sanitizers (such as ASan and TSan) in the same binary; use dedicated builds per sanitizer target.
- **Preserve Debug Symbols & Frame Pointers:** Pair sanitizers with debug symbols (`-g` / `/Zi`) and frame pointers (`-fno-omit-frame-pointer` on GCC/Clang) to get accurate stack traces and symbolicated diagnostics.
- **Combine with Compiler Warnings:** Treat sanitizers as a complement to strict warning flags (`-Wall -Wextra -Wpedantic` / `/W4`), not a replacement.

## Linux

- **Address Sanitizer (ASan):** Use `-fsanitize=address` with GCC or Clang to detect heap, stack, and global out-of-bounds accesses, use-after-free, and use-after-return bugs with low overhead compared to Valgrind.
- **Undefined Behavior Sanitizer (UBSan):** Pair `-fsanitize=undefined` with ASan during testing to catch signed integer overflow, misaligned pointers, invalid enum values, and null/shift violations.
- **Thread Sanitizer (TSan):** Use `-fsanitize=thread` with GCC or Clang in dedicated concurrency test runs to detect data races and improper synchronization across threads.
- **Memory & Leak Detection (Valgrind / Memcheck):** Use Valgrind (`memcheck`) on uninstrumented debug builds when you need deep leak analysis or uninitialized value tracking without recompiling with sanitizers.

## Windows

- **Address Sanitizer (MSVC ASan):** Use `/fsanitize=address` with MSVC to catch heap, stack, and global buffer overflows and use-after-scope/use-after-free defects on supported toolsets.
- **Debug Heap & CRT Diagnostics:** Leverage MSVC debug heap checks and runtime assertions alongside ASan to spot allocation mismatches and invalid handle/iterator usage early.
- **Concurrency & Timing Checks:** Isolate multi-threaded stress tests so race conditions and synchronization deadlocks can be reproduced deterministically.

## macOS

- **Address & Undefined Behavior Sanitizers:** Use Apple Clang with `-fsanitize=address` and `-fsanitize=undefined` to detect memory safety violations and undefined behavior during local and CI test runs.
- **Thread Sanitizer (TSan):** Use `-fsanitize=thread` in a separate build configuration to catch data races in concurrent C++ code and `std::thread` / `std::jthread` / task workloads.