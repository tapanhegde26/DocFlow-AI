# Build and push Docker image to ECR
resource "null_resource" "lambda_image_build" {
  triggers = {
    requirements = filemd5("${path.module}/requirements.txt")
    source_code  = filemd5("${path.module}/src/app.py")
    dockerfile   = filemd5("${path.module}/Dockerfile")
  }

  provisioner "local-exec" {
  command = <<-EOT
    cd ${path.module}
    
    # Get AWS account ID and region
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION="ca-central-1"
    
    # Ensure ECR repository exists
    aws ecr describe-repositories --repository-names ${var.ecr_repository_name} --region $AWS_REGION || aws ecr create-repository --repository-name ${var.ecr_repository_name} --region $AWS_REGION
    
    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Setup buildx and build with explicit platform
    docker buildx create --use --name lambda-builder || docker buildx use lambda-builder
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:read-sop-s3 .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:read-sop-s3 ${var.ecr_repository_url}:read-sop-s3
    docker push ${var.ecr_repository_url}:read-sop-s3
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "read-sop-s3"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "read_sop_s3" {
  function_name = "${var.prefix}-vectorization-read-sop-s3"
  role          = aws_iam_role.lambda_exec.arn
  # Container image configuration
  package_type = "Image"
  image_uri    = "${var.ecr_repository_url}@${data.aws_ecr_image.lambda_image.image_digest}"
  timeout = 30
  environment {
    variables = var.environment_variables
  }
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
  depends_on = [null_resource.lambda_image_build]
}

# IAM Role for Lambda execution
resource "aws_iam_role" "lambda_exec" {
  name               = "${var.prefix}-vectorization-read-sop-s3"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Environment = var.environment
    Name        = "AI_KB"
  }
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Enhanced S3 read policy with proper permissions
data "aws_iam_policy_document" "lambda_s3_access" {
  statement {
    sid    = "AllowS3GetObject"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion"
    ]
    resources = [
      "arn:aws:s3:::${var.bucket_name}/tagged_processes/*"
    ]
  }

  statement {
    sid    = "AllowS3ListBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.bucket_name}"
    ]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["tagged_processes/*"]
    }
  }
}

resource "aws_iam_policy" "lambda_s3_read_policy" {
  name        = "${var.prefix}-vectorization-s3-read"
  description = "Allows Lambda to read S3 objects from tagged_processes folder"
  policy      = data.aws_iam_policy_document.lambda_s3_access.json

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_s3_read_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_s3_read_policy.arn
}
