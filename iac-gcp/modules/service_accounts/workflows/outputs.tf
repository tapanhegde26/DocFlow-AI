# modules/service_accounts/workflows/outputs.tf

output "email" {
  description = "Service account email"
  value       = google_service_account.workflows.email
}

output "id" {
  description = "Service account ID"
  value       = google_service_account.workflows.id
}

output "name" {
  description = "Service account name"
  value       = google_service_account.workflows.name
}
