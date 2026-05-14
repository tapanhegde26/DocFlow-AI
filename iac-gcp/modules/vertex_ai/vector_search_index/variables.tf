# modules/vertex_ai/vector_search_index/variables.tf

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "embedding_dimension" {
  description = "Dimension of the embedding vectors"
  type        = number
  default     = 768
}

variable "vpc_network" {
  description = "VPC network for private endpoints"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
