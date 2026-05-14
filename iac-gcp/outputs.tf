# IaC-GCP/outputs.tf

# Cloud Storage Outputs
output "raw_sop_bucket_name" {
  description = "Name of the raw SOP upload bucket"
  value       = module.raw_sop_bucket.bucket_name
}

output "text_extract_bucket_name" {
  description = "Name of the text extraction bucket"
  value       = module.text_extract_bucket.bucket_name
}

output "standardized_bucket_name" {
  description = "Name of the standardized SOP bucket"
  value       = module.standardized_bucket.bucket_name
}

output "embedding_bucket_name" {
  description = "Name of the embedding bucket"
  value       = module.embedding_bucket.bucket_name
}

# Artifact Registry
output "artifact_registry_url" {
  description = "URL of the Artifact Registry repository"
  value       = module.artifact_registry.repository_url
}

# Cloud SQL
output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.cloud_sql.connection_name
}

output "cloud_sql_private_ip" {
  description = "Cloud SQL private IP address"
  value       = module.cloud_sql.private_ip_address
}

# Vertex AI Vector Search
output "vector_search_process_index_endpoint" {
  description = "Vertex AI Vector Search index endpoint for process docs"
  value       = module.vertex_ai_vector_search.index_endpoint_id
}

output "vector_search_nonprocess_index_endpoint" {
  description = "Vertex AI Vector Search index endpoint for non-process docs"
  value       = module.vertex_ai_vector_search.nonprocess_index_endpoint_id
}

# Cloud Workflows (Hybrid)
output "pre_formatting_workflow_id" {
  description = "Pre-formatting workflow ID"
  value       = module.workflow_pre_formatting_hybrid.workflow_id
}

output "data_ingestion_workflow_id" {
  description = "Data ingestion workflow ID"
  value       = module.workflow_data_ingestion_hybrid.workflow_id
}

output "vectorindex_workflow_id" {
  description = "Vector indexing workflow ID"
  value       = module.workflow_vectorindex_hybrid.workflow_id
}

# Pub/Sub Topics
output "pre_formatting_topic_id" {
  description = "Pre-formatting Pub/Sub topic ID"
  value       = module.pubsub_pre_formatting.topic_id
}

output "data_ingestion_topic_id" {
  description = "Data ingestion Pub/Sub topic ID"
  value       = module.pubsub_data_ingestion.topic_id
}

output "vector_process_topic_id" {
  description = "Vector process Pub/Sub topic ID"
  value       = module.pubsub_vector_process.topic_id
}

output "vector_nonprocess_topic_id" {
  description = "Vector non-process Pub/Sub topic ID"
  value       = module.pubsub_vector_nonprocess.topic_id
}

# VPC
output "vpc_network_id" {
  description = "VPC network ID"
  value       = module.vpc.network_id
}

output "vpc_connector_id" {
  description = "VPC connector ID for serverless services"
  value       = module.vpc.vpc_connector_id
}

# API Gateway
output "api_gateway_url" {
  description = "API Gateway URL"
  value       = module.api_gateway.gateway_url
}

# Vertex AI Search
output "vertex_ai_search_process_datastore_id" {
  description = "Vertex AI Search datastore ID for process docs"
  value       = module.vertex_ai_search.process_datastore_id
}

output "vertex_ai_search_nonprocess_datastore_id" {
  description = "Vertex AI Search datastore ID for non-process docs"
  value       = module.vertex_ai_search.nonprocess_datastore_id
}
