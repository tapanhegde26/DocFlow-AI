# modules/cloud_run/vectorization/store_to_vector_db/main.tf

resource "google_cloud_run_v2_service" "store_to_vector_db" {
  name     = "${var.prefix}-store-to-vector-db"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.repository_url}/store-to-vector-db:latest"

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
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "VECTOR_SEARCH_INDEX_ENDPOINT"
        value = var.vector_search_index_endpoint
      }

      env {
        name  = "VECTOR_SEARCH_INDEX_ID"
        value = var.vector_search_index_id
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

resource "google_cloud_run_v2_service_iam_member" "store_to_vector_db_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.store_to_vector_db.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account}"
}
