# modules/eventarc/vector_process_trigger/outputs.tf

output "trigger_id" {
  description = "Eventarc trigger ID"
  value       = google_eventarc_trigger.vector_process.id
}

output "trigger_name" {
  description = "Eventarc trigger name"
  value       = google_eventarc_trigger.vector_process.name
}
