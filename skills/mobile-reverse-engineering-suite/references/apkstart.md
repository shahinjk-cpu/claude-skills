---
name: apkstart
description: >
  Android APK starter kit, reverse engineering, and deployment tool. Disassemble APKs, inspect AndroidManifest.xml, patch smali code, and sign binaries for sideloading.
metadata:
  version: "1.0.0"
  category: mobile_dev
  triggers: apkstart, android apk, reverse engineer apk, decompile apk, smali, sign apk
---

# APKStart — Android Package Inspection & Scaffold Toolkit

Toolkit for inspecting, decompiling, analyzing, modifying, and rebuilding Android APK packages.

## Core Commands
```bash
# Decompile APK to smali and resources
apktool d target.apk -o ./decompiled/

# Rebuild modified APK
apktool b ./decompiled/ -o ./patched.apk

# Align and sign APK with debug keystore
zipalign -v 4 patched.apk aligned.apk
apksigner sign --ks ~/.android/debug.keystore aligned.apk
```
