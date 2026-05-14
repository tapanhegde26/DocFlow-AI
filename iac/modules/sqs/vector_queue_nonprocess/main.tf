resource "aws_sqs_queue" "vector_queue" {
  name = "${var.prefix}-vector-nonprocess-queue"

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
  name = "${var.prefix}-vector-nonprocess-dlq"
   tags = {
    Environment = var.environment
    Name     = "AI-KB"
  }
}


