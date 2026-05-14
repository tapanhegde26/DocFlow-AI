resource "aws_cloudwatch_event_rule" "s3_put_rule" {
  name        = "${var.prefix}-raws-sop-s3-put-rule"
  description = "Trigger SQS on S3 PutObject"
  state       = "ENABLED"

  event_pattern = jsonencode({
    source      = ["aws.s3"],
    "detail-type" = ["Object Created"],
    detail = {
      bucket = {
        name = [var.bucket_name]
      }
      object = {
        key = [{
          prefix = "raw_files/"
        }]
      }
    }
  })
   tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}


resource "aws_cloudwatch_event_target" "preformat_send_to_sqs" {
  rule      = aws_cloudwatch_event_rule.s3_put_rule.name
  arn       = var.sqs_queue_arn
  target_id = "${var.prefix}-preformat-s3-sqs-target"

  # Add dead letter config for failed deliveries (optional)
  dynamic "dead_letter_config" {
    for_each = var.dlq_arn != null ? [1] : []
    content {
      arn = var.dlq_arn
    }
  }

  # Add retry policy
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 3
  }
}

resource "aws_sqs_queue_policy" "allow_eventbridge" {
  queue_url = var.sqs_queue_url
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowEventBridgeToSendMessages"
      Effect    = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action   = "sqs:SendMessage"
      Resource = var.sqs_queue_arn
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_cloudwatch_event_rule.s3_put_rule.arn
        }
      }
    }]
  })
}

resource "aws_cloudwatch_log_group" "pre_format_flow_eventbridge_logs" {
  name              = "/aws/events/${var.prefix}-raw-sop-s3-event-debug"
  retention_in_days = 7

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

/*
# Use the correct resource type for CloudWatch Logs resource policy
resource "aws_cloudwatch_log_resource_policy" "eventbridge_logs_policy" {
  policy_name = "${var.prefix}-eventbridge-logs-policy"
  
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "EventBridgeLogsPolicy"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${aws_cloudwatch_log_group.pre_format_flow_eventbridge_logs.arn}:*"
    }]
  })
}
*/



resource "aws_cloudwatch_event_target" "debug_to_logs" {
  rule      = aws_cloudwatch_event_rule.s3_put_rule.name
  arn       = aws_cloudwatch_log_group.pre_format_flow_eventbridge_logs.arn
  target_id = "${var.prefix}-pre-format-debug-logs-target"
}
