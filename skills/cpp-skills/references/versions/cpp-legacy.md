# Legacy Code, C Interop & Modernization Reference

## Overview
Guidelines for maintaining legacy C++ codebases, safely crossing C/C++ boundaries, and executing incremental modernization passes without destabilizing existing behavior.

## Modernization Strategy & Priority Order
- **Incremental Scope**: Apply modernizations only to code already touched in a change, separating mechanical passes (such as `clang-tidy` `modernize-*` fixes) from behavioral changes. Avoid gratuitous churn or silently bumping the project C++ standard.
- **Triage Order**:
  1. Memory errors and undefined behavior flagged by sanitizers.
  2. Manual `new`/`delete`, owning raw pointers, and ad-hoc cleanup paths (migrate to RAII).
  3. C-style casts and unchecked conversions (migrate to named casts or stronger types).
  4. Preprocessor macros used for constants, functions, or enums (migrate to `constexpr`, templates, or `enum class`).
  5. Raw loops and index math over ranges/buffers (migrate to algorithms, `std::span`, or `std::ranges`).
  6. Out-parameters and sentinel values (migrate to return values, `std::optional`, or `std::expected`).
  7. Formatting and naming conventions, applied last and mechanically.

## Safe Practices in Legacy Codebases
- **Characterization & Gradual Wrapping**: Add characterization tests capturing current behavior (including quirks) before editing. Wrap legacy components behind modern interfaces and migrate callers incrementally rather than performing big-bang rewrites.
- **Style Consistency & Hygiene**: Match local style within a file rather than mixing conflicting conventions; separate moves, renames, and logic edits for clean reviews; remove dead code rather than maintaining unused paths; and never silence tests, assertions, or sanitizers to mask failures.

## Calling C from C++
- **RAII Wrappers & Lifetimes**: Wrap C resources and loaded libraries in RAII handles immediately at the boundary (using custom deleters or dedicated RAII structs for non-pointer handles, and favoring leaking over unsafe unload ordering when teardown sequencing is ambiguous). Convert pointer-plus-length pairs to `std::span` right at the boundary.
- **Exceptions, Callbacks & Global State**: Translate all C return codes once into the project's error model, never let C++ exceptions cross a C ABI or callback boundary, and ensure trampoline `void*` context targets outlive registration. Keep `pthread_cancel` out of C++ stack frames, use `std::out_ptr` / `std::inout_ptr` (C++23) or scoped adoption for `T**` outputs, match exact C integer widths/signedness, and follow embedding rules (such as header ordering, lock discipline, and safe object exposure) for global-state C runtimes like CPython.

## Exposing C++ via a C ABI & Mixed Builds
- **C ABI Boundaries**: Export functions with `extern "C"`, use C-compatible types only, prohibit throwing across the ABI, expose stateful objects via opaque handles with explicit creation/destruction functions, document ownership transfer clearly, and avoid exposing types whose layout varies with standard library versions.
- **Shared Headers & Language Rules**: Guard shared headers with `#ifdef __cplusplus` and `extern "C"`, verify layout assumptions (`is_trivially_copyable`, `is_standard_layout`, padding/alignment) with `static_assert`, respect differences between C and C++ (`const`, unions, `void*` conversions), and link binaries with the C++ driver whenever C++ translation units are present.

## Testing `abort()` Paths
- **Platform & Sanitizer Gates**: Guard `abort()` tests strictly on the required OS/libc/platform features rather than broad exclusions, and handle sanitizer/leak-checker behavior properly (including disabling leak checks in forked child processes when needed).
- **Assertions & Test Organization**: Assert on the `abort()` signal/exit status rather than exact diagnostic text across C runtime versions, and keep gated abort tests inside the standard unit-test target so supported environments run them automatically.
