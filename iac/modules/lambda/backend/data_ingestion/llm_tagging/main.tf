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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:llm-tagging .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:llm-tagging ${var.ecr_repository_url}:llm-tagging
    docker push ${var.ecr_repository_url}:llm-tagging
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "llm-tagging"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "llm_tagging" {
  function_name = "${var.prefix}-dataingestion-llm-tagging"
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
  name = "${var.prefix}-dataingestion-llm-tagging-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
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

# Bedrock permissions policy
data "aws_iam_policy_document" "bedrock_policy" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
    ]
  }
}

resource "aws_iam_policy" "bedrock_policy" {
  name   = "${var.prefix}-llm-tagging-bedrock-policy"
  policy = data.aws_iam_policy_document.bedrock_policy.json
}


resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

}

resource "aws_iam_role_policy_attachment" "bedrock_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.bedrock_policy.arn
}

# resource "aws_lambda_function" "llm_tagging" {
#   function_name = "${var.prefix}-dataingestion-llm-tagging"
#   role          = aws_iam_role.lambda_exec.arn
#   handler       = "app.lambda_handler"
#   runtime       = "python3.13"
#   timeout       = 30
#   filename      = data.archive_file.lambda.output_path
#   source_code_hash = data.archive_file.lambda.output_base64sha256

#   environment {
#    variables = var.environment_variables  
#   }

#    tags = {
#     Environment = var.environment
#     Name = "AI-KB"
#   }
# }
