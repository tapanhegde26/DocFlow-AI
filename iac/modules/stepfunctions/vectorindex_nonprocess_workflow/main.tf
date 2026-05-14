resource "aws_iam_role" "step_function_role" {
  name = "${var.prefix}-vectorindex-nonprocess-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_iam_role_policy" "sfn_invoke_lambda_policy" {
  name = "${var.prefix}-sfn-nonprocess-invoke-lambda"
  role = aws_iam_role.step_function_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "lambda:InvokeFunction"
        ],
        Resource = [
          var.read_s3_nonprocess_lambda_arn,
          var.chunk_nonprocess_lambda_arn,
          var.embed_nonprocess_lambda_arn,
          var.store_nonprocess_lambda_arn,
          var.bedrock_sync_lambda_arn
        ]
      }
    ]
  })
}

resource "aws_sfn_state_machine" "vector_index" {
  name     = "${var.prefix}-nonprocess-vectorindex"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/state_machine_definition.json", {
    read_s3_nonprocess_lambda_arn  = var.read_s3_nonprocess_lambda_arn,
    chunk_nonprocess_lambda_arn    = var.chunk_nonprocess_lambda_arn,
    embed_nonprocess_lambda_arn    = var.embed_nonprocess_lambda_arn,
    store_nonprocess_lambda_arn    = var.store_nonprocess_lambda_arn,
    bedrock_sync_lambda_arn   = var.bedrock_sync_lambda_arn
  })

  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}
