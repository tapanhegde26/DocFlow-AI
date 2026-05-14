# modules/cloud_run/data_ingestion/llm_tagging/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.llm_tagging.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.llm_tagging.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.llm_tagging.uri
}
