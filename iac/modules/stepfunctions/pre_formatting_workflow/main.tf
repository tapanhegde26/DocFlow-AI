resource "aws_sfn_state_machine" "pre_formatting" {
  name     = "${var.prefix}-pre-formatting-workflow"
  role_arn = aws_iam_role.step_function_role.arn
  
  definition = templatefile("${path.module}/state_machine_definition.json", {
    detect_file_type_lambda_arn        = var.detect_file_type_lambda_arn
    pdf_extract_lambda_arn           = var.pdf_extract_lambda_arn
    office_extract_lambda_arn        = var.office_extract_lambda_arn
    duplicate_detection_lambda_arn   = var.duplicate_detection_lambda_arn
    text_standardize_lambda_arn       = var.text_standardize_lambda_arn
    semantic_chunking_lambda_arn      = var.semantic_chunking_lambda_arn
    identify_distinct_process_lambda_arn = var.identify_distinct_process_lambda_arn
    create_process_docs_lambda_arn    = var.create_process_docs_lambda_arn
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
  name = "${var.prefix}-preformat-step-function-role"

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
  name              = "/aws/vendedlogs/${var.prefix}-pre-formatting-workflow"
  retention_in_days = 14
}

resource "aws_iam_policy" "step_function_logging_policy" {
  name        = "${var.prefix}-preformat-step-function-logging-policy"
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
  name        = "${var.prefix}-preformat-step-function-lambda-invoke-policy"
  description = "Policy for Step Functions to invoke Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "lambda:InvokeFunction",
        Resource = [
          var.detect_file_type_lambda_arn,
          var.pdf_extract_lambda_arn,
          var.office_extract_lambda_arn,
          var.duplicate_detection_lambda_arn,
          var.text_standardize_lambda_arn,
          var.semantic_chunking_lambda_arn,
          var.identify_distinct_process_lambda_arn,
          var.create_process_docs_lambda_arn
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
