# modules/pubsub/pre_formatting_topic/main.tf

# Main topic for pre-formatting events
resource "google_pubsub_topic" "pre_formatting" {
  project = var.project_id
  name    = "${var.prefix}-pre-formatting-topic"

  labels = var.labels

  message_retention_duration = "86400s" # 24 hours
}

# Dead letter topic
resource "google_pubsub_topic" "pre_formatting_dlq" {
  project = var.project_id
  name    = "${var.prefix}-pre-formatting-dlq"

  labels = var.labels

  message_retention_duration = "604800s" # 7 days
}

# Subscription for workflow trigger
resource "google_pubsub_subscription" "pre_formatting_sub" {
  project = var.project_id
  name    = "${var.prefix}-pre-formatting-sub"
  topic   = google_pubsub_topic.pre_formatting.name

  ack_deadline_seconds = 600 # 10 minutes

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.pre_formatting_dlq.id
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
resource "google_pubsub_subscription" "pre_formatting_dlq_sub" {
  project = var.project_id
  name    = "${var.prefix}-pre-formatting-dlq-sub"
  topic   = google_pubsub_topic.pre_formatting_dlq.name

  ack_deadline_seconds = 60

  expiration_policy {
    ttl = "" # Never expires
  }

  labels = var.labels
}
