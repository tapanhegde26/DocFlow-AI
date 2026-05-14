output "sqs_url" {
  value = aws_sqs_queue.pre_formatting_queue.id
}

output "sqs_arn" {
  value = aws_sqs_queue.pre_formatting_queue.arn
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}