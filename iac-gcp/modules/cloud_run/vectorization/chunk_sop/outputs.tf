# modules/cloud_run/vectorization/chunk_sop/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.chunk_sop.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.chunk_sop.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.chunk_sop.uri
}
