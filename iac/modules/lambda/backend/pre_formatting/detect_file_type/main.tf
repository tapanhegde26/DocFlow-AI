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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:detect-file-type .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:detect-file-type ${var.ecr_repository_url}:detect-file-type
    docker push ${var.ecr_repository_url}:detect-file-type
  EOT
}
}


# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "detect-file-type"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "detect_file_type" {
  function_name = "${var.prefix}-preformat-detect-file-type"
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

resource "aws_iam_role" "lambda_exec" {
  name = "${var.prefix}-preformat-detect-file-type-role"

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

resource "aws_iam_policy" "lambda_s3_access" {
  name = "${var.prefix}-lambda-s3-access"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:HeadObject"
        ],
        Resource = "arn:aws:s3:::${var.prefix}-raw-sop-upload/raw_files/*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = "arn:aws:s3:::${var.prefix}-raw-sop-upload",
        Condition = {
          StringLike = {
            "s3:prefix" = ["raw_files/*"]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

/*
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.detect_file_type.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_bucket_arn  # Pass this from parent module
}

resource "aws_s3_bucket_notification" "trigger_lambda" {
  bucket = var.s3_bucket_id  # Pass this from parent module

  lambda_function {
    lambda_function_arn = aws_lambda_function.detect_file_type.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw_files/"
    filter_suffix       = ""
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
*/