output "lambda_function_name" {
  value = aws_lambda_function.check_for_duplicates.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.check_for_duplicates.arn
}
