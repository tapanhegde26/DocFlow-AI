# Testing and Validation Guide

This document provides guidance for testing the GCP GenAI pipeline after migration from AWS.

## Pre-Deployment Validation

### 1. Terraform Validation

```bash
cd iac-gcp

# Format check
terraform fmt -check -recursive

# Validate configuration
terraform validate

# Plan review
terraform plan -out=tfplan
```

### 2. Container Image Validation

```bash
# Test container locally
docker run -p 8080:8080 \
  -e GCP_PROJECT=test-project \
  -e REGION=us-central1 \
  us-central1-docker.pkg.dev/PROJECT/REPO/detect-file-type:latest

# Health check
curl http://localhost:8080/health
```

## End-to-End Testing

### Test 1: Pre-Format Workflow

```bash
# Upload test document to raw SOP bucket
gsutil cp test_document.pdf gs://BUCKET-raw-sop-upload/

# Monitor workflow execution
gcloud workflows executions list \
  --workflow=WORKFLOW_NAME \
  --location=us-central1

# Check output in text extraction bucket
gsutil ls gs://BUCKET-text-extraction/
```

### Test 2: Data Ingestion Workflow

```bash
# Verify process documents created
gsutil ls gs://BUCKET-sop-standardized/processes/

# Check tagged processes
gsutil ls gs://BUCKET-sop-standardized/tagged_processes/
```

### Test 3: Vectorization Workflow

```bash
# Verify embeddings generated
gsutil ls gs://BUCKET-sop-embedding/

# Query Vector Search index
python -c "
from google.cloud import aiplatform
aiplatform.init(project='PROJECT_ID', location='us-central1')
endpoint = aiplatform.MatchingEngineIndexEndpoint('ENDPOINT_ID')
# Test query
"
```

### Test 4: RAG Query

```bash
# Test chat endpoint
curl -X POST https://API_GATEWAY_URL/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "query": "What is the process for handling customer complaints?",
    "user_id": "test-user",
    "use_agent": false
  }'
```

## Performance Benchmarking

### Latency Tests

```python
import time
import statistics
from common.gcp_clients import get_vertex_ai_client

client = get_vertex_ai_client()

# Embedding latency
latencies = []
for _ in range(100):
    start = time.time()
    client.generate_embedding("Test text for embedding")
    latencies.append(time.time() - start)

print(f"Embedding Latency - Mean: {statistics.mean(latencies):.3f}s, P95: {statistics.quantiles(latencies, n=20)[18]:.3f}s")

# LLM latency
latencies = []
for _ in range(20):
    start = time.time()
    client.generate_text("Summarize this document in 3 sentences.")
    latencies.append(time.time() - start)

print(f"LLM Latency - Mean: {statistics.mean(latencies):.3f}s, P95: {statistics.quantiles(latencies, n=20)[18]:.3f}s")
```

### Throughput Tests

```python
import concurrent.futures
from common.gcp_clients import get_storage_client

storage = get_storage_client()

def upload_file(i):
    storage.put_object(
        bucket="test-bucket",
        key=f"test-{i}.txt",
        body=b"Test content " * 1000
    )
    return i

# Concurrent uploads
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    start = time.time()
    futures = [executor.submit(upload_file, i) for i in range(1000)]
    concurrent.futures.wait(futures)
    elapsed = time.time() - start

print(f"Throughput: {1000/elapsed:.2f} uploads/second")
```

## Cost Analysis

### Estimated Monthly Costs (Development Environment)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| Cloud Run | 10 services, min 0 instances | $50-100 |
| Cloud Storage | 100GB, Standard | $2-5 |
| Pub/Sub | 1M messages/month | $1-2 |
| Cloud SQL | db-custom-2-4096, ZONAL | $50-80 |
| Vertex AI Vector Search | 2 indexes, auto-scaling | $100-200 |
| Vertex AI (LLM) | Gemini 1.5 Pro, 1M tokens | $10-30 |
| Vertex AI (Embeddings) | 10M tokens | $1-2 |
| Cloud Workflows | 10K executions | $1-2 |
| Eventarc | Included with Pub/Sub | $0 |
| Secret Manager | 10 secrets, 1K accesses | $0.50 |
| VPC/Networking | NAT, Connector | $30-50 |
| **Total** | | **$250-500/month** |

### Cost Optimization Tips

1. **Cloud Run**
   - Set `min_instance_count = 0` for dev
   - Use CPU throttling for non-critical services

2. **Cloud SQL**
   - Use `db-f1-micro` for dev ($10/month)
   - Enable auto-pause for dev instances

3. **Vertex AI Vector Search**
   - Use `SHARD_SIZE_SMALL` for dev
   - Consider AlloyDB with pgvector for cost savings

4. **Vertex AI LLM**
   - Use Gemini 1.5 Flash for non-critical tasks (10x cheaper)
   - Implement caching for repeated queries

## Comparison with AWS Costs

| Component | AWS Monthly | GCP Monthly | Difference |
|-----------|-------------|-------------|------------|
| Compute (Lambda/Cloud Run) | $100 | $75 | -25% |
| Storage (S3/GCS) | $5 | $4 | -20% |
| Queue (SQS/Pub/Sub) | $2 | $2 | 0% |
| Database (Aurora/Cloud SQL) | $80 | $60 | -25% |
| Vector DB (AOSS/Vector Search) | $200 | $150 | -25% |
| LLM (Bedrock/Vertex AI) | $50 | $30 | -40% |
| **Total** | **$437** | **$321** | **-27%** |

*Note: Costs vary based on usage patterns and region.*

## Monitoring and Alerting

### Set Up Alerts

```bash
# Create alert policy for Cloud Run errors
gcloud alpha monitoring policies create \
  --display-name="Cloud Run Error Rate" \
  --condition-display-name="Error rate > 1%" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=0.01 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=CHANNEL_ID
```

### Log-Based Metrics

```bash
# Create metric for workflow failures
gcloud logging metrics create workflow_failures \
  --description="Count of workflow execution failures" \
  --log-filter='resource.type="workflows.googleapis.com/Workflow" severity>=ERROR'
```

## Rollback Procedures

### Terraform Rollback

```bash
# View state history
terraform state list

# Rollback to previous state
terraform apply -target=module.MODULE_NAME -var="image_tag=previous-version"
```

### Database Rollback

```bash
# Point-in-time recovery
gcloud sql instances clone SOURCE_INSTANCE CLONE_INSTANCE \
  --point-in-time="2024-01-15T10:00:00Z"
```

## Checklist

- [ ] All Terraform modules validated
- [ ] Container images built and pushed
- [ ] VPC and networking configured
- [ ] Service accounts created with correct permissions
- [ ] Secrets stored in Secret Manager
- [ ] Cloud SQL database initialized
- [ ] Vertex AI Vector Search indexes created
- [ ] Eventarc triggers configured
- [ ] Cloud Workflows deployed
- [ ] API Gateway configured
- [ ] End-to-end test passed
- [ ] Monitoring and alerting set up
- [ ] Documentation updated
