# modules/cloud_workflows/pre_formatting_workflow/variables.tf

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

variable "detect_file_type_url" {
  description = "URL of the detect file type Cloud Run service"
  type        = string
}

variable "text_extraction_url" {
  description = "URL of the text extraction Cloud Run service"
  type        = string
}

variable "text_standardize_url" {
  description = "URL of the text standardize Cloud Run service"
  type        = string
}

variable "semantic_chunking_url" {
  description = "URL of the semantic chunking Cloud Run service"
  type        = string
}

variable "identify_distinct_process_url" {
  description = "URL of the identify distinct process Cloud Run service"
  type        = string
}

variable "create_process_docs_url" {
  description = "URL of the create process docs Cloud Run service"
  type        = string
}

variable "labels" {
  description = "Labels to apply to the workflow"
  type        = map(string)
  default     = {}
}
