# Build function package with dependencies included using Docker
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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:identify-distinct-process .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:identify-distinct-process ${var.ecr_repository_url}:identify-distinct-process
    docker push ${var.ecr_repository_url}:identify-distinct-process
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "identify-distinct-process"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "identify_distinct_process" {
  function_name = "${var.prefix}-preformat-identify-distinct-process"
  role          = aws_iam_role.lambda_exec.arn
  # Container image configuration
  package_type = "Image"
  image_uri    = "${var.ecr_repository_url}@${data.aws_ecr_image.lambda_image.image_digest}"
  timeout = 600
  environment {
    variables = var.environment_vars
  }
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.prefix}-preformat-identify-distinct-process-role"

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Environment = var.environment
    Name     = "AI-KB"
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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "textract_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonTextractFullAccess"
}

/*
resource "aws_iam_role_policy_attachment" "s3_read_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}
*/

resource "aws_iam_policy" "bedrock_invoke_policy" {
  name        = "${var.prefix}-identify-distinct-process-bedrock-invoke-policy"
  description = "Allows Lambda to invoke specific Bedrock models"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "*"
      }
    ]
  })
}

/*
data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = ["*"]
  }
}
*/

# Custom S3 policy for read and write access to specific buckets
resource "aws_iam_policy" "s3_access_policy" {
  name        = "${var.prefix}-identify-distinct-process-s3-access-policy"
  description = "Allows Lambda to read and write to specific S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "arn:aws:s3:::${var.prefix}-raw-sop-upload/*",
          "arn:aws:s3:::${var.prefix}-text-extraction/*",
          "arn:aws:s3:::intouchx-prompts/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = [
          "arn:aws:s3:::${var.prefix}-text-extraction/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.prefix}-raw-sop-upload",
          "arn:aws:s3:::${var.prefix}-text-extraction/*",
          "arn:aws:s3:::intouchx-prompts"
        ]
      }
    ]
  })
}

# Attach the S3 access policy
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

# New: Attach Bedrock InvokeModel policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "bedrock_invoke_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.bedrock_invoke_policy.arn
}
