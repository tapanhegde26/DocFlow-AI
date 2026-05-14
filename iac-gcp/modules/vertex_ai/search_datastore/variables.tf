# modules/vertex_ai/search_datastore/variables.tf

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

variable "standardized_bucket" {
  description = "Standardized SOP bucket name"
  type        = string
}

variable "text_extract_bucket" {
  description = "Text extraction bucket name"
  type        = string
}
