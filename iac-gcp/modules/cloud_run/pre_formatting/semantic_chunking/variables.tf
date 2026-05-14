# modules/cloud_run/pre_formatting/semantic_chunking/variables.tf

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

variable "text_extract_bucket" {
  description = "Text extraction bucket name"
  type        = string
}

variable "vertex_model_id" {
  description = "Vertex AI model ID for semantic chunking"
  type        = string
  default     = "gemini-1.5-pro"
}
