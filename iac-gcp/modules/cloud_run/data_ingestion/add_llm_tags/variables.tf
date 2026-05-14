# modules/cloud_run/data_ingestion/add_llm_tags/variables.tf

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

variable "standardized_bucket" {
  description = "Standardized SOP bucket name"
  type        = string
}

variable "db_secret_id" {
  description = "Secret Manager secret ID for database credentials"
  type        = string
}

variable "db_connection_name" {
  description = "Cloud SQL connection name"
  type        = string
}
