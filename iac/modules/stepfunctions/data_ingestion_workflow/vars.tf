# modules/stepfunctions/data_ingestion_workflow/variables.tf
variable "prefix" {
  type = string
}

variable "read_process_from_s3_lambda_arn" {
  type = string
}


variable "llm_based_tagging_lambda_arn" {
  type = string
}


variable "add_LLMTags_To_ProcessedDocs_lambda_arn" {
  type = string
}

variable "environment" {
  type = string
}