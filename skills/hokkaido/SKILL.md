---
name: hokkaido
description: Hokkaido 0.7.0 Nintendo Switch 2 Dual-Engine Emulator & Banana Native Execution Architecture for Android. Guide to building, configuring, driver injection (Mesa RADV/Adreno), game profile optimization, and AGENTS.md diagnostic switches.
triggers:
  - hokkaido
  - hokkaido 0.7.0
  - switch 2 emulator
  - banana native
  - lichii
  - xclipse 960
  - radv android
  - nintendo switch 2
category: mobile_dev
---

# Hokkaido 0.7.0 - Nintendo Switch 2 Emulator for Android

Hokkaido (formerly Lichii for Android) is an open-source Nintendo Switch 2 emulator for Android targeting modern ARM64 architecture, Samsung Exynos (AMD Xclipse 940/960 RDNA3), and Qualcomm Snapdragon 8 Elite platforms.

## Core Architectural Innovation in v0.7.0: Dual-Engine

Starting in version 0.7.0, Hokkaido introduces a **Dual-Engine architecture**:
1. **Hokkaido Emulation Engine**:
   - Emulates Switch 2 CPU via Native Code Execution (NCE) and translates GPU calls via Vulkan 1.3.
   - Works across arbitrary Switch 2 titles.
   - Optimal setting: 0.5x resolution for 8-12 GB RAM devices; 1.0x for 16 GB devices.
2. **Banana Native Execution Engine**:
   - Instead of emulation, Banana Native rewrites game binaries once during a "Prepare" phase to execute native ARM64 instructions directly on the phone SoC.
   - Near-zero virtualization overhead; renders through Vulkan using shared GPU driver profiles.
   - Auto-enabled for verified playable titles: *Donkey Kong Bananza*, *Pokemon Pokopia*, *Mario Kart World*, *Fire Emblem: Fortune's Weave*, *Star Fox*.

## Tested Hardware Platforms

| SoC | GPU | Target Device | Recommended Driver |
|---|---|---|---|
| Samsung Exynos 2600 | Samsung Xclipse 960 (RDNA3) | Galaxy S26 | Custom Mesa RADV Xclipse (Mesa 27.0-devel) |
| Samsung Exynos 2400 | Samsung Xclipse 940 (RDNA3) | Galaxy S24 | Custom Mesa RADV build |
| Snapdragon 8 Elite | Qualcomm Adreno 830 | Galaxy S25 | Patched Adreno 8gen V39 |

## Agent Diagnostic & Bug Triage Workflow

Read `references/agents-guide.md` for known program IDs and Lichii/Eden session log structures (`Android/data/dev.lichii.android/files/log/eden_log.txt`).

### Diagnostic Switches (`env.txt`)
Android cannot pass direct environment variables, so Hokkaido reads them from:
`Android/data/<app_id>/files/env.txt` (format: `KEY=VALUE`).

Common switches:
- `EDEN_DUMP_SHADERS=1`: Dumps SPIR-V and translated shaders to disk for debugging.
- `EDEN_FORCE_VULKAN_VALIDATION=1`: Enables Vulkan validation layers.
- `DM_VERBOSE=1`: Enables Banana Native verbose execution logs.

## Building from Source

```bash
cd src/android
./gradlew assembleMainlineRelWithDebInfo
```
Requirements:
- Android SDK & NDK 28.2
- CMake 3.22+
- Output path: `src/android/app/build/outputs/apk/mainline/relWithDebInfo/`
