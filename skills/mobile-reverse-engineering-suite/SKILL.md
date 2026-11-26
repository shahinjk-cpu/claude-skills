---
name: mobile-reverse-engineering-suite
description: >
  Android & iOS security suite: APK and binary decompilation, Smali analysis, iOS sideloading, dynamic analysis pipeline, and red-team app assessments.
category: devops_security
version: "2.0.0"
role: consolidated_suite
triggers: mobile-reverse-engineering-suite, mobile app reverse engineering & security suite, android-reverse-engineering, apk-redteam-pipeline, apkstart, ios-redteam-pipeline, ios-sideload, reverse-prd
---

# 📱 Mobile App Reverse Engineering & Security Suite

Android & iOS security suite: APK and binary decompilation, Smali analysis, iOS sideloading, dynamic analysis pipeline, and red-team app assessments.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (6 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`android-reverse-engineering`**: Decompile Android APK, XAPK, JAR, and AAR files using jadx or Fernflower/Vineflower. Reverse engineer Android apps, extract HTTP API endpoints (Retrofit, OkHttp, Volley), and trace call flows from UI to network layer. Use when the user wants to decompile, analyze, or reverse engineer Android packages, find API endpoints, or follow call flows. 中文触发词：反编译APK、安卓逆向、提取API、分析安卓应用、反编译安卓、逆向工程、追踪调用链、提取接口
  - *Reference File:* `references/android-reverse-engineering.md`
- **`apk-redteam-pipeline`**: End-to-end Android APK red-team pipeline — automated APK acquisition (Play Store + apkpure + apkmirror fallback), jadx decompilation, secret/URL/JWT/Firebase grep, pinned-cert extraction, exported-component enumeration, Frida runtime instrumentation templates, intent-injection probes. Built from an authorized external red-team engagement where 7 APKs were pulled manually, 4 download attempts truncated, and a hardcoded JWT + 30 internal API endpoints were recovered from one of the apps. Use when target has a mobile app catalogue (Play Store developer page), when you find an APK URL hosted on a web server, or when post-recon mentions "mobile app" in scope.
  - *Reference File:* `references/apk-redteam-pipeline.md`
- **`apkstart`**: Android APK starter kit, reverse engineering, and deployment tool. Disassemble APKs, inspect AndroidManifest.xml, patch smali code, and sign binaries for sideloading.
  - *Reference File:* `references/apkstart.md`
- **`ios-redteam-pipeline`**: End-to-end iOS red-team pipeline — IPA acquisition (App Store extraction, TestFlight, enterprise/ad-hoc sideload), class-dump/Hopper/Ghidra static analysis, Info.plist + entitlements + Keychain secret extraction, App Transport Security (ATS) misconfig + certificate-pinning bypass (frida-ios-dump, objection, SSL Kill Switch 2), URL-scheme / Universal Link hijack, exported-service enumeration, Frida runtime instrumentation. Companion to apk-redteam-pipeline for the iOS side of a mobile app catalogue. Use when target has an iOS app (App Store listing, TestFlight link, enterprise MDM distribution), when an IPA URL is found hosted on a web server, or when post-recon mentions "iOS app" / "mobile app" in scope alongside an Apple developer account.
  - *Reference File:* `references/ios-redteam-pipeline.md`
- **`ios-sideload`**: Sideload, install, and manage iOS apps (.ipa) on iPhone and iPad from Windows using pymobiledevice3, Sideloadly, and AltServer.
  - *Reference File:* `references/ios-sideload.md`
- **`reverse-prd`**: Reverse-engineers an existing, legacy or multi-stack application (e.g. PrestaShop + Laravel hybrid, NestJS services, several services sharing data) into an audited Reverse-PRD — cross-evidenced business rules, Mermaid state machines and sequence diagrams, invariant and failure-mode audit of money flows, Gherkin scenarios. Use when asked for a reverse PRD, a functional audit of payment / payout / commission / refund flows, or product documentation of an undocumented system.
  - *Reference File:* `references/reverse-prd.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `android-reverse-engineering`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
