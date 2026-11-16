---
name: ghost-security
description: Enterprise Application Security (AppSec) suite for AI agents. Combines Poltergeist (secrets & entropy scanning), Wraith (dependency OSV scanner), Exorcist (AST code vulnerability analyzer), and live exploit validation.
triggers:
- "ghost security"
- "ghost-security"
- "appsec scan"
- "poltergeist scan"
- "wraith scan"
- "exorcist scan"
---

# Ghost Security - Enterprise AppSec AI Engine

Ghost Security gives coding agents the automated tools to discover real security vulnerabilities, validate them, and generate confirmed fixes.

## Modules & Scanners

- **Scan Code (ghost-security/scan-code):** AST and semantic code analysis targeting business logic flaws and OWASP vulnerabilities.
- **Scan Dependencies (ghost-security/scan-deps):** OSV and CVE database correlation for third-party libraries.
- **Scan Secrets (ghost-security/scan-secrets):** High-entropy string detection, leaked API tokens, private keys, and credential patterns.
- **Live Validation (ghost-security/validate):** Safe, non-destructive validation to prove exploitability before reporting.
- **Reporting (ghost-security/report):** Standardized AppSec report generation with remediation diffs.
