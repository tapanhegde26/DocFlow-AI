# modules/vertex_ai/search_datastore/outputs.tf

output "process_datastore_id" {
  description = "Process datastore ID"
  value       = google_discovery_engine_data_store.process_datastore.data_store_id
}

output "process_datastore_name" {
  description = "Process datastore name"
  value       = google_discovery_engine_data_store.process_datastore.name
}

output "nonprocess_datastore_id" {
  description = "Non-process datastore ID"
  value       = google_discovery_engine_data_store.nonprocess_datastore.data_store_id
}

output "nonprocess_datastore_name" {
  description = "Non-process datastore name"
  value       = google_discovery_engine_data_store.nonprocess_datastore.name
}

output "process_engine_id" {
  description = "Process search engine ID"
  value       = google_discovery_engine_search_engine.process_engine.engine_id
}

output "nonprocess_engine_id" {
  description = "Non-process search engine ID"
  value       = google_discovery_engine_search_engine.nonprocess_engine.engine_id
}
