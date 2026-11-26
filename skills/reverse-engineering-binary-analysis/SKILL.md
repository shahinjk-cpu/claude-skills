---
name: reverse-engineering-binary-analysis
description: Analyzes, deconstructs, and reverse-engineers compiled binaries, minified/obfuscated JavaScript bundles, WebAssembly modules, Android APKs, desktop executables, and undocumented network protocols/APIs. Use when inspecting third-party bundles, recovering lost source logic, analyzing API traffic, or auditing binary behavior.
---

# Reverse Engineering & Binary/Bundle Analysis Skill

Structured methodology for analyzing compiled artifacts, obfuscated JavaScript/TypeScript bundles, mobile packages (APK/IPA), and undocumented network protocols safely and systematically.

---

## 1. Core Principles & Safety

1. **Static First, Dynamic Second**: Always inspect headers, strings, symbols, imports, and AST structures statically before executing unknown binaries.
2. **Sandbox Isolation**: Never run untrusted executables directly on the host OS without verifying their imports and network targets.
3. **Evidence-Driven Mapping**: Document entrypoints, control-flow graphs, cryptographic routines, and API schemas in structured markdown tables as you uncover them.

---

## 2. JavaScript / Webpack / Vite Bundle De-obfuscation

When analyzing minified or bundled web/Electron applications:

### Step 1: Check for Source Maps
- Inspect the end of `.js` and `.css` files for `//# sourceMappingURL=...`.
- If `.map` files are available, extract the original directory tree (`sources` and `sourcesContent` fields in the JSON map).

### Step 2: AST Formatting & Module Extraction
- Format minified code using Prettier or `js-beautify`.
- Identify bundler signatures:
  - **Webpack**: `__webpack_require__`, `webpackChunk...`
  - **Vite / Rollup**: ES module exports or IIFE wrappers
  - **Metro (React Native)**: `__d(function(global, _$$_REQUIRE, ...), moduleId, [deps])`
- Locate key anchors using high-signal string searches:
  - API Base URLs: `https://api.`, `/v1/`, `graphql`, `Authorization`, `Bearer`
  - Crypto/Signing keys: `HMAC`, `SHA-256`, `crypto.subtle`, `sign(`, `encrypt(`
  - State stores: `createSlice`, `zustand`, `dispatch({ type:`

---

## 3. Undocumented Network Protocol & API Analysis

When reconstructing an undocumented REST, GraphQL, WebSocket, or gRPC-Web API:

1. **Authentication Flow Reconstruction**:
   - Identify token acquisition endpoints (OAuth2 PKCE, custom JWT challenge, session cookies, CSRF header requirements).
   - Check custom request signing headers (e.g., `X-Signature`, `X-Timestamp`, `X-Nonce`) and trace their generation in client code.
2. **Protobuf / Binary Payload Decoding**:
   - Look for `application/x-protobuf`, `application/grpc-web+proto`, or binary WebSocket frames.
   - Extract `.proto` descriptor definitions from bundled client code (`FieldDescriptorProto`, `MessageOptions`) or decode raw wire types (Varint `0`, 64-bit `1`, Length-delimited `2`, 32-bit `5`).

---

## 4. Desktop & Mobile Binary Triage (PE / ELF / Mach-O / APK)

### A. Initial File Identification & Strings
- Check magic bytes (`MZ` for Windows PE, `\x7fELF` for Linux, `\xcf\xfa\xed\xfe` for Mach-O, `PK\x03\x04` for APK/ZIP/JAR).
- Extract ASCII and UTF-16LE strings to identify compiler toolchains (Rust `rustc`, Go `go.buildid`, Electron `asar`, Flutter `libapp.so` + `libflutter.so`, .NET CLR).

### B. Framework-Specific Unpacking
- **Electron Apps**: Locate `resources/app.asar`. Extract or inspect the archive header (JSON index of file offsets) to read the main and renderer process code.
- **Android APKs**: Unzip APK -> inspect `AndroidManifest.xml`, `classes.dex` (via `jadx` / `dex2jar`), and native libraries in `lib/arm64-v8a/`.
- **Python Frozen Binaries (PyInstaller)**: Locate the `MEI` archive magic at the end of the executable, extract `.pyc` files, and inspect bytecode/constants.
- **.NET Assemblies**: Inspect IL metadata, class hierarchies, and decompiled C# methods using `ilspycmd` or `dnSpy` patterns.
