# modules/cloud_run/data_ingestion/llm_tagging/main.tf

resource "google_cloud_run_v2_service" "llm_tagging" {
  name     = "${var.prefix}-llm-tagging"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/llm-tagging:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
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
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "VERTEX_MODEL_ID"
        value = var.vertex_model_id
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    timeout = "600s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "llm_tagging_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.llm_tagging.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
