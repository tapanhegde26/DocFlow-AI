output "lambda_function_name" {
  value = aws_lambda_function.add_llm_tags_to_s3.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.add_llm_tags_to_s3.arn
}
