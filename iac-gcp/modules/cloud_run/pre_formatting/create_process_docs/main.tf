# modules/cloud_run/pre_formatting/create_process_docs/main.tf

resource "google_cloud_run_v2_service" "create_process_docs" {
  name     = "${var.prefix}-create-process-docs"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/create-process-docs:latest"

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
        name  = "OUTPUT_BUCKET"
        value = var.standardized_bucket
      }

      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "DB_SECRET_ID"
        value = var.db_secret_id
      }

      env {
        name  = "DB_CONNECTION_NAME"
        value = var.db_connection_name
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

resource "google_cloud_run_v2_service_iam_member" "create_process_docs_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.create_process_docs.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
