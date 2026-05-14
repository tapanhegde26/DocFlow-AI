data "aws_secretsmanager_secret" "master" {
  arn        = aws_rds_cluster.this.master_user_secret[0].secret_arn
  depends_on = [aws_rds_cluster.this]
}

output "db_security_group_id" {
  description = "Security group ID for the Aurora PostgreSQL cluster"
  value       = aws_security_group.db.id
}

output "db_subnet_group_name" {
  description = "DB subnet group name"
  value       = aws_db_subnet_group.this.name
}

output "cluster_arn" {
  description = "RDS cluster ARN"
  value       = aws_rds_cluster.this.arn
}

output "cluster_id" {
  description = "RDS cluster identifier"
  value       = aws_rds_cluster.this.id
}

output "writer_endpoint" {
  description = "Cluster writer endpoint"
  value       = aws_rds_cluster.this.endpoint
}

output "reader_endpoint" {
  description = "Cluster reader endpoint"
  value       = aws_rds_cluster.this.reader_endpoint
}

output "writer_instance_endpoint" {
  description = "Endpoint of the writer instance (pin to a single instance; not recommended for general app writes)"
  value       = aws_rds_cluster_instance.writer.endpoint
}

output "db_name" {
  description = "Database name"
  value       = aws_rds_cluster.this.database_name
}

output "master_username" {
  description = "Master username"
  value       = aws_rds_cluster.this.master_username
}

output "master_secret_arn" {
  description = "Secrets Manager ARN for the master user secret"
  value       =  aws_rds_cluster.this.master_user_secret[0].secret_arn
}

output "master_secret_name" {
  description = "Secrets Manager name for the master user secret"
  value       = data.aws_secretsmanager_secret.master.name
}

output "port" {
  description = "Database port"
  value       = 5432
}

output "security_group_id" {
  description = "Database security group ID"
  value = aws_security_group.db.id
}
