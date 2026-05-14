# modules/s3/standardized_bucket/variables.tf
variable "bucket_name" {
  type        = string
  description = "The name of the standardized S3 bucket"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
}