output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  value       = awscc_bedrock_knowledge_base.bedrock_knowledge_base.id
}

output "knowledge_base_arn" {
  description = "ARN of the Bedrock Knowledge Base"
  value       = awscc_bedrock_knowledge_base.bedrock_knowledge_base.knowledge_base_arn
}

output "bedrock_kb_role_arn" {
  description = "ARN of the Bedrock Knowledge Base IAM role"
  value       = aws_iam_role.bedrock_kb.arn
}

output "data_source_id" {
  description = "ID of the Bedrock Data Source"
  value       = awscc_bedrock_data_source.tsh-industries_kb_datasource.id
}

output "bedrock_sync_lambda_arn" {
  description = "ARN of the Lambda function that syncs Bedrock Knowledge Base"
  value       = aws_lambda_function.bedrock_sync.arn
}

output "bedrock_sync_lambda_name" {
  description = "Name of the Lambda function that syncs Bedrock Knowledge Base"
  value       = aws_lambda_function.bedrock_sync.function_name
}

