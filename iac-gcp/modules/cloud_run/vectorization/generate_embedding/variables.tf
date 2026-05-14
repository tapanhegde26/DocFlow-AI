# modules/cloud_run/vectorization/generate_embedding/variables.tf

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

variable "repository_url" {
  description = "Artifact Registry repository URL"
  type        = string
}

variable "service_account" {
  description = "Service account email"
  type        = string
}

variable "vpc_connector_id" {
  description = "VPC connector ID"
  type        = string
}

variable "embedding_bucket" {
  description = "Embedding output bucket name"
  type        = string
}

variable "vertex_embedding_model" {
  description = "Vertex AI embedding model ID"
  type        = string
  default     = "text-embedding-004"
}
