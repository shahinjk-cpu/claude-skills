---
name: sentry
description: >
  Sentry application monitoring and error triage skill. Inspect stack traces, identify root causes, link regressions to git commits, and automate error issue resolution.
metadata:
  version: "1.0.0"
  category: devops_security
  triggers: sentry, error monitoring, stack trace, bug triage, crash reporting, exception tracking
---

# Sentry — Error Monitoring & Intelligent Bug Triage

Integrates with Sentry to inspect application exceptions, analyze distributed traces, link errors to specific git releases, and resolve issues programmatically.

## Triage Workflow
1. **Issue Identification**: Retrieve issue ID, event count, and user impact frequency.
2. **Stack Trace Examination**: Identify the exact filename and line number where the unhandled exception originated.
3. **Breadcrumbs & Context**: Inspect prior HTTP calls, console logs, and database queries leading up to the crash.
4. **Root Cause Resolution**: Implement a regression test, patch the bug, and mark the Sentry issue resolved.
