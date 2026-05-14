# modules/stepfunctions/data_ingestion_workflow/variables.tf
variable "prefix" {
  type = string
}

variable "detect_file_type_lambda_arn" {
  type = string
}

variable "pdf_extract_lambda_arn" {
  description = "ARN of the PDF text extraction Lambda"
  type        = string
}

variable "office_extract_lambda_arn" {
  description = "ARN of the Office text extraction Lambda"
  type        = string
}

variable "duplicate_detection_lambda_arn" {
  description = "ARN of the Office text extraction Lambda"
  type        = string
}


variable "text_standardize_lambda_arn" {
  type = string
}

variable "semantic_chunking_lambda_arn" {
  type = string
}

variable "identify_distinct_process_lambda_arn" {
  type = string
}

variable "create_process_docs_lambda_arn" {
  type = string
}

variable "environment" {
  type = string
}

variable "environment_vars" {
  type    = map(string)
  default = {}
}
