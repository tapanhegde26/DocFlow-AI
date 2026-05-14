variable "prefix" {
  description = "Prefix for resource naming resources within this module."
  type        = string
}

variable "environment" {
  description = "The deployment environment tag."
  type        = string
}

variable "app_log_group" {
  description = "CloudWatch Log Group for chatUI application logs"
  type        = string
}

variable "audit_log_group" {
  description = "CloudWatch Log Group for chatUI audit logs"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "The AWS region where resources will be deployed."
  type        = string
  default     = "ca-central-1"
}

variable "function_name" {
  description = "Function name suffix"
  type        = string
  default     = "chat-handler"
}

variable "docker_context_relpath" {
  description = "Relative path to Docker build context"
  type        = string
  default     = "ui"
}

variable "image_tag" {
  description = "Docker image tag to build/push and deploy"
  type        = string
  default     = "latest"
}

variable "architectures" {
  description = "Lambda architectures"
  type        = list(string)
  default     = ["arm64"]
}

variable "timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention (days)"
  type        = number
  default     = 14
}

variable "vpc_id" {
  description = "VPC ID for Lambda (optional)"
  type        = string
  default     = null
}

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs for Lambda (optional)"
  type        = list(string)
  default     = null
}

variable "vpc_security_group_ids" {
  description = "Additional SGs to attach (module also creates one)"
  type        = list(string)
  default     = []
}

variable "s3_bucket_names" {
  description = "List of S3 buckets this Lambda can read from"
  type        = list(string)
}
