# Build function package with dependencies included using Docker
resource "null_resource" "lambda_dependencies" {
  triggers = {
    requirements = filemd5("${path.module}/requirements.txt")
    source_code  = filemd5("${path.module}/src/app.py")
  }

  provisioner "local-exec" {
    command = <<-EOT
      cd ${path.module}
      rm -rf lambda_package invoke_bedrock_llm.zip
      mkdir -p lambda_package
      
      # Install dependencies using Docker to ensure Linux compatibility
      docker run --rm \
        -v "$(pwd):/var/task" \
        -w /var/task \
        python:3.13-slim \
        bash -c "pip install -r requirements.txt -t lambda_package/"
      
      # Copy source code
      cp -r src/* lambda_package/
      
      # Clean up unnecessary files to reduce size
      find lambda_package -name "*.pyc" -delete 2>/dev/null || true
      find lambda_package -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
      find lambda_package -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
      find lambda_package -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
    EOT
  }
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_package"
  output_path = "${path.module}/invoke_bedrock_llm.zip"
  depends_on  = [null_resource.lambda_dependencies]
  
  excludes = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.dist-info",
    "tests"
  ]
}

resource "aws_lambda_function" "invoke_bedrock_llm" {
  function_name = "${var.prefix}-invoke-bedrock-llm"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "app.lambda_handler"
  runtime       = "python3.13"
  timeout       = 60
  memory_size   = 256  # Increased memory for better performance
  
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  
  environment {
    variables = var.environment_variables
  }
  
  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.prefix}-exec-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  
  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Attach the basic Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for Bedrock and Knowledge Base access
resource "aws_iam_role_policy" "lambda_policy" {
  name   = "${var.prefix}-llm-policy"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

data "aws_iam_policy_document" "lambda_permissions" {
  # Bedrock Model Access
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      "arn:aws:bedrock:*::foundation-model/*"
    ]
  }
  
  # Bedrock Knowledge Base Access - THIS WAS MISSING
  statement {
    effect = "Allow"
    actions = [
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate"
    ]
    resources = [
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
    ]
  }
  
  # Bedrock Agent Runtime Access
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeAgent"
    ]
    resources = [
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:agent/*"
    ]
  }
  
  # OpenSearch Serverless Access (if your KB uses AOSS)
  statement {
    effect = "Allow"
    actions = [
      "aoss:APIAccessAll"
    ]
    resources = ["*"]
  }
  
  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.prefix}-invoke-bedrock-llm:*"
    ]
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Optional: Create CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.prefix}-invoke-bedrock-kb-llm"
  retention_in_days = 14
  
  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}
