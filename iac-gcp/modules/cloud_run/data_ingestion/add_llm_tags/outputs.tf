# modules/cloud_run/data_ingestion/add_llm_tags/outputs.tf

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_v2_service.add_llm_tags.id
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.add_llm_tags.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.add_llm_tags.uri
}
