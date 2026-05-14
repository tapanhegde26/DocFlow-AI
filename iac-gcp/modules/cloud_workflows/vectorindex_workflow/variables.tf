# modules/cloud_workflows/vectorindex_workflow/variables.tf

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

variable "service_account" {
  description = "Service account email for workflow execution"
  type        = string
}

variable "read_sop_url" {
  description = "URL of the read SOP Cloud Run service"
  type        = string
}

variable "chunk_sop_url" {
  description = "URL of the chunk SOP Cloud Run service"
  type        = string
}

variable "generate_embed_url" {
  description = "URL of the generate embedding Cloud Run service"
  type        = string
}

variable "store_vector_url" {
  description = "URL of the store to vector DB Cloud Run service"
  type        = string
}

variable "labels" {
  description = "Labels to apply to the workflow"
  type        = map(string)
  default     = {}
}
