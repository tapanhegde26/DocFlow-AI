# modules/cloud_sql/variables.tf

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "database_name" {
  description = "Name of the database"
  type        = string
  default     = "tsh-industries_db"
}

variable "database_user" {
  description = "Database user name"
  type        = string
  default     = "tsh-industries_admin"
}

variable "vpc_network_id" {
  description = "VPC network ID for private IP"
  type        = string
}

variable "private_ip_range" {
  description = "Private IP range name for service networking"
  type        = string
}

variable "tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-custom-2-4096"
}

variable "availability_type" {
  description = "Availability type (REGIONAL or ZONAL)"
  type        = string
  default     = "ZONAL"
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 20
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "db_secret_id" {
  description = "Secret Manager secret ID for storing credentials"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
