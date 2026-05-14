output "lambda_function_name" {
  value = aws_lambda_function.identify_distinct_process.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.identify_distinct_process.arn
}
