# modules/eventarc/data_ingestion_trigger/outputs.tf

output "trigger_id" {
  description = "Eventarc trigger ID"
  value       = google_eventarc_trigger.data_ingestion.id
}

output "trigger_name" {
  description = "Eventarc trigger name"
  value       = google_eventarc_trigger.data_ingestion.name
}
