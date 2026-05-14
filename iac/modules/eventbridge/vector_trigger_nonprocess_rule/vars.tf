variable "prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "bucket_name" {
  description = "Name of the standardized S3 bucket"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the vector indexing SQS queue"
  type        = string
}

variable "sqs_queue_url" {
  description = "URL of the vector indexing SQS queue"
  type        = string
}

variable "environment" {
  description = "env for naming"
  type        = string
}

variable "object_key_filter" {
  description = "S3 object key filter patterns"
  type = list(object({
    prefix = optional(string)
    suffix = optional(string)
  }))
  default = null
}

variable "dlq_arn" {
  description = "ARN of the dead letter queue"
  type        = string
  default     = null
}