# modules/gke/workload_identity/outputs.tf

output "gcp_service_account_email" {
  description = "GCP service account email"
  value       = google_service_account.gke_workload.email
}

output "k8s_service_account_name" {
  description = "Kubernetes service account name"
  value       = kubernetes_service_account.workload_sa.metadata[0].name
}

output "k8s_namespace" {
  description = "Kubernetes namespace"
  value       = var.k8s_namespace
}
