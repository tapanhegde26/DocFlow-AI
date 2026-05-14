# modules/secret_manager/outputs.tf

output "db_credentials_secret_id" {
  description = "Database credentials secret ID"
  value       = google_secret_manager_secret.db_credentials.secret_id
}

output "db_credentials_secret_name" {
  description = "Database credentials secret name"
  value       = google_secret_manager_secret.db_credentials.name
}

output "vertex_ai_config_secret_id" {
  description = "Vertex AI config secret ID"
  value       = google_secret_manager_secret.vertex_ai_config.secret_id
}

output "app_secrets_secret_id" {
  description = "Application secrets secret ID"
  value       = google_secret_manager_secret.app_secrets.secret_id
}

output "jwt_secret_id" {
  description = "JWT secret ID"
  value       = google_secret_manager_secret.jwt_secret.secret_id
}
