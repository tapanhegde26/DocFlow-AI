variable "prefix" {
  description = "Name prefix for the Lambda function"
  type        = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}
variable "environment" {
  type = string
}

variable "s3_bucket_id" {
  description = "ID of the S3 bucket"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
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