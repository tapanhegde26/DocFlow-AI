# modules/cloud_workflows/data_ingestion_workflow/outputs.tf

output "workflow_id" {
  description = "Workflow ID"
  value       = google_workflows_workflow.data_ingestion.id
}

output "workflow_name" {
  description = "Workflow name"
  value       = google_workflows_workflow.data_ingestion.name
}

output "workflow_revision_id" {
  description = "Workflow revision ID"
  value       = google_workflows_workflow.data_ingestion.revision_id
}
