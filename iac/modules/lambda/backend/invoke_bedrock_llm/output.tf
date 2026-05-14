output "lambda_function_name" {
  value = aws_lambda_function.invoke_bedrock_llm.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.invoke_bedrock_llm.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN assumed by the store-vector-db Lambda"
  value       = aws_iam_role.lambda_exec.arn
}