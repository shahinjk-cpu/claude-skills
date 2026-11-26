# 🐝 BeeSting

**A Claude Code skill for auditing and hardening "static frontend + Supabase + Vercel" sites.**

A Supabase project's URL and anon key are public. Anyone can open the browser console and call anything the `anon` and `authenticated` roles are allowed to, bypassing your site. BeeSting teaches the agent to find these holes in the database, close them with a migration, test the SQL locally before it goes to production, and bring the frontend up to a strict Content Security Policy.

> The skill's instructions and reference docs are written in Russian. Claude reads them fine and answers in the user's language.

## What's inside

| | |
|---|---|
| `SKILL.md` | The workflow: map the project → audit → fix with a migration → verify → hand off to the database owner |
| `references/supabase-audit.md` | Checklist for RLS, grants, SECURITY DEFINER functions, views, realtime, business logic and client code, plus a migration template |
| `references/sql-verification.md` | How to test migrations on the local harness and write "owner can / stranger can't" scenarios |
| `references/csp-sri.md` | Strict CSP without `unsafe-inline`, `script-src-attr 'none'`, SRI, security headers, rollout via Report-Only |
| `references/turnstile-gate.md` | Anti-spam: Cloudflare Turnstile + an Edge Function gate + a lock migration, rollout order and rollback |
| `references/staff-mfa.md` | Staff 2FA (TOTP via Supabase MFA) enforced in the database with an `aal2` check |
| `scripts/pg-harness/` | Supabase-like Postgres 17 (embedded): roles, `auth.uid()` / `auth.jwt()`, default privileges, a permissions audit and test scenarios |
| `scripts/csp_scan.mjs` | Finds everything that blocks a strict CSP: inline scripts, `on*` attributes, `javascript:` URLs, CDN scripts without SRI |
| `scripts/sri.sh` | SRI hashes for CDN files |
| `assets/` | Templates: `turnstile-gate.ts` (Edge Function) and `staff-mfa.js` (2FA screen for an admin panel) |
| `evals/` | 3 test cases on a training project with planted vulnerabilities, plus a database grader |

## Installation

```bash
git clone https://github.com/stingersonx228/BeeSting.git ~/.claude/skills/beesting
```

The skill triggers on its own when the project uses Supabase and you ask for something like "check our security", "fix RLS", "lock this RPC away from anon", "set up a proper CSP", "add a captcha to orders" or "enable 2FA for the admin panel". You can also invoke it explicitly with `/beesting`.

The harness needs Node.js 18+ and npm. It installs into a temporary folder, so nothing ends up in your project:

```bash
cp -r ~/.claude/skills/beesting/scripts/pg-harness /tmp/pgh && sh /tmp/pgh/setup.sh
node /tmp/pgh/harness.mjs --repo ./my-site                                   # migration order from DEPLOY.md / README.md
node /tmp/pgh/harness.mjs --repo ./my-site --twice fix.sql --scenario checks.mjs
node ~/.claude/skills/beesting/scripts/csp_scan.mjs ./my-site
```

Sample harness report (the tool prints in Russian; translated here):

```
✓ applied schema.sql
✓ applied promo.sql
⚠ Tables in public without RLS: 1
   - staff (anon: select+write)
⚠ SECURITY DEFINER without set search_path: 2
⚠ Functions callable via /rest/v1/rpc (review each one): 3
   - mark_paid(bigint) — anon+authenticated, via PUBLIC, DEFINER, no identity check
⚠ Views without security_invoker readable by anon/authenticated (bypass RLS): 1
```

## Benchmark

Three tasks on a training pizzeria site, one run each with and without the skill (Claude Opus):

| Task | With skill | Without |
|---|---|---|
| Security audit | 10/10 | 9/10 |
| Fix migration with verification | 11/11 | 10/11 |
| Strict CSP | 7/8 | 6/8 |
| **Total** | **96%** | **85%** |

With the skill, the agent confirms attacks on the harness instead of only reading the code. It also catches lazy supabase-js calls that are never `await`ed (so the request is never sent), hands over the full SQL for the SQL Editor, and includes a rollback script and a rollout order.

## Principles

- Security lives in the database. Checks in JavaScript are only for convenience.
- Applied migrations are never edited: fixes go into a new idempotent file.
- Before handoff, every SQL change runs on the harness after all previous migrations, then a second time, then against the test scenarios.
- Every rollout step leaves the site working and has a rollback.
- Nothing touches production unless explicitly requested.

## License

[MIT](LICENSE)
