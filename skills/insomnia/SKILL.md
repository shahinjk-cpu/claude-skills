---
name: insomnia
description: >
  REST and GraphQL API testing, debugging, and mock client integration. Manage Insomnia request collections, environment variables, authentication chains, and automated API specs.
metadata:
  version: "1.0.0"
  category: backend_api
  triggers: insomnia, api testing, graphql client, rest client, request collection
---

# Insomnia — API Design & Testing Orchestrator

Integrates with Insomnia API collections, test suites, and environment definitions to design, debug, and validate REST, GraphQL, gRPC, and WebSocket endpoints.

## Capabilities
- **Collection Management**: Import and export Insomnia v4/v5 YAML/JSON workspaces.
- **Environment Chaining**: Dynamic chaining of OAuth tokens, session IDs, and response headers.
- **Inso CLI Automation**: Run API tests in headless CI/CD environments.

## Inso CLI Command Reference
```bash
# Run all tests in an Insomnia workspace
inso run test "My API Test Suite"

# Lint an OpenAPI spec against spectral rules
inso lint spec "Swagger Spec"
```
