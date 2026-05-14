# modules/cloud_run/pre_formatting/create_process_docs/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.create_process_docs.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.create_process_docs.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.create_process_docs.uri
}
