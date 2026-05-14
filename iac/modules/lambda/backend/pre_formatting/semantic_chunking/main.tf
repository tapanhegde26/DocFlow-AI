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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:semantinc-chunking .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:semantinc-chunking ${var.ecr_repository_url}:semantinc-chunking
    docker push ${var.ecr_repository_url}:semantinc-chunking
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "semantinc-chunking"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "semantic_chunking" {
  function_name = "${var.prefix}-preformat-semantic-chunking"
  role          = aws_iam_role.lambda_exec.arn
  # Container image configuration
  package_type = "Image"
  image_uri    = "${var.ecr_repository_url}@${data.aws_ecr_image.lambda_image.image_digest}"
  timeout = 30
  environment {
    variables = merge(var.environment_vars, {
      SEMANTIC_CHUNKING_BUCKET = "${var.prefix}-text-extraction"
    })
  }
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.prefix}-preformat-semantic-chunking-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
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

# Basic Lambda execution permissions
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

/*
# Fixed Bedrock Access Policy - More specific resource ARN
resource "aws_iam_policy" "bedrock_policy" {
  name = "${var.prefix}-semantic-chunking-bedrock-access"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "bedrock:ListFoundationModels"
        ],
        Resource = "*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

# Always attach Bedrock policy (remove conditional)
resource "aws_iam_role_policy_attachment" "bedrock_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}
*/

# Fixed S3 bucket policy with correct resource ARNs
resource "aws_iam_policy" "s3_bucket_policy" {
  name = "${var.prefix}-s3-semantic-chunking"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::${var.prefix}-text-extraction"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        Resource = [
          "arn:aws:s3:::${var.prefix}-text-extraction/*"
        ]
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_s3_text_extraction" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.s3_bucket_policy.arn
}
