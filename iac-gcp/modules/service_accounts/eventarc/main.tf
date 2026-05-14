# modules/service_accounts/eventarc/main.tf

resource "google_service_account" "eventarc" {
  project      = var.project_id
  account_id   = "${var.prefix}-eventarc-sa"
  display_name = "Eventarc Service Account"
  description  = "Service account for Eventarc triggers"
}

# Grant Eventarc Event Receiver role
resource "google_project_iam_member" "eventarc_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

# Grant Pub/Sub Publisher role
resource "google_project_iam_member" "pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

# Grant Workflows Invoker role
resource "google_project_iam_member" "workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

# Grant Cloud Run Invoker role
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}
