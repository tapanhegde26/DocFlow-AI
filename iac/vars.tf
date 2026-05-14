variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ca-central-1"
}

variable "jwt_issuer" {
  description = "OIDC issuer URL (e.g., https://cognito-idp.<region>.amazonaws.com/<userPoolId>)"
  type        = string
  default     = "https://auth.tsh-industries.cloud/realms/master"
}

variable "jwt_audiences" {
  description = "Allowed audiences (e.g., Cognito App Client ID(s))"
  type        = list(string)
  default     = ["forge.dev.tsh-industries.cloud"]
}

variable "allow_origins" {
  description = "CORS allowed origins for API Gateway"
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
  default     = ["authorization", "content-type"]
}