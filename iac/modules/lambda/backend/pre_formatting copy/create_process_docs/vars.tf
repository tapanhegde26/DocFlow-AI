variable "prefix" {
  description = "Name prefix for the Lambda function"
  type        = string
}

variable "environment_vars" {
  type    = map(string)
  default = {}
}


variable "environment" {
  type = string
}

variable "output_bucket" {
  description = "The S3 bucket where the Lambda function writes processed files"
  type        = string
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository"
  type        = string
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