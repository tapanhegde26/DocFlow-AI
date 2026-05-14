output "rule_name" {
  description = "Name of the EventBridge rule for standardized S3 bucket"
  value       = aws_cloudwatch_event_rule.s3_standardized_put_rule.name
}

output "rule_arn" {
  description = "ARN of the EventBridge rule for standardized S3 bucket"
  value       = aws_cloudwatch_event_rule.s3_standardized_put_rule.arn
}
