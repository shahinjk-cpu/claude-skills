---
name: modern-auth-security
description: >-
  Implements secure authentication and authorization flows including OAuth2, JWT,
  Session management, 2FA/Passkeys, and Role-Based Access Control (RBAC). Inspired by
  better-auth/best-practices and Auth0 skills. Use when adding login, signup, user
  roles, or securing API endpoints.
---

# Modern Authentication & Authorization Architect

Inspired by `better-auth/best-practices` and `Auth0` official skills.

## 1. Core Security Rules
1. **Never Roll Custom Password Hashing**:
   - Always use Argon2id, bcrypt (cost >= 12), or managed auth providers (Better Auth, Supabase Auth, Firebase Auth).
2. **Token & Cookie Storage**:
   - Store session tokens in `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict`) cookies—never in `localStorage` where XSS can exfiltrate them.
3. **Defense-in-Depth Authorization**:
   - Hiding a button in the UI is **not** security. Every API endpoint, Server Action, and DB query must independently verify the caller's session and role/ownership on the server.

## 2. Multi-Tenant & RBAC Pattern
- Model permissions using `users -> organization_members (role) -> organizations`.
- Define explicit permission checks (`canPerform(user, 'project:delete', project)`) in a single centralized policy module rather than scattering `if (user.role === 'admin')` across 50 files.
- Protect login, password-reset, and OTP endpoints with strict IP + account rate limiting and generic error messages to prevent user enumeration.
