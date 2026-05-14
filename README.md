# GenAI Document Processing Pipeline

A production-ready, multi-cloud GenAI data ingestion pipeline for document processing, LLM-based tagging, and RAG (Retrieval-Augmented Generation) implementation. This project demonstrates enterprise-grade infrastructure as code with deployments on both **AWS** and **Google Cloud Platform (GCP)**.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [AWS Deployment](#aws-deployment)
- [GCP Deployment](#gcp-deployment)
- [Cost Comparison](#cost-comparison)
- [Local Development](#local-development)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This pipeline automates the ingestion, processing, and vectorization of documents for use in RAG-based AI applications. It supports multiple document types (PDF, DOCX, TXT, etc.) and provides:

- **Document Processing**: Text extraction, standardization, and semantic chunking
- **LLM Tagging**: Automated metadata extraction using large language models
- **Vector Storage**: Embeddings generation and storage for similarity search
- **RAG Queries**: Natural language querying over your document corpus

### Key Capabilities

| Capability | Description |
|------------|-------------|
| Multi-format Support | PDF, DOCX, TXT, HTML, and more |
| Intelligent Chunking | Semantic-aware document splitting |
| LLM Integration | Gemini (GCP) / Claude (AWS) for tagging |
| Vector Search | High-performance similarity search |
| Event-Driven | Fully serverless, event-driven architecture |
| Multi-Cloud | Deploy to AWS or GCP with identical functionality |

---

## Architecture

### High-Level Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Upload    │────▶│  Pre-Format  │────▶│   Ingest    │────▶│  Vectorize   │
│  Document   │     │  & Extract   │     │  & Tag      │     │  & Store     │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │   Storage   │     │  Metadata   │     │   Vector    │
                    │   Bucket    │     │   Database  │     │   Database  │
                    └─────────────┘     └─────────────┘     └─────────────┘
```

### Processing Workflows

1. **Pre-Formatting Workflow**: Detect file type → Extract text → Standardize → Semantic chunking
2. **Data Ingestion Workflow**: Read from storage → LLM tagging → Store metadata
3. **Vectorization Workflow**: Generate embeddings → Store in vector database

---

## Features

### Infrastructure as Code
- **Terraform**: Complete IaC for both AWS and GCP
- **Modular Design**: Reusable modules for each service
- **Environment Support**: Dev, staging, and production configurations
- **State Management**: Remote state with locking

### Security
- **IAM/Service Accounts**: Least-privilege access
- **VPC/Private Networks**: Isolated network architecture
- **Secret Management**: Secure credential storage
- **Encryption**: At-rest and in-transit encryption

### Observability
- **Logging**: Centralized log aggregation
- **Monitoring**: Metrics and alerting
- **Tracing**: Distributed request tracing

---

## Project Structure

```
.
├── iac/                          # AWS Infrastructure
│   ├── main.tf                   # Main Terraform configuration
│   ├── vars.tf                   # Variables
│   ├── modules/
│   │   ├── lambda/               # Lambda functions
│   │   │   ├── backend/          # Processing functions
│   │   │   └── ui/               # UI functions
│   │   ├── step_functions/       # Workflow orchestration
│   │   ├── s3/                   # Storage buckets
│   │   ├── sqs/                  # Message queues
│   │   ├── bedrock_kb_*/         # Knowledge bases
│   │   ├── opensearch/           # Vector database
│   │   └── api_gateway/          # API endpoints
│   └── environments/
│
├── iac-gcp/                      # GCP Infrastructure (Hybrid)
│   ├── main.tf                   # Main Terraform configuration
│   ├── variables.tf              # Variables
│   ├── outputs.tf                # Outputs
│   ├── backend.tf                # State backend
│   ├── modules/
│   │   ├── cloud_run/            # Cloud Run services
│   │   ├── cloud_workflows/      # Workflow orchestration
│   │   ├── cloud_storage/        # Storage buckets
│   │   ├── pubsub/               # Message queues
│   │   ├── eventarc/             # Event triggers
│   │   ├── gke/                  # Kubernetes cluster
│   │   ├── vertex_ai/            # AI services
│   │   ├── cloud_sql/            # PostgreSQL database
│   │   ├── vpc/                  # Networking
│   │   └── service_accounts/     # IAM
│   ├── k8s/                      # Kubernetes manifests
│   ├── src/                      # Application source code
│   ├── scripts/                  # Deployment scripts
│   ├── environments/             # Environment configs
│   └── docs/                     # Documentation
│
└── Notes/                        # Project documentation
```

---

## AWS Deployment

### Service Mapping

| Component | AWS Service |
|-----------|-------------|
| Compute | AWS Lambda |
| Orchestration | Step Functions |
| Storage | S3 |
| Queue | SQS |
| Vector DB | OpenSearch Serverless |
| LLM | Amazon Bedrock (Claude) |
| Embeddings | Amazon Bedrock |
| Database | DynamoDB |
| API | API Gateway |

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.4.0
- Python 3.11+

### Deployment Steps

```bash
cd iac

# Initialize Terraform
terraform init

# Select workspace
terraform workspace select dev  # or create: terraform workspace new dev

# Review plan
terraform plan -var-file="environments/dev.tfvars"

# Deploy
terraform apply -var-file="environments/dev.tfvars"
```

### AWS Architecture Diagram

```
                                    ┌─────────────────────────────────────────┐
                                    │              AWS Cloud                   │
┌──────────┐                        │  ┌─────────────────────────────────┐    │
│  Client  │───────────────────────▶│  │         API Gateway             │    │
└──────────┘                        │  └───────────────┬─────────────────┘    │
                                    │                  │                       │
                                    │  ┌───────────────▼─────────────────┐    │
                                    │  │         Step Functions          │    │
                                    │  │    (Workflow Orchestration)     │    │
                                    │  └───────────────┬─────────────────┘    │
                                    │                  │                       │
                                    │  ┌───────────────▼─────────────────┐    │
                                    │  │        Lambda Functions         │    │
                                    │  │  ┌─────┐ ┌─────┐ ┌─────┐       │    │
                                    │  │  │Detect│ │Chunk│ │Embed│ ...   │    │
                                    │  │  └─────┘ └─────┘ └─────┘       │    │
                                    │  └───────────────┬─────────────────┘    │
                                    │                  │                       │
                                    │  ┌───────────────┼─────────────────┐    │
                                    │  │               │                 │    │
                                    │  ▼               ▼                 ▼    │
                                    │ ┌───┐      ┌──────────┐    ┌─────────┐ │
                                    │ │S3 │      │ Bedrock  │    │OpenSearch│ │
                                    │ │   │      │(LLM/Embed)│   │(Vector) │ │
                                    │ └───┘      └──────────┘    └─────────┘ │
                                    └─────────────────────────────────────────┘
```

---

## GCP Deployment

### Hybrid Architecture (Cloud Run + GKE)

The GCP deployment uses a **hybrid architecture** that combines Cloud Run for low-traffic services and GKE for high-compute services, optimizing for both cost and performance.

### Service Mapping

| Component | GCP Service |
|-----------|-------------|
| Low-Traffic Compute | Cloud Run |
| High-Compute | GKE (Kubernetes) |
| Orchestration | Cloud Workflows |
| Storage | Cloud Storage |
| Queue | Pub/Sub |
| Events | Eventarc |
| Vector DB | Vertex AI Vector Search |
| LLM | Vertex AI (Gemini 1.5 Pro) |
| Embeddings | Vertex AI (text-embedding-004) |
| Database | Cloud SQL (PostgreSQL) |
| API | API Gateway |

### Service Classification

#### Cloud Run Services (Low-Traffic, Scale-to-Zero)
- `detect-file-type` - File type detection
- `text-standardize` - Text standardization
- `identify-distinct-process` - Process identification
- `create-process-docs` - Document creation
- `read-from-storage` - Storage operations
- `add-llm-tags` - Metadata tagging

#### GKE Services (High-Compute, Always-On)
- `text-extraction` - Heavy PDF/document processing
- `semantic-chunking` - ML-based chunking
- `llm-tagging` - LLM inference
- `chunk-sop` - SOP chunking
- `generate-embedding` - Embedding generation
- `store-to-vector-db` - Vector storage

### Prerequisites

- Google Cloud SDK (`gcloud`) installed
- Terraform >= 1.4.0
- kubectl (for GKE management)
- Docker (for local testing)

### Deployment Steps

```bash
cd iac-gcp

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  run.googleapis.com \
  workflows.googleapis.com \
  eventarc.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com

# Create Terraform state bucket
gsutil mb -l us-central1 gs://tsh-industries-terraform-state
gsutil versioning set on gs://tsh-industries-terraform-state

# Update backend.tf to uncomment the GCS backend

# Initialize Terraform
terraform init

# Select workspace
terraform workspace select dev

# Update dev.tfvars: set skip_gcp_auth = false

# Review plan
terraform plan -var-file="environments/dev.tfvars"

# Deploy
terraform apply -var-file="environments/dev.tfvars"

# Deploy Kubernetes manifests (after GKE is ready)
gcloud container clusters get-credentials $(terraform output -raw gke_cluster_name) --region us-central1
kubectl apply -k k8s/
```

### GCP Hybrid Architecture Diagram

```
                                    ┌─────────────────────────────────────────────────────┐
                                    │                    GCP Cloud                         │
┌──────────┐                        │  ┌─────────────────────────────────────────────┐    │
│  Client  │───────────────────────▶│  │              API Gateway                    │    │
└──────────┘                        │  └─────────────────────┬───────────────────────┘    │
                                    │                        │                             │
                                    │  ┌─────────────────────▼───────────────────────┐    │
                                    │  │              Cloud Workflows                 │    │
                                    │  │          (Workflow Orchestration)            │    │
                                    │  └─────────────────────┬───────────────────────┘    │
                                    │                        │                             │
                                    │         ┌──────────────┴──────────────┐             │
                                    │         │                             │             │
                                    │         ▼                             ▼             │
                                    │  ┌─────────────────┐         ┌─────────────────┐   │
                                    │  │   Cloud Run     │         │      GKE        │   │
                                    │  │  (Low Traffic)  │         │ (High Compute)  │   │
                                    │  │                 │         │                 │   │
                                    │  │ • detect-file   │         │ • text-extract  │   │
                                    │  │ • standardize   │         │ • chunking      │   │
                                    │  │ • read-storage  │         │ • embedding     │   │
                                    │  │ • add-tags      │         │ • llm-tagging   │   │
                                    │  └────────┬────────┘         └────────┬────────┘   │
                                    │           │                           │             │
                                    │           └─────────────┬─────────────┘             │
                                    │                         │                           │
                                    │  ┌──────────────────────┼──────────────────────┐   │
                                    │  │                      │                      │   │
                                    │  ▼                      ▼                      ▼   │
                                    │ ┌───────────┐    ┌────────────┐    ┌────────────┐ │
                                    │ │  Cloud    │    │ Vertex AI  │    │ Vertex AI  │ │
                                    │ │  Storage  │    │  (Gemini)  │    │  Vector    │ │
                                    │ └───────────┘    └────────────┘    │  Search    │ │
                                    │                                    └────────────┘ │
                                    └─────────────────────────────────────────────────────┘
```

---

## Cost Comparison

### Monthly Cost Estimates (Medium Workload: ~10,000 documents/month)

| Component | AWS | GCP (Cloud Run Only) | GCP (Hybrid) | Savings |
|-----------|-----|---------------------|--------------|---------|
| **Compute** | | | | |
| Serverless/Cloud Run | $180 | $450 | $120 | - |
| GKE (Spot VMs) | N/A | N/A | $180 | - |
| **Orchestration** | $25 | $15 | $15 | - |
| **Storage** | $50 | $45 | $45 | - |
| **Vector Database** | $350 | $400 | $400 | - |
| **LLM/Embeddings** | $200 | $180 | $180 | - |
| **Database** | $25 | $75 | $75 | - |
| **Networking** | $30 | $25 | $25 | - |
| **Other** | $40 | $35 | $35 | - |
| | | | | |
| **Total** | **$900** | **$1,225** | **$1,075** | **~12%** |

### Why Hybrid Architecture Saves Money

#### Cloud Run Limitations
- Minimum billing of 100ms per request
- Cold starts add latency and cost
- Not cost-effective for long-running compute tasks
- Per-request pricing adds up for high-volume services

#### GKE Advantages for High-Compute
- **Spot VMs**: 60-91% cheaper than on-demand
- **Sustained use discounts**: Up to 30% off
- **Resource sharing**: Multiple services share nodes
- **No cold starts**: Always-warm containers

#### Hybrid Strategy
```
┌─────────────────────────────────────────────────────────────────┐
│                    Service Classification                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Cloud Run (Scale-to-Zero)          GKE (Always-On + Spot)      │
│  ─────────────────────────          ──────────────────────      │
│  • Low request volume               • High request volume        │
│  • Quick execution (<30s)           • Long execution (>30s)      │
│  • Bursty traffic                   • Steady traffic             │
│  • Simple I/O operations            • CPU/Memory intensive       │
│                                                                  │
│  Examples:                          Examples:                    │
│  • File type detection              • PDF text extraction        │
│  • Metadata reads                   • Embedding generation       │
│  • Simple transformations           • LLM inference              │
│                                     • Semantic chunking          │
└─────────────────────────────────────────────────────────────────┘
```

### Cost Optimization Tips

1. **Use Spot VMs for GKE**: 60-91% savings on compute
2. **Scale to Zero**: Cloud Run services cost nothing when idle
3. **Right-size instances**: Start small, scale based on metrics
4. **Use committed use discounts**: For predictable workloads
5. **Optimize LLM calls**: Use Gemini Flash for simple tasks
6. **Batch embeddings**: Process in batches to reduce API calls

### Break-Even Analysis

| Workload | Cloud Run Only | Hybrid | Recommendation |
|----------|---------------|--------|----------------|
| < 1,000 docs/month | $200 | $350 | Cloud Run |
| 1,000-5,000 docs/month | $500 | $450 | Hybrid |
| 5,000-20,000 docs/month | $1,200 | $900 | Hybrid |
| > 20,000 docs/month | $2,500+ | $1,500 | Hybrid |

---

## Local Development

### Quick Start with Docker Compose

```bash
cd iac-gcp

# Start local environment (emulators + databases)
./scripts/local-setup.sh start

# Access services:
# - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
# - PostgreSQL: localhost:5432 (tsh-industries/localdevpassword)
# - Adminer (DB UI): http://localhost:8088
# - Pub/Sub Emulator: localhost:8085
# - Qdrant (Vector DB): http://localhost:6333
# - Redis: localhost:6379

# Run a test through the pipeline
./scripts/local-setup.sh test

# View logs
./scripts/local-setup.sh logs

# Stop all services
./scripts/local-setup.sh stop

# Clean up (remove all data)
./scripts/local-setup.sh cleanup
```

### Terraform Validation (Without GCP Account)

```bash
cd iac-gcp

# Initialize without backend
terraform init -backend=false

# Validate configuration
terraform validate

# Plan with local validation mode
terraform plan -var-file="environments/dev.tfvars"
# Note: dev.tfvars has skip_gcp_auth=true for local validation
```

---

## Environment Variables

### AWS

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region (default: us-east-1) |
| `AWS_PROFILE` | AWS CLI profile name |
| `TF_VAR_environment` | Environment name |

### GCP

| Variable | Description |
|----------|-------------|
| `GOOGLE_PROJECT` | GCP project ID |
| `GOOGLE_REGION` | GCP region (default: us-central1) |
| `TF_VAR_skip_gcp_auth` | Skip GCP auth for local validation |

---

## Monitoring & Observability

### AWS
- **CloudWatch Logs**: Centralized logging
- **CloudWatch Metrics**: Performance metrics
- **X-Ray**: Distributed tracing
- **CloudWatch Alarms**: Alerting

### GCP
- **Cloud Logging**: Centralized logging
- **Cloud Monitoring**: Metrics and dashboards
- **Cloud Trace**: Distributed tracing
- **Error Reporting**: Error aggregation

---

## Security Considerations

1. **Network Isolation**: VPC with private subnets
2. **IAM**: Least-privilege service accounts
3. **Encryption**: KMS for data at rest
4. **Secrets**: Secret Manager for credentials
5. **API Security**: JWT authentication
6. **Audit Logging**: All API calls logged

---

## Troubleshooting

### Common Issues

#### Terraform State Lock
```bash
# Force unlock (use with caution)
terraform force-unlock LOCK_ID
```

#### GKE Authentication
```bash
# Refresh credentials
gcloud container clusters get-credentials CLUSTER_NAME --region REGION
```

#### Cloud Run Cold Starts
- Increase `min_instances` for critical services
- Use Cloud Run "always on CPU" feature

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- AWS and GCP documentation
- Terraform community modules
- Open-source LLM and embedding models

---

## Contact

For questions or support, please open an issue in this repository.
