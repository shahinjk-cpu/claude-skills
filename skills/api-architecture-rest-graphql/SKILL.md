---
name: api-architecture-rest-graphql
description: >-
  Designs clean, scalable, and well-documented REST, GraphQL, gRPC, and WebSocket APIs.
  Inspired by testmu-ai/api-skill and apollographql/apollo-skills. Use when designing
  backend endpoints, OpenAPI/Swagger specs, GraphQL schemas, or API error contracts.
---

# API Architecture (REST, GraphQL & Real-Time)

Inspired by `testmu-ai/api-skill` and `apollographql/apollo-skills`.

## 1. REST API Design Standards
1. **Consistent Resource Naming & Status Codes**:
   - Use plural nouns (`GET /v1/projects`, `POST /v1/projects`, `PATCH /v1/projects/:id`).
   - Return accurate HTTP codes: `200 OK`, `201 Created`, `204 No Content`, `400 Bad Request` (validation), `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`, `429 Too Many Requests`.
2. **Standardized Error Envelope**:
   ```json
   {
     "error": {
       "code": "VALIDATION_ERROR",
       "message": "Invalid input parameters",
       "details": [{ "field": "email", "issue": "Must be a valid email address" }],
       "requestId": "req_9f8a7b"
     }
   }
   ```
3. **Pagination & Filtering**:
   - Always paginate list endpoints using cursor pagination (`?cursor=...&limit=25`) or bounded offset pagination (`max limit = 100`).

## 2. GraphQL & Real-Time Best Practices
- Prevent $N+1$ query problems in GraphQL resolvers using **DataLoader** batching.
- Enforce query depth and complexity limits to prevent DoS attacks.
- Validate all incoming payloads at the boundary with strict schemas (Zod / Pydantic / JSON Schema).
