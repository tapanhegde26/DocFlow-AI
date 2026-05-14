variable "site_name" {
  description = "Short site name, e.g., chat-ui or review-ui"
  type        = string
}

variable "environment" {
  description = "Environment tag value"
  type        = string
}

variable "bucket_name" {
  description = "S3 origin bucket name (if not provided, one will be generated)"
  type        = string
  default     = ""
}

variable "logs_bucket_name" {
  description = "S3 bucket for CloudFront standard logs (if not provided, one will be generated)"
  type        = string
  default     = ""
}

variable "default_root_object" {
  description = "Default root object"
  type        = string
  default     = "index.html"
}

variable "price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_200, PriceClass_100)"
  type        = string
  default     = "PriceClass_100"
}

variable "comment" {
  description = "Distribution comment"
  type        = string
  default     = ""
}

variable "prefix" {
  description = "Name prefix for the Lambda function"
  type        = string
}
