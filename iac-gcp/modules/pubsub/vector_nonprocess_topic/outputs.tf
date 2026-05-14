# modules/pubsub/vector_nonprocess_topic/outputs.tf

output "topic_id" {
  description = "Topic ID"
  value       = google_pubsub_topic.vector_nonprocess.id
}

output "topic_name" {
  description = "Topic name"
  value       = google_pubsub_topic.vector_nonprocess.name
}

output "subscription_id" {
  description = "Subscription ID"
  value       = google_pubsub_subscription.vector_nonprocess_sub.id
}

output "subscription_name" {
  description = "Subscription name"
  value       = google_pubsub_subscription.vector_nonprocess_sub.name
}

output "dlq_topic_id" {
  description = "Dead letter topic ID"
  value       = google_pubsub_topic.vector_nonprocess_dlq.id
}

output "dlq_topic_name" {
  description = "Dead letter topic name"
  value       = google_pubsub_topic.vector_nonprocess_dlq.name
}
