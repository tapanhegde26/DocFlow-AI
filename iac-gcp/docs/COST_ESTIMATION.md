# GCP GenAI Pipeline - Cost Estimation Report

**Prepared by:** SRE Team  
**Date:** May 2026  
**Version:** 1.0

---

## Executive Summary

This document provides a detailed cost estimation for the GenAI Data Ingestion Pipeline deployed on Google Cloud Platform. The analysis covers three deployment scenarios: Development, Staging, and Production environments.

| Environment | Monthly Cost (USD) | Annual Cost (USD) |
|-------------|-------------------|-------------------|
| Development | $450 - $650 | $5,400 - $7,800 |
| Staging | $800 - $1,200 | $9,600 - $14,400 |
| Production | $2,500 - $4,500 | $30,000 - $54,000 |

---

## Assumptions

### Workload Assumptions

| Metric | Development | Staging | Production |
|--------|-------------|---------|------------|
| Documents processed/month | 500 | 2,000 | 10,000 |
| Average document size | 2 MB | 2 MB | 2 MB |
| RAG queries/month | 5,000 | 20,000 | 200,000 |
| Concurrent users | 5 | 20 | 100 |
| Data retention | 30 days | 90 days | 365 days |
| Availability target | 95% | 99% | 99.9% |

### Technical Assumptions

- Region: `us-central1` (Iowa) - lowest cost tier
- Embedding dimension: 768 (text-embedding-004)
- Average chunks per document: 50
- LLM tokens per document: ~10,000 (input + output)
- LLM tokens per RAG query: ~2,000 (input + output)

---

## Detailed Cost Breakdown

### 1. Compute - Cloud Run

Cloud Run pricing: $0.00002400/vCPU-second, $0.00000250/GiB-second

#### Development Environment

| Service | vCPU | Memory | Requests/month | Avg Duration | Min Instances | Monthly Cost |
|---------|------|--------|----------------|--------------|---------------|--------------|
| detect-file-type | 1 | 512Mi | 500 | 2s | 0 | $0.50 |
| text-extraction | 2 | 2Gi | 500 | 30s | 0 | $15.00 |
| text-standardize | 1 | 1Gi | 500 | 10s | 0 | $2.50 |
| semantic-chunking | 2 | 4Gi | 500 | 60s | 0 | $35.00 |
| identify-distinct-process | 1 | 1Gi | 500 | 5s | 0 | $1.25 |
| create-process-docs | 1 | 1Gi | 500 | 10s | 0 | $2.50 |
| read-from-storage | 1 | 512Mi | 1,000 | 2s | 0 | $1.00 |
| llm-tagging | 2 | 4Gi | 500 | 45s | 0 | $25.00 |
| add-llm-tags | 1 | 1Gi | 500 | 5s | 0 | $1.25 |
| chunk-sop | 1 | 1Gi | 1,000 | 5s | 0 | $2.50 |
| generate-embedding | 2 | 4Gi | 25,000 | 2s | 0 | $50.00 |
| store-to-vector-db | 2 | 2Gi | 25,000 | 1s | 0 | $25.00 |
| **Subtotal** | | | | | | **$161.50** |

#### Production Environment (with min instances for latency)

| Service | vCPU | Memory | Requests/month | Avg Duration | Min Instances | Monthly Cost |
|---------|------|--------|----------------|--------------|---------------|--------------|
| detect-file-type | 1 | 512Mi | 10,000 | 2s | 1 | $35.00 |
| text-extraction | 2 | 2Gi | 10,000 | 30s | 2 | $180.00 |
| text-standardize | 1 | 1Gi | 10,000 | 10s | 1 | $45.00 |
| semantic-chunking | 2 | 4Gi | 10,000 | 60s | 2 | $350.00 |
| identify-distinct-process | 1 | 1Gi | 10,000 | 5s | 1 | $30.00 |
| create-process-docs | 1 | 1Gi | 10,000 | 10s | 1 | $45.00 |
| read-from-storage | 1 | 512Mi | 20,000 | 2s | 1 | $40.00 |
| llm-tagging | 2 | 4Gi | 10,000 | 45s | 2 | $280.00 |
| add-llm-tags | 1 | 1Gi | 10,000 | 5s | 1 | $30.00 |
| chunk-sop | 1 | 1Gi | 20,000 | 5s | 1 | $45.00 |
| generate-embedding | 2 | 4Gi | 500,000 | 2s | 3 | $450.00 |
| store-to-vector-db | 2 | 2Gi | 500,000 | 1s | 2 | $280.00 |
| **Subtotal** | | | | | | **$1,810.00** |

---

### 2. Storage - Cloud Storage

Pricing: Standard - $0.020/GB/month, Nearline - $0.010/GB/month

| Bucket | Dev Size | Staging Size | Prod Size | Storage Class | Dev Cost | Prod Cost |
|--------|----------|--------------|-----------|---------------|----------|-----------|
| raw-sop-upload | 1 GB | 4 GB | 20 GB | Standard | $0.02 | $0.40 |
| text-extraction | 2 GB | 8 GB | 40 GB | Standard | $0.04 | $0.80 |
| sop-standardized | 3 GB | 12 GB | 60 GB | Standard | $0.06 | $1.20 |
| sop-embedding | 5 GB | 20 GB | 100 GB | Standard | $0.10 | $2.00 |
| nonprocess-embedding | 2 GB | 8 GB | 40 GB | Standard | $0.04 | $0.80 |
| vector-index-data | 10 GB | 40 GB | 200 GB | Standard | $0.20 | $4.00 |
| **Subtotal** | | | | | **$0.46** | **$9.20** |

**Operations Cost** (Class A: $0.05/10K, Class B: $0.004/10K):

| Environment | Class A Ops | Class B Ops | Monthly Cost |
|-------------|-------------|-------------|--------------|
| Development | 50,000 | 200,000 | $0.33 |
| Production | 1,000,000 | 5,000,000 | $7.00 |

---

### 3. Database - Cloud SQL PostgreSQL

| Configuration | Development | Staging | Production |
|---------------|-------------|---------|------------|
| Instance Type | db-f1-micro | db-custom-2-4096 | db-custom-4-8192 |
| vCPUs | Shared | 2 | 4 |
| Memory | 0.6 GB | 4 GB | 8 GB |
| Storage | 10 GB SSD | 50 GB SSD | 200 GB SSD |
| HA | No | No | Yes (Regional) |
| Backups | 7 days | 14 days | 30 days |
| **Monthly Cost** | **$9.37** | **$77.00** | **$310.00** |

**Breakdown (Production):**
- Instance: $0.1386/hr × 730 hrs = $101.18
- HA Standby: $101.18
- Storage: 200 GB × $0.17 = $34.00
- Backups: 200 GB × $0.08 × 30 days = $48.00
- Network egress: ~$25.00

---

### 4. AI/ML - Vertex AI

#### Vertex AI Embeddings (text-embedding-004)

Pricing: $0.00002 per 1,000 characters (~$0.025 per 1M tokens)

| Environment | Documents | Chunks/Doc | Chars/Chunk | RAG Queries | Monthly Cost |
|-------------|-----------|------------|-------------|-------------|--------------|
| Development | 500 | 50 | 2,000 | 5,000 | $1.50 |
| Staging | 2,000 | 50 | 2,000 | 20,000 | $6.00 |
| Production | 10,000 | 50 | 2,000 | 200,000 | $30.00 |

#### Vertex AI LLM (Gemini 1.5 Pro)

Pricing: Input $0.00125/1K tokens, Output $0.00375/1K tokens

| Use Case | Input Tokens | Output Tokens | Cost/Request |
|----------|--------------|---------------|--------------|
| Semantic Chunking | 8,000 | 2,000 | $0.0175 |
| LLM Tagging | 5,000 | 1,000 | $0.0100 |
| RAG Query | 1,500 | 500 | $0.0037 |

| Environment | Chunking Requests | Tagging Requests | RAG Queries | Monthly Cost |
|-------------|-------------------|------------------|-------------|--------------|
| Development | 500 | 500 | 5,000 | $32.25 |
| Staging | 2,000 | 2,000 | 20,000 | $129.00 |
| Production | 10,000 | 10,000 | 200,000 | $1,015.00 |

**Cost Optimization Option - Gemini 1.5 Flash:**
- 10x cheaper: Input $0.000125/1K, Output $0.000375/1K
- Production cost would drop to ~$100/month
- Trade-off: Slightly lower quality for non-critical tasks

---

### 5. Vector Search - Vertex AI Vector Search

Pricing varies by shard size and replica count.

| Configuration | Development | Staging | Production |
|---------------|-------------|---------|------------|
| Shard Size | Small | Small | Medium |
| Indexes | 2 | 2 | 2 |
| Replicas/Index | 1 | 2 | 3 |
| Vectors (Process) | 25,000 | 100,000 | 500,000 |
| Vectors (Non-Process) | 10,000 | 40,000 | 200,000 |
| Queries/month | 5,000 | 20,000 | 200,000 |
| **Monthly Cost** | **$75.00** | **$200.00** | **$600.00** |

**Breakdown:**
- Index hosting: $0.10/hour per replica × 730 hours = $73/replica
- Query cost: $0.40 per 1,000 queries
- Data ingestion: Included in hosting

**Alternative: AlloyDB with pgvector**
- Could reduce costs by 40-50% for smaller workloads
- Trade-off: Less scalable, requires more management

---

### 6. Messaging - Cloud Pub/Sub

Pricing: $40/TiB for message delivery

| Environment | Messages/Month | Avg Size | Data Volume | Monthly Cost |
|-------------|----------------|----------|-------------|--------------|
| Development | 50,000 | 1 KB | 50 MB | $0.50 |
| Staging | 200,000 | 1 KB | 200 MB | $1.00 |
| Production | 2,000,000 | 1 KB | 2 GB | $5.00 |

---

### 7. Workflow Orchestration - Cloud Workflows

Pricing: $0.01 per 1,000 internal steps, $0.025 per 1,000 external calls

| Environment | Workflow Executions | Steps/Execution | External Calls | Monthly Cost |
|-------------|---------------------|-----------------|----------------|--------------|
| Development | 2,000 | 10 | 6 | $0.50 |
| Staging | 8,000 | 10 | 6 | $2.00 |
| Production | 40,000 | 10 | 6 | $10.00 |

---

### 8. Networking

#### VPC and NAT

| Component | Development | Staging | Production |
|-----------|-------------|---------|------------|
| VPC Connector | $7.30 | $14.60 | $36.50 |
| Cloud NAT | $1.00 | $5.00 | $25.00 |
| Egress (Internet) | $2.00 | $10.00 | $50.00 |
| **Subtotal** | **$10.30** | **$29.60** | **$111.50** |

#### API Gateway

| Environment | Requests/Month | Monthly Cost |
|-------------|----------------|--------------|
| Development | 10,000 | $3.00 |
| Staging | 50,000 | $15.00 |
| Production | 500,000 | $150.00 |

---

### 9. Security and Secrets

#### Secret Manager

Pricing: $0.03 per secret version per month, $0.03 per 10,000 access operations

| Environment | Secrets | Versions | Access Ops | Monthly Cost |
|-------------|---------|----------|------------|--------------|
| Development | 5 | 2 | 10,000 | $0.33 |
| Staging | 5 | 3 | 50,000 | $0.60 |
| Production | 10 | 5 | 500,000 | $3.00 |

---

### 10. Monitoring and Logging

#### Cloud Logging

Pricing: First 50 GB free, then $0.50/GB

| Environment | Log Volume/Month | Monthly Cost |
|-------------|------------------|--------------|
| Development | 10 GB | $0.00 |
| Staging | 30 GB | $0.00 |
| Production | 100 GB | $25.00 |

#### Cloud Monitoring

| Environment | Metrics | Uptime Checks | Monthly Cost |
|-------------|---------|---------------|--------------|
| Development | Basic | 3 | $0.00 |
| Staging | Custom (10) | 5 | $5.00 |
| Production | Custom (50) | 20 | $25.00 |

---

## Total Cost Summary

### Development Environment

| Category | Monthly Cost |
|----------|--------------|
| Cloud Run | $161.50 |
| Cloud Storage | $1.00 |
| Cloud SQL | $9.37 |
| Vertex AI Embeddings | $1.50 |
| Vertex AI LLM | $32.25 |
| Vector Search | $75.00 |
| Pub/Sub | $0.50 |
| Workflows | $0.50 |
| Networking | $13.30 |
| Security | $0.33 |
| Monitoring | $0.00 |
| **Total** | **$295.25** |
| **With 20% buffer** | **$354.30** |

### Staging Environment

| Category | Monthly Cost |
|----------|--------------|
| Cloud Run | $500.00 |
| Cloud Storage | $3.00 |
| Cloud SQL | $77.00 |
| Vertex AI Embeddings | $6.00 |
| Vertex AI LLM | $129.00 |
| Vector Search | $200.00 |
| Pub/Sub | $1.00 |
| Workflows | $2.00 |
| Networking | $44.60 |
| Security | $0.60 |
| Monitoring | $5.00 |
| **Total** | **$968.20** |
| **With 20% buffer** | **$1,161.84** |

### Production Environment

| Category | Monthly Cost |
|----------|--------------|
| Cloud Run | $1,810.00 |
| Cloud Storage | $16.20 |
| Cloud SQL | $310.00 |
| Vertex AI Embeddings | $30.00 |
| Vertex AI LLM | $1,015.00 |
| Vector Search | $600.00 |
| Pub/Sub | $5.00 |
| Workflows | $10.00 |
| Networking | $261.50 |
| Security | $3.00 |
| Monitoring | $50.00 |
| **Total** | **$4,110.70** |
| **With 20% buffer** | **$4,932.84** |

---

## Cost Optimization Recommendations

### Immediate Savings (20-30% reduction)

1. **Use Gemini 1.5 Flash for non-critical LLM tasks**
   - Semantic chunking and tagging can use Flash
   - Keep Pro for RAG responses
   - Savings: ~$600/month in production

2. **Implement request batching for embeddings**
   - Batch up to 250 texts per API call
   - Reduces API overhead
   - Savings: ~$10/month

3. **Use committed use discounts (CUDs)**
   - 1-year commitment: 20% discount
   - 3-year commitment: 40% discount
   - Applicable to: Cloud SQL, Cloud Run (min instances)

### Medium-term Optimizations

4. **Implement caching layer**
   - Cache frequent RAG queries with Memorystore
   - Cache embeddings for repeated content
   - Potential savings: 30-40% on LLM costs

5. **Right-size Cloud Run services**
   - Monitor actual CPU/memory usage
   - Adjust limits based on P95 metrics
   - Potential savings: 15-20%

6. **Consider AlloyDB for combined SQL + Vector**
   - Eliminates separate Vector Search cost
   - Better for workloads < 1M vectors
   - Potential savings: $400-500/month

### Long-term Architecture Changes

7. **Implement tiered storage**
   - Move old documents to Nearline/Coldline
   - Implement lifecycle policies
   - Savings: 50-80% on storage

8. **Use spot/preemptible instances for batch processing**
   - Not applicable to Cloud Run directly
   - Consider GKE for batch workloads
   - Potential savings: 60-80% on compute

---

## Cost Comparison: AWS vs GCP

| Component | AWS Monthly | GCP Monthly | Difference |
|-----------|-------------|-------------|------------|
| Compute (Lambda vs Cloud Run) | $2,200 | $1,810 | -18% |
| Storage (S3 vs GCS) | $20 | $16 | -20% |
| Database (Aurora vs Cloud SQL) | $380 | $310 | -18% |
| Vector DB (AOSS vs Vector Search) | $750 | $600 | -20% |
| LLM (Bedrock vs Vertex AI) | $1,200 | $1,045 | -13% |
| Messaging (SQS vs Pub/Sub) | $8 | $5 | -38% |
| Orchestration (Step Functions vs Workflows) | $25 | $10 | -60% |
| Networking | $300 | $262 | -13% |
| **Total** | **$4,883** | **$4,058** | **-17%** |

**Key Insight:** GCP offers approximately 17% cost savings compared to equivalent AWS infrastructure, primarily due to:
- More competitive LLM pricing (Gemini vs Claude on Bedrock)
- Lower orchestration costs (Workflows vs Step Functions)
- Better Pub/Sub pricing model

---

## Budget Alerts and Governance

### Recommended Budget Alerts

| Environment | Monthly Budget | Alert Thresholds |
|-------------|----------------|------------------|
| Development | $500 | 50%, 80%, 100% |
| Staging | $1,500 | 50%, 80%, 100% |
| Production | $6,000 | 50%, 75%, 90%, 100% |

### Cost Anomaly Detection

Enable Cloud Billing anomaly detection with:
- Sensitivity: Medium
- Alert on: >20% daily increase
- Notification: Email + Slack

### Resource Quotas

| Resource | Development | Staging | Production |
|----------|-------------|---------|------------|
| Cloud Run instances | 20 | 50 | 200 |
| Cloud SQL storage | 20 GB | 100 GB | 500 GB |
| Vector Search vectors | 50,000 | 200,000 | 1,000,000 |
| Pub/Sub messages/day | 10,000 | 50,000 | 500,000 |

---

## Appendix: Pricing References

- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud Storage Pricing](https://cloud.google.com/storage/pricing)
- [Cloud SQL Pricing](https://cloud.google.com/sql/pricing)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)
- [Vertex AI Vector Search Pricing](https://cloud.google.com/vertex-ai/docs/vector-search/pricing)
- [Pub/Sub Pricing](https://cloud.google.com/pubsub/pricing)
- [Cloud Workflows Pricing](https://cloud.google.com/workflows/pricing)

---

*This cost estimation is based on GCP pricing as of May 2026. Actual costs may vary based on usage patterns, regional pricing differences, and promotional credits. Review and update quarterly.*
