---
name: bigquery-cloud-suite
description: >
  Enterprise data warehouse suite: BigQuery SQL optimization, Data Transfer Service, BigFrames Python dataframe, AI/ML integration, graph queries, and performance troubleshooting.
category: database_storage
version: "2.0.0"
role: consolidated_suite
triggers: bigquery-cloud-suite, google cloud bigquery analytics suite, bigquery, bigquery-ai-ml, bigquery-bigframes, bigquery-data-transfer-service, bigquery-graph-author, bigquery-graph-query, bigquery-observability, bigquery-optimization, bigquery-troubleshooting
---

# 📊 Google Cloud BigQuery Analytics Suite

Enterprise data warehouse suite: BigQuery SQL optimization, Data Transfer Service, BigFrames Python dataframe, AI/ML integration, graph queries, and performance troubleshooting.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (8 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`bigquery-ai-ml`**: - Leverages BigQuery's built-in machine learning and GenAI capabilities for advanced data analytics. Use when you need to write SQL queries that perform time-series forecasting, predict values, detect outliers or anomalies, find key drivers, perform semantic search or vector search, classify text, calculate similarity, summarize content, translate language, evaluate models, filter by semantic conditions, measure the causal effect of an intervention, compute correlations between columns, generate descriptive statistics and table distribution profiles, detect change points or structural breaks, extract trend or seasonality components, or leverage generative AI capabilities in BigQuery. Do not use for general BigQuery dataset, table, or job management requests.
  - *Reference File:* `references/bigquery-ai-ml.md`
- **`bigquery-bigframes`**: - Generates Python code using BigQuery DataFrames (BigFrames). Use by default for any Python data task involving BigQuery, including data processing, analysis, and machine learning. Don't use for SQL-first workflows or the google-cloud-bigquery client library — use bigquery-basics. --- # BigFrames (BigQuery DataFrame) basics
  - *Reference File:* `references/bigquery-bigframes.md`
- **`bigquery-data-transfer-service`**: Discovers and inspects BigQuery Data Transfer Service (DTS) configurations. Use this to identify existing ingestion pipelines and extract datasource or transfer config metadata for data pipelines. Use when a user asks for ingestion scenarios while building or managing data pipelines or when a user asks to "ingest" or "add" data that may already be managed by a DTS transfer.
  - *Reference File:* `references/bigquery-data-transfer-service.md`
- **`bigquery-graph-author`**: - Provides an end-to-end journey for authoring a BigQuery property graph from your tables or from a model document/diagram (an ER diagram, an ontology, a semantic model): dataset discovery, candidate relationships verified against the data, a readable plan, and `CREATE PROPERTY GRAPH` DDL with schema best practices and semantic measures/dimensions, plus an opt-in verification suite for the landed graph. Use when creating or replacing a property graph, authoring a graph from a dataset or a document, or verifying relationships or suspicious edge counts. Don't use for querying an existing graph, for non-BigQuery graph databases, or for drawing/rendering diagrams.
  - *Reference File:* `references/bigquery-graph-author.md`
- **`bigquery-graph-query`**: - Provides guidelines and best practices for querying BigQuery property graphs and semantic graphs: native GQL (Graph Query Language) pattern matching, multi-hop and variable-length paths, aggregation, top-N, path extraction, output formatting (graph visualization with TO_JSON vs tabular), GRAPH_TABLE relational SQL integration, and semantic graph querying via the GRAPH_EXPAND TVF with starting-node view selection and AGG() measures. Also covers hybrid semantic search, combining `VECTOR_SEARCH` candidate generation with graph traversal when a node carries an embedding-backed property. Use when querying graph topology, node/edge connections, paths, or semantic measures over an existing BigQuery graph. Don't use for Cypher or non-BigQuery graph databases, or for creating/modifying a graph schema.
  - *Reference File:* `references/bigquery-graph-query.md`
- **`bigquery-observability`**: - Provides data-retrieval best practices, tool selection guidance, and performant SQL query syntax for BigQuery telemetry across INFORMATION_SCHEMA, Cloud Monitoring, and the REST API. Use when the telemetry to fetch is already known, selecting telemetry tools, writing performant INFORMATION_SCHEMA queries, retrieving telemetry for diagnosing single-job performance bottlenecks, investigating slot contention, job concurrency and queue latency, analyzing reservation capacity, utilization and autoscaling saturation, or auditing capacity-based and on-demand compute and storage resource billable usage. Don't use for root-cause diagnosis or symptom troubleshooting when the cause is unknown (use bigquery-troubleshooting first), or for writing or optimizing business logic SQL (use bigquery-optimization).
  - *Reference File:* `references/bigquery-observability.md`
- **`bigquery-optimization`**: - Provides workflows to optimize BigQuery environments (capacity planning, editions), storage assets (partitioning, clustering, storage lifecycles, billing models), and SQL queries. Use when optimizing cost, modeling Edition migrations, rightsizing reservations, evaluating logical vs. physical storage, designing table partitioning/clustering, generating table DDL, migrating unpartitioned tables, managing partition expiration, optimizing individual SQL queries, or evaluating acceleration structures (search indexes, materialized views, BI Engine). Do not use for raw usage reporting (use bigquery-observability), query execution plan analysis, error troubleshooting, or diagnosing why a specific job was slow (use bigquery-troubleshooting).
  - *Reference File:* `references/bigquery-optimization.md`
- **`bigquery-troubleshooting`**: - Provides diagnostic workflows and step-by-step root-cause analysis procedures for actively broken, failing, or slow BigQuery jobs, execution graph and query plan stage bottlenecks, system performance issues, or unexpectedly expensive workloads. Use when interpreting symptoms, isolating bottlenecks, diagnosing cost spikes (on-demand query spend, capacity slot autoscaling, storage growth), execution graph stages or substep variables, identifying root causes, and determining remediation steps. Don't use for writing or optimizing SQL, proactive capacity planning, or storage layout design (use bigquery-optimization), or when the user already knows which telemetry they want and just needs the query (use bigquery-observability).
  - *Reference File:* `references/bigquery-troubleshooting.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `bigquery-ai-ml`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
