# modules/eventarc/vector_nonprocess_trigger/main.tf

# Eventarc trigger for non-process documents
resource "google_eventarc_trigger" "vector_nonprocess" {
  project  = var.project_id
  name     = "${var.prefix}-vector-nonprocess-trigger"
  location = var.region

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = var.bucket_name
  }

  destination {
    pubsub {
      topic = var.pubsub_topic_id
    }
  }

  service_account = var.service_account

  labels = var.labels
}
