variable "prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "description" {
  description = "Description for the Bedrock Knowledge Base"
  type        = string
}

variable "existing_opensearch_collection_name" {
  description = "Name of the existing OpenSearch Serverless collection"
  type        = string
}

variable "existing_opensearch_index_name" {
  description = "Name of the existing OpenSearch index"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket containing documents"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "opensearch_index_creation_marker" {
  description = "Marker to ensure index is created before KB"
  type        = string
  default     = ""
}
