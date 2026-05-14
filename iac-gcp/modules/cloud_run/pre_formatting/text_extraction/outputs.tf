# modules/cloud_run/pre_formatting/text_extraction/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.text_extraction.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.text_extraction.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.text_extraction.uri
}
