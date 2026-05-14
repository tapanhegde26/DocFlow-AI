# modules/eventarc/vector_nonprocess_trigger/outputs.tf

output "trigger_id" {
  description = "Eventarc trigger ID"
  value       = google_eventarc_trigger.vector_nonprocess.id
}

output "trigger_name" {
  description = "Eventarc trigger name"
  value       = google_eventarc_trigger.vector_nonprocess.name
}
