# modules/cloud_run/vectorization/store_to_vector_db/variables.tf

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

variable "vector_search_index_endpoint" {
  description = "Vertex AI Vector Search index endpoint"
  type        = string
}

variable "vector_search_index_id" {
  description = "Vertex AI Vector Search index ID"
  type        = string
}
