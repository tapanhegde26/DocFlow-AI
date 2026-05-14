# modules/cloud_workflows/vectorindex_workflow/outputs.tf

output "workflow_id" {
  description = "Workflow ID"
  value       = google_workflows_workflow.vectorindex.id
}

output "workflow_name" {
  description = "Workflow name"
  value       = google_workflows_workflow.vectorindex.name
}

output "workflow_revision_id" {
  description = "Workflow revision ID"
  value       = google_workflows_workflow.vectorindex.revision_id
}
