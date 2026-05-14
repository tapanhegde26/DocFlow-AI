# iac/modules/lambda/backend/data_ingestion/add_llm_tags_to_s3/variables.tf

variable "prefix" {
  description = "A unique prefix for naming resources within this module."
  type        = string
}

variable "environment" {
  description = "The deployment environment tag."
  type        = string
}

variable "environment_variables" {
  description = "A map of additional environment variables to pass to the Lambda function (excluding DB credential names, unless explicitly merged)."
  type        = map(string)
  default     = {}
}

variable "s3_bucket_name" {
  description = "The name of the S3 bucket where documents are stored and tagged."
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

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository"
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
