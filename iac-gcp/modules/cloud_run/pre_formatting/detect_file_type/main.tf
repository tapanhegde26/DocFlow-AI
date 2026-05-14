# modules/cloud_run/pre_formatting/detect_file_type/main.tf

resource "google_cloud_run_v2_service" "detect_file_type" {
  name     = "${var.prefix}-detect-file-type"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/detect-file-type:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
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
        name  = "RAW_SOP_BUCKET"
        value = var.raw_sop_bucket
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

# Allow unauthenticated access (for internal workflow calls)
resource "google_cloud_run_v2_service_iam_member" "detect_file_type_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.detect_file_type.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
