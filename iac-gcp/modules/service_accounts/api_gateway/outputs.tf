# modules/service_accounts/api_gateway/outputs.tf

output "email" {
  description = "Service account email"
  value       = google_service_account.api_gateway.email
}

output "id" {
  description = "Service account ID"
  value       = google_service_account.api_gateway.id
}

output "name" {
  description = "Service account name"
  value       = google_service_account.api_gateway.name
}
