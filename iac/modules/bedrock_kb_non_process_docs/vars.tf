variable "prefix" {
  description = "Name of the knowledge base"
  type        = string
}

variable "description" {
  description = "Description of the KB"
  type        = string
  default     = "Bedrock KB with OpenSearch backend"
}


variable "s3_bucket_arn" {
  description = "ARN of the s3 bucket"
  type        = string
}


variable "environment" {
  description = "env for naming"
  type        = string
}

variable "existing_opensearch_collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  type        = string
}

variable "existing_opensearch_index_name" {
  description = "Name of the OpenSearch Serverless index"
  type        = string
}

variable "opensearch_index_creation_marker" {
  description = "Marker to ensure index is created before KB"
  type        = string
  default     = ""
}