# modules/cloud_run/pre_formatting/identify_distinct_process/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.identify_distinct_process.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.identify_distinct_process.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.identify_distinct_process.uri
}
