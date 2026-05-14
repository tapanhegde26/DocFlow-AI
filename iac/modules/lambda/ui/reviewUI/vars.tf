variable "prefix" {
  description = "Prefix for resource naming resources within this module."
  type        = string
}

variable "environment" {
  description = "The deployment environment tag."
  type        = string
}

variable "app_log_group" {
  description = "CloudWatch Log Group for reviewUI application logs"
  type        = string
}

variable "audit_log_group" {
  description = "CloudWatch Log Group for reviewUI audit logs"
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
  default     = "review-handler"
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
  description = "Lambda timeout (seconds)"
  type        = number
  default     = 900
}

variable "memory_size" {
  description = "Lambda memory (MB)"
  type        = number
  default     = 512
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention (days)"
  type        = number
  default     = 14
}

variable "vpc_id" {
  description = "VPC where Lambda runs"
  type        = string
  default     = null
}
variable "vpc_subnet_ids" {
  description = "Private subnet IDs for Lambda ENIs"
  type        = list(string)
  default     = null
}

variable "vpc_security_group_ids" {
  description = "Additional SGs to attach (module also creates one)"
  type        = list(string)
  default     = []
}

# Variables to pass the ARNs of the secret/parameters for IAM policy permissions
variable "rds_secret_arn" {
  description = "The ARN of the AWS Secrets Manager secret storing the DB creds(for IAM policy)."
  type        = string
}

variable "rds_cluster_arn" {
  description = "ARN of the RDS Cluster for Data API"
  type        = string
}

variable "rds_data_api_policy_arn" {
  description = "ARN of the RDS Policy for Data API"
  type        = string
}

variable "secrets_manager_read_policy_arn" {
  description = "ARN of the RDS Policy for Data API"
  type        = string
}

variable "s3_bucket_names" {
  description = "List of S3 buckets this Lambda can read from"
  type        = list(string)
}