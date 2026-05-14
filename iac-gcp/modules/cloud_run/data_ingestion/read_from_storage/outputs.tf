# modules/cloud_run/data_ingestion/read_from_storage/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.read_from_storage.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.read_from_storage.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.read_from_storage.uri
}
