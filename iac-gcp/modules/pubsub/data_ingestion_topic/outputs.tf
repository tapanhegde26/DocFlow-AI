# modules/pubsub/data_ingestion_topic/outputs.tf

output "topic_id" {
  description = "Topic ID"
  value       = google_pubsub_topic.data_ingestion.id
}

output "topic_name" {
  description = "Topic name"
  value       = google_pubsub_topic.data_ingestion.name
}

output "subscription_id" {
  description = "Subscription ID"
  value       = google_pubsub_subscription.data_ingestion_sub.id
}

output "subscription_name" {
  description = "Subscription name"
  value       = google_pubsub_subscription.data_ingestion_sub.name
}

output "dlq_topic_id" {
  description = "Dead letter topic ID"
  value       = google_pubsub_topic.data_ingestion_dlq.id
}

output "dlq_topic_name" {
  description = "Dead letter topic name"
  value       = google_pubsub_topic.data_ingestion_dlq.name
}
