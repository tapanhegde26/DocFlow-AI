# outputs.tf

# Root outputs (only RDS + shared)
output "writer_endpoint" {
  description = "Aurora writer endpoint (read/write)"
  value       = module.rds_postgres.writer_endpoint
}

output "reader_endpoint" {
  description = "Aurora reader endpoint (read-only)"
  value       = module.rds_postgres.reader_endpoint
}

output "db_name" {
  description = "Aurora database name"
  value       = module.rds_postgres.db_name
}

output "master_username" {
  description = "Master username"
  value       = module.rds_postgres.master_username
}

output "master_secret_arn" {
  description = "Secrets Manager ARN for the master credential"
  value       = module.rds_postgres.master_secret_arn
}


# --- API Gateway v2 information ---
output "api_gateway" {
  description = "HTTP API details"
  value = {
    api_id        = module.api_gateway.api_id
    api_endpoint  = module.api_gateway.api_endpoint
    authorizer_id = module.api_gateway.authorizer_id
    routes        = module.api_gateway.routes
  }
}

# --- Cloudfront distribution ---
# Chat UI CDN
output "chat_ui_cdn" {
  value = {
    distribution_id        = module.chat_ui_cdn.distribution_id
    domain_name            = module.chat_ui_cdn.distribution_domain_name
    origin_bucket          = module.chat_ui_cdn.origin_bucket_name
    logs_bucket            = module.chat_ui_cdn.logs_bucket_name
    public_access_block    = module.chat_ui_cdn.origin_bucket_public_access_block
    origin_bucket_policy   = module.chat_ui_cdn.origin_bucket_policy_json
    cloudfront_source_arn  = module.chat_ui_cdn.cloudfront_source_arn
    waf_arn                = module.chat_ui_cdn.waf_arn
    cloudwatch_log_group   = module.chat_ui_cdn.cloudwatch_log_group
  }
}

# Review UI CDN
output "review_ui_cdn" {
  value = {
    distribution_id        = module.review_ui_cdn.distribution_id
    domain_name            = module.review_ui_cdn.distribution_domain_name
    origin_bucket          = module.review_ui_cdn.origin_bucket_name
    logs_bucket            = module.review_ui_cdn.logs_bucket_name
    public_access_block    = module.review_ui_cdn.origin_bucket_public_access_block
    origin_bucket_policy   = module.review_ui_cdn.origin_bucket_policy_json
    cloudfront_source_arn  = module.review_ui_cdn.cloudfront_source_arn
    waf_arn                = module.review_ui_cdn.waf_arn
    cloudwatch_log_group   = module.review_ui_cdn.cloudwatch_log_group
  }
}


output "chat_app_log_group" {
  value = aws_cloudwatch_log_group.chat_app_logs.name
}

output "chat_audit_log_group" {
  value = aws_cloudwatch_log_group.chat_audit_logs.name
}


output "opensearch_collection_endpoint" {
  value = module.opensearch_knn.collection_endpoint
}

output "knowledge_base_id" {
  value = module.bedrock_knowledge_base_process_docs.knowledge_base_id
}

output "knowledge_base_arn" {
  value = module.bedrock_knowledge_base_process_docs.knowledge_base_arn
}

output "rds_data_api_policy_arn" {
  value = aws_iam_policy.rds_data_api_policy.arn
}

output "secrets_manager_read_policy_arn" {
  value = aws_iam_policy.secrets_manager_read_policy.arn
}