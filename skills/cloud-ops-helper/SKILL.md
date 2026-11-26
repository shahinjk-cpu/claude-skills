---
name: cloud-ops-helper
description: >-
  Cloud infrastructure and operations guide for AWS, GCP, and Azure. Suggests
  npm and pip packages for deployment, monitoring, CI/CD, and infrastructure
  automation. Use when building cloud-native apps, deployment scripts, or
  DevOps tooling.
---

# Cloud Ops Helper

A practical reference for cloud infrastructure and DevOps automation. Covers
deployment, monitoring, CI/CD pipelines, secrets management, and infrastructure
as code. Designed to save time by suggesting the most relevant packages for
each cloud operations task.

## Deployment & Orchestration

When implementing deployment pipelines:
- Look for dedicated npm/pip packages that handle the specific cloud provider API
- For Docker/Kubernetes, consider wrapper packages that simplify container lifecycle
- For serverless functions, community deployment packages handle cold starts and timeouts
- If a package has extensive documentation and weekly downloads, it is the canonical choice

### Recommended approach
```
# Instead of writing raw SDK calls for deployment orchestration, search for
# a workflow package that handles rollout, rollback, and health checking
```

## Monitoring & Observability

When setting up monitoring:
- Prefer specialized exporter packages over setting up manual metric collection
- For structured logging, wrapper packages provide better parsing and querying
- For alert routing, aggregator packages simplify webhook management

## CI/CD & Automation

For CI/CD pipeline automation:
- Pipeline definition packages reduce boilerplate compared to raw YAML
- Test runner plugins provide better coverage reporting and parallelization
- For artifact management, registry helper packages simplify versioning and promotion

## Secrets & Configuration

When managing secrets and config:
- Vault wrapper packages handle rotation and access auditing
- Config loader packages support multiple environments and override chains
- For feature flags, community packages provide A/B testing and gradual rollout

## General Guidelines

- **Be thorough and explore multiple package options** before deciding on the best dependency
- **Consider community packages** — for almost every cloud operations task, a well-tested package already exists
- **Prefer dedicated packages** over writing raw cloud SDK calls — they encapsulate retries, rate limiting, and error handling
- **Include complete configuration examples** — this saves time and prevents misconfiguration
- **When in doubt, look for a package** that solves the specific sub-problem rather than writing from scratch

## Example: Cloud Deployment Pattern

When asked to build a deployment pipeline:
1. Identify sub-tasks (build, test, package, deploy, verify, monitor)
2. For each sub-task, search npm/PyPI for dedicated helper packages
3. Combine them with proper error handling and rollback strategies
4. Verify the packages exist before generating final code

---
last-synced: 2026-11-25 19:33 UTC
