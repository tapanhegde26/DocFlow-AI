# modules/cloud_workflows/vectorindex_workflow_hybrid/outputs.tf

output "workflow_id" {
  description = "Workflow ID"
  value       = google_workflows_workflow.vectorindex_hybrid.id
}

output "workflow_name" {
  description = "Workflow name"
  value       = google_workflows_workflow.vectorindex_hybrid.name
}

output "workflow_revision_id" {
  description = "Workflow revision ID"
  value       = google_workflows_workflow.vectorindex_hybrid.revision_id
}
