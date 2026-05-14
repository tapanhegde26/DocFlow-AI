terraform {
  required_version = ">= 1.4.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  lambda_name = "${var.prefix}-${var.function_name}"
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

# --- ECR Repository for Lambda Docker Image ---
resource "aws_ecr_repository" "lambda_review_handler_repo" {
  name                 = local.lambda_name
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }

  force_delete = true

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "keep_recent" {
  repository = aws_ecr_repository.lambda_review_handler_repo.name
  policy     = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 30 images"
      selection = {
        tagStatus = "any",
        countType = "imageCountMoreThan",
        countNumber = 30
      }
      action    = { type = "expire" }
    }]
  })
}


# --- Build and Push Docker Image ---
resource "null_resource" "build_and_push_docker_image" {
  triggers = {
    repo_url         = aws_ecr_repository.lambda_review_handler_repo.repository_url
    dockerfile_md5   = filemd5("${path.module}/src/Dockerfile")
    requirements_md5 = filemd5("${path.module}/src/requirements.txt")
    app_py_md5       = fileexists("${path.module}/${var.docker_context_relpath}/app.py") ? filemd5("${path.module}/${var.docker_context_relpath}/app.py") : "none"
    tag              = var.image_tag
    region           = var.aws_region
    module_path      = path.module
  }

  provisioner "local-exec" {
  working_dir = "${path.module}/.."
  interpreter = ["/bin/bash", "-c"]
  command     = <<-EOT
  set -euo pipefail

  # Use a temp Docker config so we don't hit local Keychain at all
  DOCKER_CONFIG_DIR="$(mktemp -d)"
  export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"
  trap 'rm -rf "$DOCKER_CONFIG_DIR"' EXIT

  # Login to ECR
  aws ecr get-login-password --region ${var.aws_region} \
    | docker login --username AWS --password-stdin ${aws_ecr_repository.lambda_review_handler_repo.repository_url}

  # Check if buildx is available, if not use regular docker build
  if docker buildx version >/dev/null 2>&1; then
    echo "Using docker buildx"
    docker buildx create --use >/dev/null 2>&1 || true
    echo "Building from context: ${path.module}"
    docker buildx build \
      --platform=linux/arm64 \
      --provenance=false \
      --sbom=false \
      --output=type=registry,oci-mediatypes=false \
      -t ${aws_ecr_repository.lambda_review_handler_repo.repository_url}:${var.image_tag} \
      -f reviewUI/src/Dockerfile \
      --push ${path.module}
  else
    echo "Using regular docker build"
    echo "Building from context: ${path.module}"
    docker build \
      --platform linux/arm64 \
      -t ${aws_ecr_repository.lambda_review_handler_repo.repository_url}:${var.image_tag} \
      -f reviewUI/src/Dockerfile .

    docker push ${aws_ecr_repository.lambda_review_handler_repo.repository_url}:${var.image_tag}
  fi
  EOT
}

  depends_on = [
    aws_ecr_repository.lambda_review_handler_repo,
    aws_ecr_lifecycle_policy.keep_recent
  ]
}

# --- AWS Lambda Function using Docker Image ---
data "aws_ecr_image" "pushed" {
  repository_name = aws_ecr_repository.lambda_review_handler_repo.name
  image_tag       = var.image_tag
  depends_on      = [null_resource.build_and_push_docker_image]
}

# IAM role (logs + VPC ENI only)
data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${local.lambda_name}-exec"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
  tags               = local.tags
}

# Managed policies: logs + VPC ENI
resource "aws_iam_role_policy_attachment" "basic_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Log group
resource "aws_cloudwatch_log_group" "lg" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

# VPC SG (egress only)
resource "aws_security_group" "lambda_review_sg" {
  name        = "${local.lambda_name}-sg"
  description = "Egress-only SG for ${local.lambda_name}"
  vpc_id      = var.vpc_id

  egress {
    description = "Allow all egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags

  lifecycle {
    ignore_changes  = [name, description, tags]
  }
}

# policy for CloudWatch Logs permissions
resource "aws_iam_role_policy" "review_handler_logging_policy" {
  name = "${var.prefix}-${var.environment}-review-handler-logging"
  role = aws_iam_role.lambda_exec.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${var.environment_variables["APP_LOG_GROUP"]}:*",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${var.environment_variables["AUDIT_LOG_GROUP"]}:*"
        ]
      }
    ]
  })
}

# Lambda in VPC
resource "aws_lambda_function" "lambda_review_handler" {
  function_name = local.lambda_name
  role          = aws_iam_role.lambda_exec.arn

  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda_review_handler_repo.repository_url}@${data.aws_ecr_image.pushed.image_digest}"

  timeout       = var.timeout
  memory_size   = var.memory_size
  architectures = var.architectures

  environment { variables = var.environment_variables }

  vpc_config {
    subnet_ids         = var.vpc_subnet_ids
    security_group_ids = concat(var.vpc_security_group_ids, [aws_security_group.lambda_review_sg.id])
  }

  tags = local.tags

  depends_on = [
    aws_cloudwatch_log_group.lg,
    aws_iam_role_policy_attachment.basic_logs,
    aws_iam_role_policy_attachment.vpc_access
  ]
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy_attachment" "lambda_rds_data_api_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = var.rds_data_api_policy_arn
}

resource "aws_iam_role_policy_attachment" "lambda_secrets_manager_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = var.secrets_manager_read_policy_arn
}

# --- Allow Lambda to read from multiple S3 buckets ---
resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${local.lambda_name}-s3-access"
  role = aws_iam_role.lambda_exec.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowReadFromS3Buckets"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          for b in var.s3_bucket_names : "arn:aws:s3:::${b}/*"
        ]
      }
    ]
  })
}