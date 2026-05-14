# modules/cloud_workflows/data_ingestion_workflow_hybrid/outputs.tf

output "workflow_id" {
  description = "Workflow ID"
  value       = google_workflows_workflow.data_ingestion_hybrid.id
}

output "workflow_name" {
  description = "Workflow name"
  value       = google_workflows_workflow.data_ingestion_hybrid.name
}

output "workflow_revision_id" {
  description = "Workflow revision ID"
  value       = google_workflows_workflow.data_ingestion_hybrid.revision_id
}
