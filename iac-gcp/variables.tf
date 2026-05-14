# IaC-GCP/variables.tf

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  default     = "development"
}

variable "skip_gcp_auth" {
  description = "Skip GCP authentication for local validation (set to true when running without GCP credentials)"
  type        = bool
  default     = false
}

variable "vertex_llm_model_id" {
  description = "Vertex AI LLM model ID for text generation"
  type        = string
  default     = "gemini-1.5-pro"
}

variable "vertex_embedding_model_id" {
  description = "Vertex AI embedding model ID"
  type        = string
  default     = "text-embedding-004"
}

variable "jwt_issuer" {
  description = "JWT issuer for API authentication"
  type        = string
  default     = ""
}

variable "jwt_audiences" {
  description = "JWT audiences for API authentication"
  type        = list(string)
  default     = []
}

variable "allow_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = ["*"]
}

variable "allow_methods" {
  description = "Allowed CORS methods"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}

variable "allow_headers" {
  description = "Allowed CORS headers"
  type        = list(string)
  default     = ["Content-Type", "Authorization"]
}
