# S3 bucket notification to send events to EventBridge
resource "aws_s3_bucket_notification" "s3_notification" {
  bucket      = var.bucket_name
  eventbridge = true
}

# EventBridge rule to capture S3 events
resource "aws_cloudwatch_event_rule" "s3_nonprocessdocs_put_rule" {
  name        = "${var.prefix}-non-distinct-process-s3-put-rule"
  description = "Trigger SQS for non distinct process SOP uploads in /non-distinct-process path"
  state       = "ENABLED"
  
  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [var.bucket_name]
      }
      object = {
        key = [{
          prefix = "non_distinct_processes/"
        }]
      }
    }
  })
  
  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

# EventBridge target to send to SQS
resource "aws_cloudwatch_event_target" "send_to_sqs" {
  rule      = aws_cloudwatch_event_rule.s3_nonprocessdocs_put_rule.name
  arn       = var.sqs_queue_arn
  target_id = "${var.prefix}-nonprocessdocs-s3-sqs-target"
  
  dynamic "dead_letter_config" {
    for_each = var.dlq_arn != null ? [1] : []
    content {
      arn = var.dlq_arn
    }
  }
  
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 3
  }
}

# SQS queue policy to allow EventBridge
resource "aws_sqs_queue_policy" "allow_eventbridge" {
  queue_url = var.sqs_queue_url
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowEventBridgeToSendMessages"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action   = "sqs:SendMessage"
      Resource = var.sqs_queue_arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_cloudwatch_event_rule.s3_nonprocessdocs_put_rule.arn
        }
      }
    }]
  })
}

# CloudWatch Log Group for debugging
resource "aws_cloudwatch_log_group" "vector_index_flow_nonprocess_logs" {
  name              = "/aws/events/${var.prefix}-nonprocess-docs-s3-event-debug"
  retention_in_days = 7
  
  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

# Remove the data source and resource policy entirely

# EventBridge target for debugging logs (try without resource policy first)
resource "aws_cloudwatch_event_target" "debug_to_logs" {
  rule      = aws_cloudwatch_event_rule.s3_nonprocessdocs_put_rule.name
  arn       = aws_cloudwatch_log_group.vector_index_flow_nonprocess_logs.arn
  target_id = "${var.prefix}-debug-logs-target"
}
