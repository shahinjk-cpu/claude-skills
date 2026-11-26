---
name: gcp-cloud-expert
description: Google Cloud Platform (GCP) master enterprise architect suite covering Cloud Run, GKE, Dataflow, Composer (Airflow), BigQuery, Cloud Storage, VPC networking, and security.
---

# GCP Enterprise Architecture Master Suite

Cloud architecture, data engineering, serverless orchestration, and reliability on Google Cloud.

## Services & Architectures
### Cloud Architect (`gcp-cloud-architect`)
---
name: "gcp-cloud-architect"
description: "Design, deploy and cut the cost of Google Cloud setups: Cloud Run, GKE, Functions, Cloud SQL, BigQuery, moving to GCP. Use whenever the user asks how to host or run something on GCP, why their GCP bill is high, or plans a GCP migration."
---

# GCP Cloud Architect

Design scalable, cost-effective Google Cloud architectures for startups and enterprises with infrastructure-as-code templates.

---

## Wo

### Cloud Run (`gcp-cloud-run`)
---
name: gcp-cloud-run
description: "Specialized skill for building production-ready serverless applications on GCP. Covers Cloud Run services (containerized), Cloud Run Functions (event-driven), cold start optimization, and event-driven architecture with Pub/Sub."
metadata:
  source: vibeship-spawner-skills (Apache 2.0)
---

# GCP Cloud Run

## Patterns

### Cloud Run Service Pattern

Containerized web service on Cloud Run

**When to use**: ['W

### Composer Troubleshooting (`gcp-composer-troubleshooting`)
---
name: gcp-composer-troubleshooting
description: 'Provides expert guidance for troubleshooting Cloud Composer (Apache
  Airflow) and Orchestration pipelines. Use this skill when the user asks to generate
  Root Cause Analysis (RCA), troubleshoot or fix a failed pipeline, DAG in Composer
  environment and generate RCA report.

  '
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Composer Troubleshooting Expert Skill

This 

### Data Pipelines (`gcp-data-pipelines`)
---
name: gcp-data-pipelines
description: 'Primary entry point for building, managing, and orchestrating data pipelines
  on Google Cloud. Guides users to the appropriate skill for dbt, Dataflow (Apache
  Beam), Dataform, Spark (Dataproc Serverless), BigQuery Data Transfer Service (DTS)
  or orchestration pipeline using Cloud Composer. Clarify requirements and resolve
  ambiguity for creating, updating and running data pipelines.

  '
license: Ap

### Dataflow (`gcp-dataflow`)
---
name: gcp-dataflow
description: >
  Guides writing, packaging, executing, and troubleshooting Apache Beam
  pipelines on Dataflow. Use when creating new pipelines, configuring Flex
  Templates, or analyzing performance of Dataflow jobs. Capabilities include
  Java/Python/Go setup, Cloud Build integration, and deep diagnostic analysis
  of job health and autoscaling.

  Use when:
  - Creating an Apache Beam Dataflow pipeline.
  - Creating a Go

### Managed Airflow Dag Authoring (`gcp-managed-airflow-dag-authoring`)
---
name: gcp-managed-airflow-dag-authoring
description: Guides the authoring and validation of Apache Airflow DAGs for Managed Service for Apache Airflow (MSAA; formerly Cloud Composer). Covers environment context discovery, Airflow 2 vs 3 compatibility, authoring best practices, and local/remote validation processes. Use when creating or extending an Airflow DAG. Don't use when authoring Python code unrelated to Airflow DAGs.
license: Apache-2.

### Managed Airflow Migrations (`gcp-managed-airflow-migrations`)
---
name: gcp-managed-airflow-migrations
description: Provides guidance for migrating Apache Airflow DAGs in Managed Service for Apache Airflow (MSAA; formerly Cloud Composer). Covers migration to Airflow 2.11.1 (MSAA Gen 2 and 3) and Airflow 3 (MSAA Gen 3), including environment inspection, GCS download/upload and scanning patterns for breaking changes.
license: Apache-2.0
metadata:
  version: v1
  publisher: google
---

# Managed Service for Ap

### Managed Airflow Recommendations (`gcp-managed-airflow-recommendations`)
---
name: gcp-managed-airflow-recommendations
description: 'Provides recommendations and best practices for creating, configuring, tuning and optimizing Managed Service for Apache Airflow (MSAA, Cloud Composer) environments. Use when the user asks for guidance, recommendations, or best practices on configuring Cloud Composer, scaling Airflow environments, preventing workload restarts, or analyzing system health.'
license: Apache-2.0
metadata:
  v

### Managed Spark Upgrades (`gcp-managed-spark-upgrades`)
---
name: gcp-managed-spark-upgrades
description: |
  Upgrades Spark workloads on Google Cloud Managed Service for Apache Spark (formerly known as Dataproc) clusters and Serverless to a newer image or runtime version. Supports static compatibility analysis, code upgrade, build checks against the target version, and optional verification runs.
  Use when:
  - Upgrading Managed Spark versions (major, minor, or sub-minor) or assessing upgrade readin

### Pipeline Orchestration (`gcp-pipeline-orchestration`)
---
name: gcp-pipeline-orchestration
description: This skill helps the agent generate or update orchestration pipeline
  definitions for Google Cloud Composer to initialize orchestration pipeline or update
  the orchestration definition for orchestration of various data pipelines, like dbt
  pipelines, notebooks, Spark jobs, Dataform, Python scripts, Vertex AI custom jobs,
  Machine Learning training, or inline BigQuery SQL queries. This skill al

### Pipeline Resource Provisioning (`gcp-pipeline-resource-provisioning`)
---
name: gcp-pipeline-resource-provisioning
description: |
  Automates declarative resource creation and provisioning for data pipelines, supporting BigQuery, Dataform, Dataproc, BigQuery Data Transfer Service (DTS), and other resources. It manages environment-specific configurations (dev, staging, prod) through a deployment.yaml file.
  Use when:
  - Modifying or creating deployment.yaml for deployment settings.
  - Resolving environment-specif

### Spark (`gcp-spark`)
---
name: gcp-spark
description: |
  Authors, optimizes, and runs PySpark and Spark code on Google Cloud Managed Spark
  (Dataproc Serverless, clusters, and Spark Connect).
  Use when:
  - Authoring or running Spark/PySpark notebooks in any kernel (Local Kernel with
    spark-remote templates, Remote Spark / Remote Kernel, ManagedSparkSession, Spark Connect).
  - Querying, transforming, or writing data with PySpark or Spark SQL, including
    Apa

### Spark Observability (`gcp-spark-observability`)
---
name: gcp-spark-observability
description: >-
  Monitors, inventories, and assesses Google Cloud Managed Service for Apache
  Spark (Dataproc Serverless and Dataproc on Compute Engine) environments,
  clusters, batches, jobs, sessions, metrics, logs, costs, and configurations
  across single and multiple regions. Use when listing active or historical
  Spark workloads, discovering failed batches or jobs, auditing multi-region
  fleet inventor

### Spark Troubleshooting (`gcp-spark-troubleshooting`)
---
name: gcp-spark-troubleshooting
description: "Provides expert guidance for troubleshooting Google Cloud Spark and Dataproc workloads (Dataproc Serverless batches and standard Dataproc clusters), and inspecting, streaming, searching, tailing, or summarizing Spark driver outputs and event logs in Cloud Storage. Use when the user asks to debug, troubleshoot, diagnose, or perform Root Cause Analysis (RCA) on failed Spark jobs, PySpark batches, or

