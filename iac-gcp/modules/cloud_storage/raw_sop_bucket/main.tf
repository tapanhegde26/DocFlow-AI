# modules/cloud_storage/raw_sop_bucket/main.tf

resource "google_storage_bucket" "raw_sop" {
  name          = var.bucket_name
  project       = var.project_id
  location      = var.location
  force_destroy = var.force_destroy

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels
}

# Enable notifications for Eventarc
resource "google_storage_notification" "notification" {
  bucket         = google_storage_bucket.raw_sop.name
  payload_format = "JSON_API_V1"
  topic          = var.pubsub_topic_id
  event_types    = ["OBJECT_FINALIZE"]

  count = var.pubsub_topic_id != "" ? 1 : 0
}
