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
  description = "Name of the OpenSearch collection"
  type        = string
}

variable "collection_type" {
  description = "Type of OpenSearch collection (VECTORSEARCH or SEARCH)"
  type        = string
}

variable "environment" {
  type = string
}

variable "principals" {
  description = "List of AWS Principals (ARNS) allowed to access OpenSearch collection"
  type        = list(string)
}

variable "index_name" {
  description = "Name of the OpenSearch index to create"
  type        = string
  default     = "vector-index"
}

variable "bedrock_kb_role_arn" {
  description = "ARN of the Bedrock Knowledge Base IAM role"
  type        = string
  default     = ""
}


