# modules/stepfunctions/data_ingestion_workflow/outputs.tf
output "step_function_arn" {
  value = aws_sfn_state_machine.data_ingestion.arn
}