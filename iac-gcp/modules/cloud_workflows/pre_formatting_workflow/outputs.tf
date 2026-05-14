# modules/cloud_workflows/pre_formatting_workflow/outputs.tf

output "workflow_id" {
  description = "Workflow ID"
  value       = google_workflows_workflow.pre_formatting.id
}

output "workflow_name" {
  description = "Workflow name"
  value       = google_workflows_workflow.pre_formatting.name
}

output "workflow_revision_id" {
  description = "Workflow revision ID"
  value       = google_workflows_workflow.pre_formatting.revision_id
}
