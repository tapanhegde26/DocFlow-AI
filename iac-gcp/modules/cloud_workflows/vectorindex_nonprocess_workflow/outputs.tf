# modules/cloud_workflows/vectorindex_nonprocess_workflow/outputs.tf

output "workflow_id" {
  description = "Workflow ID"
  value       = google_workflows_workflow.vectorindex_nonprocess.id
}

output "workflow_name" {
  description = "Workflow name"
  value       = google_workflows_workflow.vectorindex_nonprocess.name
}

output "workflow_revision_id" {
  description = "Workflow revision ID"
  value       = google_workflows_workflow.vectorindex_nonprocess.revision_id
}
