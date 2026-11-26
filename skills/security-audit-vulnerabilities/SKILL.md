---
name: security-audit-vulnerabilities
description: Conducts thorough security audits, threat modeling, OWASP Top 10 vulnerability assessments, secret leak detection, and code hardening across web, mobile, backend, and AI/LLM applications. Use when reviewing code for security flaws, fixing SQLi/XSS/CSRF/SSRF/IDOR bugs, auditing APIs, or hardening infrastructure.
---

# Security Audit & Vulnerability Hardening Skill

Comprehensive methodology inspired by Trail of Bits and Cloudflare security engineering standards for auditing codebases, identifying exploitable flaws, and implementing defense-in-depth fixes.

---

## 1. Threat Modeling & Audit Workflow

When asked to audit a project or feature:
1. **Map Trust Boundaries**: Identify where untrusted input enters the system (HTTP headers/params/body, WebSockets, webhooks, uploaded files, LLM user prompts, URL query strings).
2. **Trace Data Sinks**: Follow untrusted data to critical sinks (SQL queries, shell commands, HTML rendering, file system paths, internal HTTP requests, LLM system prompts).
3. **Verify AuthN & AuthZ at Every Boundary**: Never rely on UI hiding or client-side routing; verify session ownership and tenant isolation on every mutation and sensitive query.
4. **Classify Findings**: Report issues with **Severity** (Critical, High, Medium, Low, Informational), **File/Line Reference**, **Exploit Scenario (PoC)**, and **Remediation Code**.

---

## 2. OWASP Top 10 & Modern Vulnerability Checklist

### A. Broken Access Control & IDOR (Insecure Direct Object Reference)
- **Flaw**: Querying resources solely by user-supplied ID (`WHERE id = $1`) without checking `AND user_id = $2` or `organization_id = $2`.
- **Fix**: Enforce ownership in the database query or via PostgreSQL Row-Level Security (RLS). Validate role permissions via centralized middleware.

### B. Injection (SQLi, NoSQLi, Command Injection, Path Traversal)
- **SQL Injection**: Never concatenate strings into SQL (`SELECT * FROM users WHERE email = '${email}'`). Always use parameterized queries (`$1`, `?`) or type-safe ORM query builders.
- **Command Injection**: Never pass user input to `exec()`, `spawn(..., { shell: true })`, or `os.system()`. Use `execFile()` or `subprocess.run([cmd, arg1, arg2], shell=False)`.
- **Path Traversal**: Sanitize filenames using `path.basename(input)` and verify resolved paths stay within the intended root directory:
  ```typescript
  const safePath = path.resolve(UPLOAD_DIR, path.basename(userFilename));
  if (!safePath.startsWith(path.resolve(UPLOAD_DIR) + path.sep)) {
    throw new Error('Path traversal detected');
  }
  ```

### C. Cross-Site Scripting (XSS) & Client-Side Security
- **Flaw**: Using `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, or `javascript:` URLs in `<a href={userUrl}>`.
- **Fix**: Sanitize HTML with `DOMPurify` before rendering; validate that user-supplied URLs start with `https://` or `http://` before rendering in `href`/`src`.
- **CSP (Content Security Policy)**: Configure strict CSP headers (`default-src 'self'; script-src 'self' 'nonce-...'`).

### D. Server-Side Request Forgery (SSRF)
- **Flaw**: Fetching user-provided URLs on the server (e.g., webhook testers, link previews, PDF generators) without blocking internal IP ranges.
- **Fix**: Parse the URL, resolve DNS, and block private/loopback/metadata IP ranges (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254` AWS/GCP metadata endpoint).

### E. Cryptographic & Secret Management Flaws
- Never use `Math.random()` or Python `random` for tokens, OTPs, or IDs. Use CSPRNG (`crypto.randomBytes`, `crypto.randomUUID()`, Python `secrets`).
- Never compare HMAC signatures or tokens with `===`. Use constant-time comparison (`crypto.timingSafeEqual`).
- Scan for hardcoded secrets (`sk_live_`, `AIza`, `ghp_`, `eyJ...`, private keys) and ensure `.env` files are in `.gitignore`.

### F. AI / LLM Security (OWASP LLM Top 10)
- **Indirect Prompt Injection**: Untrusted external content (scraped web pages, RAG documents, emails) must be clearly delimited (e.g., XML tags `<untrusted_context>...</untrusted_context>`) and never given direct execution privileges over high-risk tools (email sending, DB deletion, shell execution) without human-in-the-loop confirmation.
- **Insecure Output Handling**: Never pass raw LLM output directly into `eval()`, SQL execution, or unsanitized HTML rendering.

---

## 3. Essential HTTP Security Headers

Ensure production responses include:
```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```
