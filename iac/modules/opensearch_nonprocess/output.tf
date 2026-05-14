output "collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.collection.arn
}

output "collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.collection.collection_endpoint
}

output "collection_id" {
  description = "ID of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.collection.id
}

output "collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.collection.name
}

output "index_name" {
  description = "Name of the created index"
  value       = var.index_name
}

output "index_creation_complete" {
  description = "Marker to indicate index creation is complete"
  value       = null_resource.create_opensearch_index.id
}
