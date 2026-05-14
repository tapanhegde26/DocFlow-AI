# modules/cloud_run/vectorization/chunk_sop/main.tf

resource "google_cloud_run_v2_service" "chunk_sop" {
  name     = "${var.prefix}-chunk-sop"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/chunk-sop:latest"

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
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "CHUNK_SIZE"
        value = "500"
      }

      env {
        name  = "CHUNK_OVERLAP"
        value = "50"
      }

      env {
        name  = "INCLUDE_IMAGE_REFS"
        value = "true"
      }

      env {
        name  = "SEPARATE_IMAGE_CHUNKS"
        value = "false"
      }

      env {
        name  = "INCLUDE_TAGGING_INFO"
        value = "true"
      }

      env {
        name  = "SEPARATE_TAGGING_CHUNKS"
        value = "true"
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

resource "google_cloud_run_v2_service_iam_member" "chunk_sop_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.chunk_sop.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
