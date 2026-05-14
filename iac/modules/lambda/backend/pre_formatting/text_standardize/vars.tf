variable "prefix" {
  description = "Lambda function name prefix"
  type        = string
}

variable "environment_vars" {
  type    = map(string)
  default = {}
}

variable "use_claude" {
  description = "Enable Claude for standardization"
  type        = bool
  default     = false
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