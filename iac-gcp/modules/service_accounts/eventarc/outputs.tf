# modules/service_accounts/eventarc/outputs.tf

output "email" {
  description = "Service account email"
  value       = google_service_account.eventarc.email
}

output "id" {
  description = "Service account ID"
  value       = google_service_account.eventarc.id
}

output "name" {
  description = "Service account name"
  value       = google_service_account.eventarc.name
}
