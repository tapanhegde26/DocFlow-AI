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
    docker buildx build --platform linux/amd64 --load -t ${var.ecr_repository_name}:add-llm-tags .
    
    # Tag and push
    docker tag ${var.ecr_repository_name}:add-llm-tags ${var.ecr_repository_url}:add-llm-tags
    docker push ${var.ecr_repository_url}:add-llm-tags
  EOT
}
}

# Data source to get the latest image URI from ECR
data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repository_name
  image_tag       = "add-llm-tags"
  
  depends_on = [null_resource.lambda_image_build]
}

resource "aws_lambda_function" "add_llm_tags_to_s3" {
  function_name = "${var.prefix}-data-ingestion-add-llm-tags"
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

# --- IAM Role for Lambda ---
resource "aws_iam_role" "lambda_exec" {
  name = "${var.prefix}-lambda-add-llm-tags-s3-role"

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

resource "aws_iam_role_policy_attachment" "lambda_secrets_manager_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = var.secrets_manager_read_policy_arn
}

/*
# --- NEW: Policy to allow reading from Parameter Store ---
resource "aws_iam_policy" "ssm_parameter_read_policy" {
  name        = "${var.prefix}-lambda-ssm-parameter-read"
  description = "Allows Lambda to read DB connection parameters from Parameter Store"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
        ],
        Effect   = "Allow",
        # Resource must be a list of specific ARNs for the parameters
        Resource = [
          var.db_host_param_arn,
          var.db_name_param_arn,
          var.db_user_param_arn,
          var.db_port_param_arn,
        ],
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_ssm_parameter_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.ssm_parameter_read_policy.arn
}
*/

# --- S3 Permissions (Existing or new, but ensure this Lambda has put_object for tagged_processes and _index) ---
resource "aws_iam_policy" "s3_put_object_policy" {
  name        = "${var.prefix}-lambda-s3-put-object"
  description = "Allows Lambda to put objects to the S3 bucket's tagged_processes paths"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl", # If you need to set ACLs, though S3 bucket policy is usually preferred
          "s3:GetObject" # If the Lambda needs to read the original object from S3 as a fallback (which it does)
        ],
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}/tagged_processes/*",
          "arn:aws:s3:::${var.s3_bucket_name}/processes/*", # For reading original content
        ],
      },
    ],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_put_object_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.s3_put_object_policy.arn
}


resource "aws_iam_role_policy_attachment" "lambda_rds_data_api_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = var.rds_data_api_policy_arn
}