# modules/eventarc/data_ingestion_trigger/main.tf

# Eventarc trigger for process documents
resource "google_eventarc_trigger" "data_ingestion" {
  project  = var.project_id
  name     = "${var.prefix}-data-ingestion-trigger"
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
