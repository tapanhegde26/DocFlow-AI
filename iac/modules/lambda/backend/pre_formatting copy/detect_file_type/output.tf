output "lambda_function_name" {
  value = aws_lambda_function.detect_file_type.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.detect_file_type.arn
}
