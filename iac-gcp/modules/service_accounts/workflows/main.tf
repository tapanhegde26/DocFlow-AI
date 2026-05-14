# modules/service_accounts/workflows/main.tf

resource "google_service_account" "workflows" {
  project      = var.project_id
  account_id   = "${var.short_prefix}-wf-sa"
  display_name = "Cloud Workflows Service Account (${var.prefix})"
  description  = "Service account for Cloud Workflows"
}

# Grant Cloud Run Invoker role
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.workflows.email}"
}

# Grant Workflows Invoker role (for nested workflows)
resource "google_project_iam_member" "workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.workflows.email}"
}

# Grant Logging Writer role
resource "google_project_iam_member" "logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.workflows.email}"
}

# Grant Storage Object Viewer role
resource "google_project_iam_member" "storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.workflows.email}"
}
