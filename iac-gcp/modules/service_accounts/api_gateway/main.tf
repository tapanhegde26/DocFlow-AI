# modules/service_accounts/api_gateway/main.tf

resource "google_service_account" "api_gateway" {
  project      = var.project_id
  account_id   = "${var.short_prefix}-apigw-sa"
  display_name = "API Gateway Service Account (${var.prefix})"
  description  = "Service account for API Gateway"
}

# Grant Cloud Run Invoker role
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}

# Grant Service Account Token Creator (for authentication)
resource "google_project_iam_member" "token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.api_gateway.email}"
}
