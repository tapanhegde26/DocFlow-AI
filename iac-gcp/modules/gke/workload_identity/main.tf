# modules/gke/workload_identity/main.tf
# Workload Identity configuration for GKE services to access GCP APIs

# Kubernetes Service Account
resource "kubernetes_service_account" "workload_sa" {
  metadata {
    name      = var.k8s_service_account_name
    namespace = var.k8s_namespace
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.gke_workload.email
    }
  }
}

# GCP Service Account for workloads
resource "google_service_account" "gke_workload" {
  project      = var.project_id
  account_id   = "${var.short_prefix}-gke-wl-sa"
  display_name = "GKE Workload Service Account (${var.prefix})"
  description  = "Service account for GKE workloads to access GCP services"
}

# IAM binding for Workload Identity
resource "google_service_account_iam_member" "workload_identity_binding" {
  service_account_id = google_service_account.gke_workload.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[${var.k8s_namespace}/${var.k8s_service_account_name}]"
}

# Grant necessary permissions to the GCP service account

# Storage access
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Vertex AI access
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Secret Manager access
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Cloud SQL access
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Pub/Sub access
resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Logging access
resource "google_project_iam_member" "logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Monitoring access
resource "google_project_iam_member" "monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# Discovery Engine (Vertex AI Search) access
resource "google_project_iam_member" "discovery_engine_editor" {
  project = var.project_id
  role    = "roles/discoveryengine.editor"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}
