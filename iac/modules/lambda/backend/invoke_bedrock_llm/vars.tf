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

variable "opensearch_collection_name" {
  type = string
}