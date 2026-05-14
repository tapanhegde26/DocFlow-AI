# modules/eventarc/pre_formatting_trigger/outputs.tf

output "trigger_id" {
  description = "Eventarc trigger ID"
  value       = var.use_pubsub_destination ? google_eventarc_trigger.pre_formatting_pubsub[0].id : google_eventarc_trigger.pre_formatting.id
}

output "trigger_name" {
  description = "Eventarc trigger name"
  value       = var.use_pubsub_destination ? google_eventarc_trigger.pre_formatting_pubsub[0].name : google_eventarc_trigger.pre_formatting.name
}
