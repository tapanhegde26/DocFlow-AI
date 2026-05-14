output "lambda_function_name" {
  value = aws_lambda_function.store_vector_db.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.store_vector_db.arn
}

output "lambda_role_arn" {
  description = "IAM role ARN assumed by the store-vector-db Lambda"
  value       = aws_iam_role.lambda_exec.arn
}