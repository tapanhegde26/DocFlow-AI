# modules/service_accounts/cloud_run/variables.tf

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "short_prefix" {
  description = "Short prefix for service account IDs (max 20 chars to allow suffix)"
  type        = string
}
