# modules/cloud_run/pre_formatting/text_standardize/main.tf

resource "google_cloud_run_v2_service" "text_standardize" {
  name     = "${var.prefix}-text-standardize"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/text-standardize:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
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
        name  = "TEXT_STD_BUCKET"
        value = var.text_extract_bucket
      }

      env {
        name  = "REGION"
        value = var.region
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    timeout = "300s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "text_standardize_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.text_standardize.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
