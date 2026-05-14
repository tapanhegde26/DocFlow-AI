# modules/service_accounts/cloud_run/outputs.tf

output "email" {
  description = "Service account email"
  value       = google_service_account.cloud_run.email
}

output "id" {
  description = "Service account ID"
  value       = google_service_account.cloud_run.id
}

output "name" {
  description = "Service account name"
  value       = google_service_account.cloud_run.name
}
