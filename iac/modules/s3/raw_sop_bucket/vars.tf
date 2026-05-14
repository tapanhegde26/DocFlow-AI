# modules/s3/upload_bucket/variables.tf
variable "bucket_name" {
  type        = string
  description = "The name of the upload S3 bucket"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
}