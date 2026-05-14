# modules/stepfunctions/vectorindex_workflow/variables.tf
variable "prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "read_s3_lambda_arn" {
  type = string
}

variable "chunk_lambda_arn" {
  type = string
}

variable "embed_lambda_arn" {
  type = string
}

variable "store_lambda_arn" {
  type = string
}

variable "bedrock_sync_lambda_arn" {
  type = string
}