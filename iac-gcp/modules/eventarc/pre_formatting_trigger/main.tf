# modules/eventarc/pre_formatting_trigger/main.tf

# Eventarc trigger for raw SOP uploads
resource "google_eventarc_trigger" "pre_formatting" {
  project  = var.project_id
  name     = "${var.prefix}-pre-formatting-trigger"
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
    cloud_run_service {
      service = var.workflow_trigger_service
      region  = var.region
    }
  }

  service_account = var.service_account

  labels = var.labels
}

# Alternative: Direct Pub/Sub destination
resource "google_eventarc_trigger" "pre_formatting_pubsub" {
  count = var.use_pubsub_destination ? 1 : 0

  project  = var.project_id
  name     = "${var.prefix}-pre-formatting-pubsub-trigger"
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
