variable "encryption_policy_name" {
  description = "Name of the encryption policy"
  type        = string
}

variable "network_policy_name" {
  description = "Name of the network policy"
  type        = string
}

variable "data_access_policy_name" {
  description = "Name of the data access policy"
  type        = string
}

variable "collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  type        = string
}

variable "collection_type" {
  description = "Type of the collection (VECTORSEARCH or SEARCH)"
  type        = string
  default     = "VECTORSEARCH"
}

variable "principals" {
  description = "List of IAM principal ARNs to grant access"
  type        = list(string)
  default     = []
}

variable "bedrock_kb_role_arn" {
  description = "ARN of the Bedrock Knowledge Base IAM role"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "index_name" {
  description = "Name of the OpenSearch index to create"
  type        = string
}
