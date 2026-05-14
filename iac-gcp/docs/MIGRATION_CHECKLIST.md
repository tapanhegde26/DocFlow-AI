# Migration Checklist: AWS to GCP

## Pre-Migration

- [ ] Review AWS architecture and document all components
- [ ] Identify GCP equivalent services
- [ ] Estimate GCP costs
- [ ] Create GCP project and enable billing
- [ ] Set up GCP IAM and service accounts
- [ ] Configure Terraform backend (GCS bucket)

## Phase 1: Foundation Infrastructure

- [ ] Enable required GCP APIs
- [ ] Create VPC and subnets
- [ ] Configure VPC connector for serverless
- [ ] Set up Cloud NAT for outbound access
- [ ] Create Cloud Storage buckets
  - [ ] raw-sop-upload
  - [ ] text-extraction
  - [ ] sop-standardized
  - [ ] sop-embedding
  - [ ] nonprocess-sop-embedding
- [ ] Create Artifact Registry repository
- [ ] Set up Secret Manager secrets

## Phase 2: Event and Messaging Layer

- [ ] Create Pub/Sub topics
  - [ ] pre-formatting-topic
  - [ ] data-ingestion-topic
  - [ ] vector-process-topic
  - [ ] vector-nonprocess-topic
- [ ] Create Pub/Sub subscriptions
- [ ] Configure dead-letter topics
- [ ] Set up Eventarc triggers
  - [ ] Raw SOP upload trigger
  - [ ] Process documents trigger
  - [ ] Tagged processes trigger
  - [ ] Non-process documents trigger

## Phase 3: Compute Layer

- [ ] Migrate Lambda code to Cloud Run
  - [ ] Update Python imports (boto3 → google-cloud-*)
  - [ ] Update environment variables
  - [ ] Create Dockerfiles
  - [ ] Build and push container images
- [ ] Deploy Cloud Run services
  - [ ] detect-file-type
  - [ ] text-extraction
  - [ ] text-standardize
  - [ ] semantic-chunking
  - [ ] identify-distinct-process
  - [ ] create-process-docs
  - [ ] read-from-storage
  - [ ] llm-tagging
  - [ ] add-llm-tags
  - [ ] chunk-sop
  - [ ] generate-embedding
  - [ ] store-to-vector-db
- [ ] Create Cloud Workflows
  - [ ] pre-formatting-workflow
  - [ ] data-ingestion-workflow
  - [ ] vectorindex-workflow
  - [ ] vectorindex-nonprocess-workflow

## Phase 4: AI/ML Layer

- [ ] Set up Vertex AI Vector Search
  - [ ] Create process index
  - [ ] Create non-process index
  - [ ] Deploy indexes to endpoints
- [ ] Configure Vertex AI for embeddings
  - [ ] Test text-embedding-004 model
  - [ ] Verify embedding dimensions match
- [ ] Configure Vertex AI for LLM
  - [ ] Enable Gemini 1.5 Pro or Claude
  - [ ] Test prompt compatibility
- [ ] Set up Vertex AI Search (optional RAG)
  - [ ] Create process datastore
  - [ ] Create non-process datastore
  - [ ] Configure search engines

## Phase 5: Database and API Layer

- [ ] Deploy Cloud SQL PostgreSQL
  - [ ] Configure private IP
  - [ ] Set up backup schedule
  - [ ] Create database and user
- [ ] Migrate database schema
  - [ ] Export schema from Aurora
  - [ ] Import to Cloud SQL
  - [ ] Verify data types compatibility
- [ ] Set up API Gateway
  - [ ] Create API config
  - [ ] Configure authentication
  - [ ] Set up CORS
- [ ] Configure Cloud CDN (if needed)

## Phase 6: Testing and Validation

- [ ] Unit tests for GCP client code
- [ ] Integration tests for each workflow
- [ ] End-to-end pipeline test
- [ ] Performance benchmarking
- [ ] Cost analysis
- [ ] Security review
- [ ] Documentation update

## Post-Migration

- [ ] Set up monitoring dashboards
- [ ] Configure alerting policies
- [ ] Create runbooks for operations
- [ ] Train team on GCP tools
- [ ] Plan AWS resource decommissioning
- [ ] Update CI/CD pipelines

## Code Changes Summary

### Python SDK Replacements

| AWS | GCP |
|-----|-----|
| `boto3.client('s3')` | `google.cloud.storage.Client()` |
| `boto3.client('sqs')` | `google.cloud.pubsub_v1.PublisherClient()` |
| `boto3.client('secretsmanager')` | `google.cloud.secretmanager.SecretManagerServiceClient()` |
| `boto3.client('bedrock-runtime')` | `vertexai.generative_models.GenerativeModel()` |
| `opensearchpy.OpenSearch()` | `google.cloud.aiplatform.MatchingEngineIndexEndpoint()` |

### Environment Variable Changes

| AWS | GCP |
|-----|-----|
| `AWS_REGION` | `REGION` |
| `BEDROCK_MODEL_ID` | `VERTEX_MODEL_ID` |
| `AOSS_ENDPOINT` | `VECTOR_SEARCH_INDEX_ENDPOINT` |
| `DB_SECRET_NAME` | `DB_SECRET_ID` |
| `DB_CLUSTER_ARN` | `DB_CONNECTION_NAME` |

### Terraform Provider Changes

| AWS | GCP |
|-----|-----|
| `hashicorp/aws` | `hashicorp/google` |
| `hashicorp/awscc` | `hashicorp/google-beta` |
| `opensearch-project/opensearch` | (not needed) |

## Rollback Plan

1. Keep AWS infrastructure running during migration
2. Use feature flags to switch between AWS and GCP
3. Maintain data sync between environments
4. Document rollback procedures for each component
5. Test rollback procedures before go-live
