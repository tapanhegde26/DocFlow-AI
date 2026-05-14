# modules/cloud_storage/raw_sop_bucket/variables.tf

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "bucket_name" {
  description = "Name of the bucket"
  type        = string
}

variable "location" {
  description = "Location for the bucket"
  type        = string
}

variable "force_destroy" {
  description = "Allow bucket to be destroyed even if not empty"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to the bucket"
  type        = map(string)
  default     = {}
}

variable "pubsub_topic_id" {
  description = "Pub/Sub topic ID for notifications"
  type        = string
  default     = ""
}
