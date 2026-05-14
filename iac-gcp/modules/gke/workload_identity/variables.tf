# modules/gke/workload_identity/variables.tf

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

variable "k8s_namespace" {
  description = "Kubernetes namespace for the service account"
  type        = string
  default     = "genai-pipeline"
}

variable "k8s_service_account_name" {
  description = "Kubernetes service account name"
  type        = string
  default     = "genai-workload-sa"
}
