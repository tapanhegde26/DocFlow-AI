# modules/cloud_run/pre_formatting/text_extraction/main.tf

resource "google_cloud_run_v2_service" "text_extraction" {
  name     = "${var.prefix}-text-extraction"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/text-extraction:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }

      env {
        name  = "EXTRACTED_TEXT_BUCKET"
        value = var.text_extract_bucket
      }

      env {
        name  = "REGION"
        value = var.region
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }

    timeout = "600s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "text_extraction_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.text_extraction.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
