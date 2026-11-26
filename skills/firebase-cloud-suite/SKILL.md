---
name: firebase-cloud-suite
description: >
  Full Firebase backend suite: Firestore database design, Authentication, Storage, Cloud Functions, Hosting, Security Rules auditing, Crashlytics, and Remote Config.
category: backend_api
version: "2.0.0"
role: consolidated_suite
triggers: firebase-cloud-suite, firebase cloud architecture & security suite, firebase, firebase-ai-logic-basics, firebase-app-hosting-basics, firebase-auth-basics, firebase-basics, firebase-crashlytics, firebase-data-connect, firebase-firestore, firebase-hosting-basics, firebase-remote-config-basics, firebase-security-rules-auditor
---

# 🔥 Firebase Cloud Architecture & Security Suite

Full Firebase backend suite: Firestore database design, Authentication, Storage, Cloud Functions, Hosting, Security Rules auditing, Crashlytics, and Remote Config.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (10 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`firebase-ai-logic-basics`**: Official skill for integrating Firebase AI Logic (Gemini API) into web applications. Covers setup, multimodal inference, structured output, and security.
  - *Reference File:* `references/firebase-ai-logic-basics.md`
- **`firebase-app-hosting-basics`**: - Deploys and manages full-stack web applications (Next.js, Angular) with Server-Side Rendering (SSR) using Firebase App Hosting. Use when deploying Next.js/Angular apps, configuring apphosting.yaml or firebase.json apphosting blocks, managing secrets, setting up GitHub CI/CD, or configuring Blaze billing requirements. Don't use for classic static web hosting, Auth, Firestore, Crashlytics, or Xcode.
  - *Reference File:* `references/firebase-app-hosting-basics.md`
- **`firebase-auth-basics`**: Guide for setting up and using Firebase Authentication. Use this skill when the user's app requires user sign-in, user management, or secure data access using auth rules.
  - *Reference File:* `references/firebase-auth-basics.md`
- **`firebase-basics`**: - Provides foundational Firebase CLI setup, CLI installation, version checks (`firebase-tools@latest --version`), CLI login (including --no-localhost), project creation, project selection (`firebase use`), and app config file downloads (`google-services.json`, `GoogleService-Info.plist`). Use ONLY for CLI login, project creation/switching, or downloading app config files. Don't use for Firebase Hosting deploy, Firestore, Auth, App Hosting, Data Connect, Crashlytics, or Remote Config.
  - *Reference File:* `references/firebase-basics.md`
- **`firebase-crashlytics`**: Comprehensive guide for Firebase Crashlytics, including provisioning and SDK usage. Use this skill when the user needs help setting up Crashlytics, adding crash reporting, or using the Crashlytics SDK in their application.
  - *Reference File:* `references/firebase-crashlytics.md`
- **`firebase-data-connect`**: Builds and deploys Firebase SQL Connect (aka Firebase Data Connect) backends with PostgreSQL securely. Use when designing schemas with tables and relations, writing authorized queries and mutations, configuring real-time data updates, or generating type-safe SDKs. Use when you need a relational database with Firebase, or when the user mentions SQL Connect or Data Connect.
  - *Reference File:* `references/firebase-data-connect.md`
- **`firebase-firestore`**: - Sets up, manages, queries, and configures Cloud Firestore databases (Standard/Enterprise edition), including data modeling, security rules, indexes, and SDK integrations (Web, Python, iOS, Android, Flutter). Use when creating/listing Firestore databases, defining data models/indexes, writing SDK queries, or integrating Firestore SDKs. For authoring or modifying Firestore Security Rules (firestore.rules), delegate to the firestore-rules-author subagent if subagent delegation is available, or use firestore-rules-creation otherwise. Don't use for Firebase Hosting, Data Connect, Auth, Storage/GCS, Crashlytics, Functions, or BigQuery.
  - *Reference File:* `references/firebase-firestore.md`
- **`firebase-hosting-basics`**: - Deploys and configures classic Firebase Hosting for static websites, single-page apps (SPAs), and microservices. Use when deploying static sites/SPAs, setting up custom domains, configuring firebase.json hosting settings (redirects, rewrites, headers, multi-site), or managing preview channels. Don't use for Firebase App Hosting (Next.js/SSR), Auth, Firestore queries/rules, Data Connect, or Crashlytics.
  - *Reference File:* `references/firebase-hosting-basics.md`
- **`firebase-remote-config-basics`**: - Manages Firebase Remote Config templates, feature flags, loading strategies, and SDKs (Android, iOS). Use when downloading/deploying remoteconfig JSON templates, managing version history/feature flags, setting in-app defaults, fetchAndActivate(), real-time listeners, or SDK setup. Don't use for Firebase Hosting, Auth, Firestore, Data Connect, Crashlytics, or App Hosting.
  - *Reference File:* `references/firebase-remote-config-basics.md`
- **`firebase-security-rules-auditor`**: - Audits Firebase (Firestore, Cloud Storage) security rules for vulnerabilities, privilege escalation, role bypasses, create vs update inconsistencies, resource exhaustion, type safety, size limits, and hasOnly ownership checks. Use when auditing/reviewing rules, running red-team rule assessments, or scoring against auditor checklists. Don't use for Firebase CLI (login, deploy), Auth, Crashlytics, Remote Config, or database queries.
  - *Reference File:* `references/firebase-security-rules-auditor.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `firebase-ai-logic-basics`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
