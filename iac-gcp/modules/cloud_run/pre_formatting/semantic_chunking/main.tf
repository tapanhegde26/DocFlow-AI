# modules/cloud_run/pre_formatting/semantic_chunking/main.tf

resource "google_cloud_run_v2_service" "semantic_chunking" {
  name     = "${var.prefix}-semantic-chunking"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/semantic-chunking:latest"

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
        name  = "SEMANTIC_CHUNKING_BUCKET"
        value = var.text_extract_bucket
      }

      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "VERTEX_MODEL_ID"
        value = var.vertex_model_id
      }

      env {
        name  = "USE_VERTEX_AI"
        value = "true"
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

resource "google_cloud_run_v2_service_iam_member" "semantic_chunking_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.semantic_chunking.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
