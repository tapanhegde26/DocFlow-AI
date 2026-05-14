variable "repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

variable "image_tag_mutability" {
  description = "The tag mutability setting for the repository"
  type        = string
  default     = "MUTABLE"
  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "Image tag mutability must be either MUTABLE or IMMUTABLE."
  }
}

variable "force_delete" {
  description = "If true, will delete the repository even if it contains images"
  type        = bool
  default     = false
}

variable "scan_on_push" {
  description = "Indicates whether images are scanned after being pushed to the repository"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "AI-KB"
}

variable "additional_tags" {
  description = "Additional tags to apply to the repository"
  type        = map(string)
  default     = {}
}

variable "enable_lifecycle_policy" {
  description = "Whether to enable lifecycle policy"
  type        = bool
  default     = true
}

variable "lifecycle_rule_priority" {
  description = "Priority of the lifecycle rule"
  type        = number
  default     = 1
}

variable "lifecycle_rule_description" {
  description = "Description of the lifecycle rule"
  type        = string
  default     = "Keep last 30 images"
}

variable "lifecycle_tag_status" {
  description = "Tag status for lifecycle rule"
  type        = string
  default     = "any"
}

variable "lifecycle_count_type" {
  description = "Count type for lifecycle rule"
  type        = string
  default     = "imageCountMoreThan"
}

variable "lifecycle_count_number" {
  description = "Count number for lifecycle rule"
  type        = number
  default     = 30
}

variable "prefix" {
  type = string
}
