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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:chunk-sop .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:chunk-sop ${var.ecr_repository_url}:chunk-sop
    docker push ${var.ecr_repository_url}:chunk-sop
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "chunk-sop"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "chunk_sop" {
  function_name = "${var.prefix}-vectorization-chunk-and-embed"
  role          = aws_iam_role.lambda_exec.arn
  package_type = "Image"
  image_uri    = "${var.ecr_repository_url}@${data.aws_ecr_image.lambda_image.image_digest}"
  timeout       = 60
  memory_size   = 512
  environment {
   variables = var.environment_variables
  }

  tags = {
    Environment = var.environment
    Name     = "AI-KB"
  }

  depends_on = [null_resource.lambda_image_build]
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.prefix}-vectorization-chunk-embed-role"

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Environment = var.environment
    Project     = "AI-KB"
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

resource "aws_iam_role_policy_attachment" "s3_read" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_policy" "bedrock_policy" {
  name = "${var.prefix}-bedrock-embed-access"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel"
        ],
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}

resource "aws_iam_role_policy_attachment" "bedrock_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}
