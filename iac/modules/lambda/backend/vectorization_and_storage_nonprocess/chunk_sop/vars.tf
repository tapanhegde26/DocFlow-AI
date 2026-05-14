variable "prefix" {
  description = "Lambda function prefix"
  type        = string
}


variable "environment" {
  type = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "ecr_repository_url" {
  description = "URL of the ECR repository"
  type        = string
}