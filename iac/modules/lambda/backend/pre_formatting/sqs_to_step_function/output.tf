output "lambda_function_name" {
  value = aws_lambda_function.sqs_to_sfn.function_name
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_exec_role.arn
}

output "lambda_function_arn" {
  value = aws_lambda_function.sqs_to_sfn.arn
}