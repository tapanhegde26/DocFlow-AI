# modules/eventarc/pre_formatting_trigger/variables.tf

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

variable "workflow_trigger_service" {
  description = "Cloud Run service name for workflow trigger"
  type        = string
  default     = ""
}

variable "use_pubsub_destination" {
  description = "Use Pub/Sub as destination instead of Cloud Run"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
