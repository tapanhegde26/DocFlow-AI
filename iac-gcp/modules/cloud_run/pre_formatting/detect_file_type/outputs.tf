# modules/cloud_run/pre_formatting/detect_file_type/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.detect_file_type.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.detect_file_type.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.detect_file_type.uri
}
