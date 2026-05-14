# modules/pubsub/vector_process_topic/main.tf

# Main topic for vector process events
resource "google_pubsub_topic" "vector_process" {
  project = var.project_id
  name    = "${var.prefix}-vector-process-topic"

  labels = var.labels

  message_retention_duration = "86400s" # 24 hours
}

# Dead letter topic
resource "google_pubsub_topic" "vector_process_dlq" {
  project = var.project_id
  name    = "${var.prefix}-vector-process-dlq"

  labels = var.labels

  message_retention_duration = "604800s" # 7 days
}

# Subscription for workflow trigger
resource "google_pubsub_subscription" "vector_process_sub" {
  project = var.project_id
  name    = "${var.prefix}-vector-process-sub"
  topic   = google_pubsub_topic.vector_process.name

  ack_deadline_seconds = 600 # 10 minutes

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.vector_process_dlq.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  expiration_policy {
    ttl = "" # Never expires
  }

  labels = var.labels
}

# Dead letter subscription for monitoring
resource "google_pubsub_subscription" "vector_process_dlq_sub" {
  project = var.project_id
  name    = "${var.prefix}-vector-process-dlq-sub"
  topic   = google_pubsub_topic.vector_process_dlq.name

  ack_deadline_seconds = 60

  expiration_policy {
    ttl = "" # Never expires
  }

  labels = var.labels
}
