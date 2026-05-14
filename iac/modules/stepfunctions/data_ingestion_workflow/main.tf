resource "aws_sfn_state_machine" "data_ingestion" {
  name     = "${var.prefix}-data-ingestion-workflow"
  role_arn = aws_iam_role.step_function_role.arn
  
  definition = templatefile("${path.module}/state_machine_definition.json", {
    read_process_from_s3_lambda_arn        = var.read_process_from_s3_lambda_arn
    llm_based_tagging_lambda_arn       = var.llm_based_tagging_lambda_arn
    add_LLMTags_To_ProcessedDocs_lambda_arn = var.add_LLMTags_To_ProcessedDocs_lambda_arn
  })

  logging_configuration {
    level                  = "ALL"
    include_execution_data = true
    log_destination        = "${aws_cloudwatch_log_group.step_function_logs.arn}:*"
  }

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_iam_role" "step_function_role" {
  name = "${var.prefix}-data-ingestion-step-function-role"

  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Environment = var.environment
    Name     = "AI-KB"
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "step_function_logs" {
  name              = "/aws/vendedlogs/${var.prefix}-data-ingestion-workflow"
  retention_in_days = 14
}

resource "aws_iam_policy" "step_function_logging_policy" {
  name        = "${var.prefix}-data-ingestion-step-function-logging-policy"
  description = "Policy for Step Functions to write to CloudWatch Logs"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ],
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name = "AI-KB"
  }
}

resource "aws_iam_role_policy_attachment" "step_function_logging_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_logging_policy.arn
}

resource "aws_iam_policy" "lambda_invoke_policy" {
  name        = "${var.prefix}-data-ingestion-step-function-lambda-invoke-policy"
  description = "Policy for Step Functions to invoke Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "lambda:InvokeFunction",
        Resource = [
          var.read_process_from_s3_lambda_arn,
          var.llm_based_tagging_lambda_arn,
          var.add_LLMTags_To_ProcessedDocs_lambda_arn
        ]
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_invoke_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.lambda_invoke_policy.arn
}
