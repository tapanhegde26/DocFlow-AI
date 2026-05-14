# modules/cloud_run/vectorization/generate_embedding/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.generate_embedding.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.generate_embedding.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.generate_embedding.uri
}
