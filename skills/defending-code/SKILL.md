---
name: defending-code
description: Official Anthropic defensive engineering reference harness. Threat modeling, vulnerability scanning (/vuln-scan), triaging, automated patch generation (/patch), and fix verification for securing local codebases.
triggers:
- "defending code"
- "defending-code"
- "threat modeling"
- "vuln-scan"
- "secure patch"
---

# Defending Code - Defensive Engineering & Threat Modeling

Defending Code provides structured, disciplined workflows for finding and patching vulnerabilities in source code safely.

## Workflow Phases

1. **Threat Model:** Map trust boundaries, external attack surfaces, and high-risk components.
2. **Vulnerability Scan (/vuln-scan):** Scan source files with focus on real attacker exploits and boundary crossings.
3. **Triage:** Filter false positives; verify concrete impact on confidentiality, integrity, or availability.
4. **Patch (/patch):** Produce minimal, robust, defensive patches that preserve functional correctness.
5. **Verify:** Test and validate that the patch eliminates the vulnerability without regressing tests.
