# modules/cloud_run/vectorization/store_to_vector_db/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.store_to_vector_db.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.store_to_vector_db.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.store_to_vector_db.uri
}
