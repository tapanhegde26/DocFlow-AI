# modules/pubsub/vector_nonprocess_topic/main.tf

# Main topic for vector non-process events
resource "google_pubsub_topic" "vector_nonprocess" {
  project = var.project_id
  name    = "${var.prefix}-vector-nonprocess-topic"

  labels = var.labels

  message_retention_duration = "86400s" # 24 hours
}

# Dead letter topic
resource "google_pubsub_topic" "vector_nonprocess_dlq" {
  project = var.project_id
  name    = "${var.prefix}-vector-nonprocess-dlq"

  labels = var.labels

  message_retention_duration = "604800s" # 7 days
}

# Subscription for workflow trigger
resource "google_pubsub_subscription" "vector_nonprocess_sub" {
  project = var.project_id
  name    = "${var.prefix}-vector-nonprocess-sub"
  topic   = google_pubsub_topic.vector_nonprocess.name

  ack_deadline_seconds = 600 # 10 minutes

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.vector_nonprocess_dlq.id
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
resource "google_pubsub_subscription" "vector_nonprocess_dlq_sub" {
  project = var.project_id
  name    = "${var.prefix}-vector-nonprocess-dlq-sub"
  topic   = google_pubsub_topic.vector_nonprocess_dlq.name

  ack_deadline_seconds = 60

  expiration_policy {
    ttl = "" # Never expires
  }

  labels = var.labels
}
