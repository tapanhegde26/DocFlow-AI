# modules/vertex_ai/vector_search_index/outputs.tf

output "process_index_id" {
  description = "Process index ID"
  value       = google_vertex_ai_index.process_index.id
}

output "process_index_name" {
  description = "Process index name"
  value       = google_vertex_ai_index.process_index.name
}

output "nonprocess_index_id" {
  description = "Non-process index ID"
  value       = google_vertex_ai_index.nonprocess_index.id
}

output "nonprocess_index_name" {
  description = "Non-process index name"
  value       = google_vertex_ai_index.nonprocess_index.name
}

output "index_endpoint_id" {
  description = "Process index endpoint ID"
  value       = google_vertex_ai_index_endpoint.process_endpoint.id
}

output "index_endpoint_name" {
  description = "Process index endpoint name"
  value       = google_vertex_ai_index_endpoint.process_endpoint.name
}

output "nonprocess_index_endpoint_id" {
  description = "Non-process index endpoint ID"
  value       = google_vertex_ai_index_endpoint.nonprocess_endpoint.id
}

output "nonprocess_index_endpoint_name" {
  description = "Non-process index endpoint name"
  value       = google_vertex_ai_index_endpoint.nonprocess_endpoint.name
}

output "vector_index_data_bucket" {
  description = "GCS bucket for vector index data"
  value       = google_storage_bucket.vector_index_data.name
}
