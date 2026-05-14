output "lambda_function_name" {
  description = "Name of the Lambda function"
  value = aws_lambda_function.lambda_review_handler.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value = aws_lambda_function.lambda_review_handler.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_exec.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value = aws_iam_role.lambda_exec.name
}

output "review_security_group_id" {
  description = "Security group ID for the Lambda function"
  value       = var.vpc_subnet_ids != null ? aws_security_group.lambda_review_sg.id : null
}

output "repository_name" {
  value = aws_ecr_repository.lambda_review_handler_repo.name
}

output "repository_url" {
  description = "URL of the ECR repository"
  value = aws_ecr_repository.lambda_review_handler_repo.repository_url
}

output "lambda_invoke_arn" {
  description = "ARN to invoke Lambda function"
  value       = aws_lambda_function.lambda_review_handler.invoke_arn
}
