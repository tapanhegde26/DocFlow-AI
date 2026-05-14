# modules/stepfunctions/vectorindex_workflow/outputs.tf
output "step_function_arn" {
  value = aws_sfn_state_machine.vector_index.arn
}