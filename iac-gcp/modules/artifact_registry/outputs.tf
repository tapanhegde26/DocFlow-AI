# modules/artifact_registry/outputs.tf

output "repository_id" {
  description = "Repository ID"
  value       = google_artifact_registry_repository.docker_repo.repository_id
}

output "repository_name" {
  description = "Repository name"
  value       = google_artifact_registry_repository.docker_repo.name
}

output "repository_url" {
  description = "Repository URL for docker push/pull"
  value       = "${var.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}
