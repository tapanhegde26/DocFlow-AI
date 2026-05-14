variable "prefix" {
  description = "Name prefix for the Lambda function"
  type        = string
}

variable "environment_vars" {
  type    = map(string)
  default = {}
}


variable "environment" {
  type = string
}


variable "pdf_docker_context_relpath" {
  description = "Relative path to PDF Docker context from module root"
  type        = string
  default     = "src/pdf"
}

variable "office_docker_context_relpath" {
  description = "Relative path to Office Docker context from module root"
  type        = string
  default     = "src/office"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "REGION" {
  description = "AWS region"
  type        = string
}