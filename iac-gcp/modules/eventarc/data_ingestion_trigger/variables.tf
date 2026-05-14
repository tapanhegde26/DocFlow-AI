# modules/eventarc/data_ingestion_trigger/variables.tf

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

variable "bucket_name" {
  description = "Source bucket name to monitor"
  type        = string
}

variable "pubsub_topic_id" {
  description = "Pub/Sub topic ID for destination"
  type        = string
}

variable "service_account" {
  description = "Service account email for the trigger"
  type        = string
}

variable "object_prefix" {
  description = "Object prefix filter (e.g., 'processes/')"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
