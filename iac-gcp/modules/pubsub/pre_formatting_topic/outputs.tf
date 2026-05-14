# modules/pubsub/pre_formatting_topic/outputs.tf

output "topic_id" {
  description = "Topic ID"
  value       = google_pubsub_topic.pre_formatting.id
}

output "topic_name" {
  description = "Topic name"
  value       = google_pubsub_topic.pre_formatting.name
}

output "subscription_id" {
  description = "Subscription ID"
  value       = google_pubsub_subscription.pre_formatting_sub.id
}

output "subscription_name" {
  description = "Subscription name"
  value       = google_pubsub_subscription.pre_formatting_sub.name
}

output "dlq_topic_id" {
  description = "Dead letter topic ID"
  value       = google_pubsub_topic.pre_formatting_dlq.id
}

output "dlq_topic_name" {
  description = "Dead letter topic name"
  value       = google_pubsub_topic.pre_formatting_dlq.name
}
