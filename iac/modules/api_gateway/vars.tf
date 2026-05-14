variable "prefix" {
  description = "Prefix name for all resources"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ca-central-1"
}

variable "review_lambda_arn" {
  description = "Path to the ZIP file for Review Lambda function"
  type        = string
}

variable "review_lambda_invoke_arn" {
  description = "Invoke ARN for the Review Lambda"
  type        = string
}

variable "chat_lambda_arn" {
  description = "Path to the ZIP file for Chat Lambda function"
  type        = string
}

variable "chat_lambda_invoke_arn" {
  description = "Invoke ARN for the Chat Lambda"
  type        = string
}


# JWT authorizer config
variable "jwt_issuer" {
  description = "OIDC issuer URL"
  type        = string
}

variable "jwt_audiences" {
  description = "Allowed audiences (e.g., Cognito App Client ID(s))"
  type        = list(string)
}

# CORS (tune for prod)
variable "allow_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "allow_methods" {
  description = "CORS allowed methods"
  type        = list(string)
  default     = ["GET", "POST", "OPTIONS"]
}

variable "allow_headers" {
  description = "CORS allowed headers"
  type        = list(string)
  default     = ["content-type", "authorization"]
}

# Stage
variable "stage_name" {
  description = "Stage name. Use $default for auto-deploy and base URL without stage suffix"
  type        = string
  default     = "$default"
}

variable "auto_deploy" {
  description = "Auto-deploy stage on config changes"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
}