output "sqs_url" {
  value = aws_sqs_queue.vector_queue.id
}

output "sqs_arn" {
  value = aws_sqs_queue.vector_queue.arn
}

output "dlq_arn" {
  value = aws_sqs_queue.dlq.arn
}


