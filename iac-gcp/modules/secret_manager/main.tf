# modules/secret_manager/main.tf

# Database credentials secret
resource "google_secret_manager_secret" "db_credentials" {
  project   = var.project_id
  secret_id = "${var.prefix}-db-credentials"

  replication {
    auto {}
  }

  labels = var.labels
}

# Vertex AI API key secret (if needed for external services)
resource "google_secret_manager_secret" "vertex_ai_config" {
  project   = var.project_id
  secret_id = "${var.prefix}-vertex-ai-config"

  replication {
    auto {}
  }

  labels = var.labels
}

# Application secrets
resource "google_secret_manager_secret" "app_secrets" {
  project   = var.project_id
  secret_id = "${var.prefix}-app-secrets"

  replication {
    auto {}
  }

  labels = var.labels
}

# JWT signing key
resource "google_secret_manager_secret" "jwt_secret" {
  project   = var.project_id
  secret_id = "${var.prefix}-jwt-secret"

  replication {
    auto {}
  }

  labels = var.labels
}
