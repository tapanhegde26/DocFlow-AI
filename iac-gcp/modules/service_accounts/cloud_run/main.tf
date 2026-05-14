# modules/service_accounts/cloud_run/main.tf

resource "google_service_account" "cloud_run" {
  project      = var.project_id
  account_id   = "${var.short_prefix}-run-sa"
  display_name = "Cloud Run Service Account (${var.prefix})"
  description  = "Service account for Cloud Run services"
}

# Grant Storage Object Viewer/Creator roles
resource "google_project_iam_member" "storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Vertex AI User role
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Secret Manager Secret Accessor role
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Cloud SQL Client role
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Pub/Sub Publisher role
resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Logging Writer role
resource "google_project_iam_member" "logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Grant Discovery Engine Editor role (for Vertex AI Search)
resource "google_project_iam_member" "discovery_engine_editor" {
  project = var.project_id
  role    = "roles/discoveryengine.editor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}
