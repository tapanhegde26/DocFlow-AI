terraform {
  required_version = ">= 1.4.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-subnets"
  subnet_ids = var.subnet_ids
  tags       = local.tags
}

resource "aws_security_group" "db" {
  name        = "${var.name}-sg"
  description = "Aurora PostgreSQL security group"
  vpc_id      = var.vpc_id
  tags        = local.tags
}

# Allow SG-to-SG access (e.g., from Lambda SGs)
resource "aws_security_group_rule" "ingress_from_sgs" {
  for_each                 = toset(var.allowed_security_group_ids)
  type                     = "ingress"
  security_group_id        = aws_security_group.db.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = each.value
  description              = "Allow Postgres from SG ${each.value}"
}

# CIDR-based ingress
resource "aws_security_group_rule" "ingress_from_cidrs" {
  count             = length(var.allowed_cidr_blocks) > 0 ? 1 : 0
  type              = "ingress"
  security_group_id = aws_security_group.db.id
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  description       = "Allow Postgres from CIDRs"
}

# Egress anywhere
resource "aws_security_group_rule" "egress_all" {
  type              = "egress"
  security_group_id = aws_security_group.db.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "Allow all egress"
}

# --------------------------------
# Parameter groups (optional, minimal defaults)
# --------------------------------
resource "aws_rds_cluster_parameter_group" "cluster_pg" {
  name   = "${var.name}-cluster-pg"
  family = "aurora-postgresql14"
  tags   = local.tags
}

resource "aws_db_parameter_group" "instance_pg" {
  name   = "${var.name}-instance-pg"
  family = "aurora-postgresql14"
  tags   = local.tags
}

# --------------------------------
# Aurora PostgreSQL Cluster
# --------------------------------
resource "aws_rds_cluster" "this" {
  cluster_identifier              = var.name
  engine                          = "aurora-postgresql"
  engine_version                  = var.engine_version
  storage_type                    = "aurora" # Standard (not I/O-Optimized)
  database_name                   = var.db_name
  master_username                 = var.username

  # Let RDS manage the master password in Secrets Manager
  manage_master_user_password     = true
  # Use default aws/secretsmanager key by omitting master_user_secret_kms_key_id

  db_subnet_group_name            = aws_db_subnet_group.this.name
  vpc_security_group_ids          = [aws_security_group.db.id]
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.cluster_pg.name

  backup_retention_period         = var.backup_retention_days
  preferred_backup_window         = var.preferred_backup_window
  preferred_maintenance_window    = var.preferred_maintenance_window
  deletion_protection             = var.deletion_protection
  copy_tags_to_snapshot           = var.copy_tags_to_snapshot

  apply_immediately               = var.apply_immediately

  enabled_cloudwatch_logs_exports = var.enable_cloudwatch_logs_exports

  tags = local.tags
  skip_final_snapshot = var.skip_final_snapshot

  # Enable RDS Data API
  enable_http_endpoint = true
}

# --------------------------------
# Single writer instance (single-AZ)
# --------------------------------
resource "aws_rds_cluster_instance" "writer" {
  identifier                   = "${var.name}-writer-1"
  cluster_identifier           = aws_rds_cluster.this.id
  instance_class               = var.instance_class
  engine                       = aws_rds_cluster.this.engine
  engine_version               = aws_rds_cluster.this.engine_version
  db_parameter_group_name      = aws_db_parameter_group.instance_pg.name
  publicly_accessible          = var.publicly_accessible
  db_subnet_group_name         = aws_db_subnet_group.this.name
  auto_minor_version_upgrade   = true
  promotion_tier               = 1
  apply_immediately            = var.apply_immediately


  tags = local.tags
}
