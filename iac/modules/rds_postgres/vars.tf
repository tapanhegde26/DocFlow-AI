variable "name" {
  description = "Base name for the Aurora cluster and related resources"
  type        = string
}

variable "environment" {
  description = "Environment tag value"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the DB subnet group and security group"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the DB subnet group (2+ subnets recommended)"
  type        = list(string)
}

variable "db_name" {
  description = "Initial database name"
  type        = string
}

variable "username" {
  description = "Master username (password is managed by RDS + Secrets Manager)"
  type        = string
}

variable "engine_version" {
  description = "Aurora PostgreSQL engine version"
  type        = string
  default = "14.17"
}

variable "instance_class" {
  description = "DB instance class for the writer (e.g., db.r6g.large)"
  type        = string
  default     = "db.r6g.large"
  validation {
    condition     = can(regex("^db\\.(r6g|r7g|r5|r6i)\\.", var.instance_class))
    error_message = "Use an Aurora-supported class like db.r6g.*, db.r7g.*, db.r5.*, or db.r6i.*"
  }
}

variable "publicly_accessible" {
  description = "Whether instances get public IPs (keep false for private)"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Automated backup retention period"
  type        = number
  default     = 1
}

variable "deletion_protection" {
  description = "Protect cluster from deletion"
  type        = bool
  default     = false
}

variable "copy_tags_to_snapshot" {
  description = "Copy resource tags to snapshots"
  type        = bool
  default     = true
}

variable "preferred_backup_window" {
  description = "Daily time range for taking backups (UTC), e.g., 03:00-04:00"
  type        = string
  default     = "03:00-04:00"
}

variable "preferred_maintenance_window" {
  description = "Weekly time range for maintenance, e.g., sun:05:00-sun:06:00"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "enable_cloudwatch_logs_exports" {
  description = "List of log types to export to CloudWatch (e.g., [\"postgresql\"])"
  type        = list(string)
  default     = []
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to connect to Postgres on 5432 (e.g., Lambda SGs)"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to connect to Postgres on 5432 (avoid 0.0.0.0/0 in prod)"
  type        = list(string)
  default     = []
}

variable "apply_immediately" {
  description = "Apply changes immediately"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on destroy"
  type        = bool
  default     = false
}
