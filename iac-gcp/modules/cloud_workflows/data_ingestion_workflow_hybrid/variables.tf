# modules/cloud_workflows/data_ingestion_workflow_hybrid/variables.tf

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

# Cloud Run service URLs
variable "read_from_storage_url" {
  description = "URL of the read from storage Cloud Run service"
  type        = string
}

variable "add_llm_tags_url" {
  description = "URL of the add LLM tags Cloud Run service"
  type        = string
}

# GKE service URLs
variable "llm_tagging_url" {
  description = "URL of the LLM tagging GKE service"
  type        = string
}

variable "labels" {
  description = "Labels to apply to the workflow"
  type        = map(string)
  default     = {}
}
