# modules/lambda/llm_tagging/outputs.tf
output "lambda_function_name" {
  value = aws_lambda_function.llm_tagging.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.llm_tagging.arn
}