resource "aws_sqs_queue" "pre_formatting_queue" {
  name = "${var.prefix}-pre-formatting-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Environment = var.environment
    Name     = "AI-KB"
  }
}


resource "aws_sqs_queue" "dlq" {
  name = "${var.prefix}-pre-formatting-dlq"
  tags = {
    Environment = var.environment
    Name     = "AI-KB"
  }
}


