# GenAI Data Ingestion Pipeline - Google Cloud Platform

This directory contains the Terraform Infrastructure as Code (IaC) for deploying the GenAI data ingestion pipeline on Google Cloud Platform, migrated from AWS.

## Architecture Overview

The pipeline consists of 4 main workflows:

1. **Pre-Format Workflow** - Document upload, text extraction, standardization, semantic chunking
2. **Data Ingestion Workflow** - LLM-based tagging of process documents
3. **Vectorization Process Workflow** - Embedding generation and storage for process docs
4. **Vectorization Non-Process Workflow** - Embedding generation and storage for non-process docs

## AWS to GCP Service Mapping

| AWS Service | GCP Equivalent |
|-------------|----------------|
| S3 | Cloud Storage |
| EventBridge | Eventarc |
| SQS | Cloud Pub/Sub |
| Lambda | Cloud Run |
| Step Functions | Cloud Workflows |
| ECR | Artifact Registry |
| OpenSearch Serverless | Vertex AI Vector Search |
| Amazon Bedrock | Vertex AI |
| Amazon Titan V2 | Vertex AI Embeddings (text-embedding-004) |
| Claude on Bedrock | Claude on Vertex AI / Gemini |
| Bedrock Knowledge Base | Vertex AI Search |
| RDS Aurora PostgreSQL | Cloud SQL for PostgreSQL |
| CloudFront | Cloud CDN |
| API Gateway | API Gateway |
| Secrets Manager | Secret Manager |
| CloudWatch | Cloud Logging + Monitoring |

## Prerequisites

1. **GCP Project**: Create a GCP project and note the project ID
2. **gcloud CLI**: Install and configure the gcloud CLI
3. **Terraform**: Install Terraform >= 1.4.0
4. **Service Account**: Create a service account with appropriate permissions

## Quick Start

### 1. Configure GCP Authentication

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Create Terraform State Bucket

```bash
gsutil mb -l us-central1 gs://tsh-industries-terraform-state
gsutil versioning set on gs://tsh-industries-terraform-state
```

### 3. Initialize Terraform

```bash
cd iac-gcp
terraform init
```

### 4. Create Workspace

```bash
terraform workspace new dev
# or
terraform workspace select dev
```

### 5. Configure Variables

Create a `terraform.tfvars` file:

```hcl
project_id                = "your-gcp-project-id"
region                    = "us-central1"
environment               = "development"
vertex_llm_model_id       = "gemini-1.5-pro"
vertex_embedding_model_id = "text-embedding-004"
```

### 6. Deploy Infrastructure

```bash
terraform plan
terraform apply
```

## Module Structure

```
iac-gcp/
├── main.tf                 # Main configuration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── backend.tf              # State backend config
└── modules/
    ├── cloud_storage/      # GCS buckets
    ├── eventarc/           # Event triggers
    ├── pubsub/             # Message queues
    ├── cloud_workflows/    # Workflow orchestration
    ├── cloud_run/          # Serverless functions
    ├── artifact_registry/  # Container registry
    ├── vertex_ai/          # AI/ML services
    ├── cloud_sql/          # PostgreSQL database
    ├── secret_manager/     # Secrets storage
    ├── vpc/                # Networking
    ├── api_gateway/        # API management
    └── service_accounts/   # IAM service accounts
```

## Building Container Images

Each Cloud Run service requires a container image. Build and push images to Artifact Registry:

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push an image
cd src/functions/detect_file_type
docker build -t us-central1-docker.pkg.dev/PROJECT_ID/REPO_NAME/detect-file-type:latest .
docker push us-central1-docker.pkg.dev/PROJECT_ID/REPO_NAME/detect-file-type:latest
```

## Python SDK Migration

The `src/common/gcp_clients.py` module provides GCP equivalents for AWS SDK calls:

```python
# AWS (before)
import boto3
s3 = boto3.client('s3')
s3.get_object(Bucket='bucket', Key='key')

# GCP (after)
from common.gcp_clients import get_storage_client
storage = get_storage_client()
storage.get_object(bucket='bucket', key='key')
```

## Environment Variables

Cloud Run services use these environment variables:

| Variable | Description |
|----------|-------------|
| `GCP_PROJECT` | GCP project ID |
| `REGION` | GCP region |
| `VERTEX_MODEL_ID` | Vertex AI LLM model ID |
| `VERTEX_EMBEDDING_MODEL` | Vertex AI embedding model ID |
| `DB_SECRET_ID` | Secret Manager secret ID for DB credentials |
| `DB_CONNECTION_NAME` | Cloud SQL connection name |

## Monitoring

- **Cloud Logging**: All services log to Cloud Logging
- **Cloud Monitoring**: Metrics and dashboards available
- **Error Reporting**: Automatic error tracking

## Cost Optimization

1. **Cloud Run**: Set min instances to 0 for dev environments
2. **Cloud SQL**: Use smaller instance types for non-production
3. **Vertex AI Vector Search**: Use automatic scaling
4. **Pub/Sub**: Messages are charged per operation

## Security

1. All services use VPC connectors for private networking
2. Cloud SQL uses private IP only
3. Secrets stored in Secret Manager
4. Service accounts follow least-privilege principle

## Cleanup

```bash
terraform destroy
```

## Support

For issues or questions, refer to:
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
