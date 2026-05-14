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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:store-to-aoss .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:store-to-aoss ${var.ecr_repository_url}:store-to-aoss
    docker push ${var.ecr_repository_url}:store-to-aoss
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "store-to-aoss"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "store_vector_db" {
  function_name = "${var.prefix}-vectorization-store-vector-db"
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
  name = "${var.prefix}-vectorization-store-vector-db"
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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Comprehensive S3 access policy
data "aws_iam_policy_document" "lambda_s3_access" {
  statement {
    sid    = "AllowS3ReadFromEmbeddingBucket"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.prefix}-dev-sop-embedding",
      "arn:aws:s3:::${var.prefix}-dev-sop-embedding/*"
    ]
  }
}

resource "aws_iam_policy" "lambda_s3_access" {
  name        = "${var.prefix}-vectorization-lambda-s3-access"
  description = "Comprehensive S3 access for vectorization Lambda"
  policy      = data.aws_iam_policy_document.lambda_s3_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

# Updated AOSS access policy with comprehensive permissions
data "aws_iam_policy_document" "aoss_access" {
  statement {
    sid    = "AllowOpenSearchServerlessAccess"
    effect = "Allow"
    actions = [
      "aoss:BatchPutDocument",
      "aoss:APIAccessAll",
      "aoss:WriteDocument",
      "aoss:ReadDocument",
      "aoss:CreateIndex",
      "aoss:DeleteIndex",
      "aoss:UpdateIndex",
      "aoss:DescribeIndex",
      "aoss:DescribeCollectionItems",
      "aoss:CreateCollectionItems",
      "aoss:DeleteCollectionItems",
      "aoss:UpdateCollectionItems"
    ]
    resources = ["*"]
  }

  # Add specific permissions for ES HTTP operations
  statement {
    sid    = "AllowESHTTPOperations"
    effect = "Allow"
    actions = [
      "es:ESHttpDelete",
      "es:ESHttpGet",
      "es:ESHttpHead",
      "es:ESHttpPost",
      "es:ESHttpPut"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "aoss_access" {
  name   = "${var.prefix}-vectorization-aoss-access"
  policy = data.aws_iam_policy_document.aoss_access.json
}

resource "aws_iam_role_policy_attachment" "aoss_access_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.aoss_access.arn
}

# Remove the duplicate/conflicting S3 policy
# resource "aws_iam_policy" "lambda_s3_getobject" { ... } - REMOVED
# resource "aws_iam_role_policy_attachment" "lambda_s3_getobject_attach" { ... } - REMOVED

# OpenSearch Serverless data access policy
resource "aws_opensearchserverless_access_policy" "lambda_data_access" {
  name = "${var.prefix}-lambda-dt-access"
  type = "data"
  
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/*/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection"
          Resource     = ["collection/*"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        }
      ]
      Principal = [
        "arn:aws:iam::381492081885:role/aws-reserved/sso.amazonaws.com/AWSReservedSSO_AdministratorAccess_04a46f8912deb967",
        aws_iam_role.lambda_exec.arn
      ]
    }
  ])
}


# Optional: CloudWatch logs retention
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.store_vector_db.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = "AI-KB"
  }
}
