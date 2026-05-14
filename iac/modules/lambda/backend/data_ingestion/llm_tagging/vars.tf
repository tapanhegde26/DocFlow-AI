
# modules/lambda/llm_tagging/variables.tf
variable "prefix" {
  type = string
}

variable "handler" {
  type    = string
  default = "app.handler"
}

variable "runtime" {
  type    = string
  default = "python3.11"
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "environment" {
  type = string
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository"
  type        = string
}