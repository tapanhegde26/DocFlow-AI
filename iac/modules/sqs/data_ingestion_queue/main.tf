resource "aws_sqs_queue" "data_ingestion_queue" {
  name = "${var.prefix}-data-ingestion-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}


resource "aws_sqs_queue" "dlq" {
  name = "${var.prefix}-data-ingestion-dlq"
  tags = {
    Environment = var.environment
    Name     = "AI-KB"
  }
}

