# modules/api_gateway/variables.tf

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
  description = "Service account email for API Gateway"
  type        = string
}

variable "chat_handler_url" {
  description = "URL of the chat handler Cloud Run service"
  type        = string
  default     = ""
}

variable "review_handler_url" {
  description = "URL of the review handler Cloud Run service"
  type        = string
  default     = ""
}

variable "health_check_url" {
  description = "URL for health check endpoint"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
