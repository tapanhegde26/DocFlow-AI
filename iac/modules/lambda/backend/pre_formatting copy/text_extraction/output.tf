output "pdf_lambda_function_arn" {
  description = "ARN of the PDF text extraction Lambda function"
  value       = aws_lambda_function.pdf_text_extraction.arn
}

output "office_lambda_function_arn" {
  description = "ARN of the Office text extraction Lambda function"
  value       = aws_lambda_function.office_text_extraction.arn
}

output "pdf_lambda_function_name" {
  description = "Name of the PDF text extraction Lambda function"
  value       = aws_lambda_function.pdf_text_extraction.function_name
}

output "office_lambda_function_name" {
  description = "Name of the Office text extraction Lambda function"
  value       = aws_lambda_function.office_text_extraction.function_name
}

output "pdf_ecr_repository_url" {
  description = "URL of the PDF Lambda ECR repository"
  value       = aws_ecr_repository.pdf_lambda_image_repo.repository_url
}

output "office_ecr_repository_url" {
  description = "URL of the Office Lambda ECR repository"
  value       = aws_ecr_repository.office_lambda_image_repo.repository_url
}

output "pdf_lambda_role_arn" {
  description = "ARN of the PDF Lambda execution role"
  value       = aws_iam_role.pdf_lambda_exec.arn
}

output "office_lambda_role_arn" {
  description = "ARN of the Office Lambda execution role"
  value       = aws_iam_role.office_lambda_exec.arn
}
