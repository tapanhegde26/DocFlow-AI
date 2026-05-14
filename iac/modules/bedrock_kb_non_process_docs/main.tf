terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = "1.49.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9"
    }
  }
}


# ------------------------------------------------------------------------------
# Data Sources
# ------------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}


# Use existing OpenSearch collection instead of creating new one
data "aws_opensearchserverless_collection" "existing_collection" {
  name = var.existing_opensearch_collection_name
}


# ------------------------------------------------------------------------------
# IAM Role for Bedrock Knowledge Base
# ------------------------------------------------------------------------------
resource "aws_iam_role" "bedrock_kb" {
  name               = "${var.prefix}-bedrock-kb-np-docs-role"
  assume_role_policy = data.aws_iam_policy_document.bedrock_assume.json
  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

data "aws_iam_policy_document" "bedrock_assume" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

# ------------------------------------------------------------------------------
# Access Policy for existing collection
# ------------------------------------------------------------------------------
resource "aws_opensearchserverless_access_policy" "bedrock_kb_access" {
  name        = "${var.prefix}-knwlgbs-npd-access"
  type        = "data"
  description = "Allow Bedrock KB role to access existing collection"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index",
          Resource     = ["index/${var.existing_opensearch_collection_name}/*"],
          Permission   = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection",
          Resource     = ["collection/${var.existing_opensearch_collection_name}"],
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        }
      ],
      Principal = [
        aws_iam_role.bedrock_kb.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}


# ------------------------------------------------------------------------------
# IAM Role Policies
# ------------------------------------------------------------------------------
resource "aws_iam_role_policy" "bedrock_kb_policy" {
  name   = "${var.prefix}-bedrock-kb-np-docs-access"
  role   = aws_iam_role.bedrock_kb.id
  policy = data.aws_iam_policy_document.bedrock_kb_bedrock_access.json
}

data "aws_iam_policy_document" "bedrock_kb_bedrock_access" {
  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      "arn:aws:bedrock:${data.aws_region.current.id}::foundation-model/amazon.titan-embed-text-v2:0"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = [
      var.s3_bucket_arn,
      "${var.s3_bucket_arn}/non_distinct_processes/*"
    ]
  }
}

# OpenSearch policy for existing collection
resource "aws_iam_role_policy" "bedrock_kb_aoss_policy" {
  name = "${var.prefix}-bedrock-kb-np-docs-aoss-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = data.aws_opensearchserverless_collection.existing_collection.arn
      }
    ]
  })
}

# ------------------------------------------------------------------------------
# Wait for IAM and Access Policy Propagation
# ------------------------------------------------------------------------------
resource "time_sleep" "wait_for_iam_propagation" {
  depends_on = [
    aws_iam_role_policy.bedrock_kb_policy,
    aws_iam_role_policy.bedrock_kb_aoss_policy,
    aws_opensearchserverless_access_policy.bedrock_kb_access
  ]
  create_duration = "30s"
}



# ------------------------------------------------------------------------------
# Bedrock Knowledge Base
# ------------------------------------------------------------------------------
resource "awscc_bedrock_knowledge_base" "bedrock_knowledge_base" {
  name        = "${var.prefix}-bedrock-nonprocessdocs-kb"
  role_arn    = aws_iam_role.bedrock_kb.arn
  description = var.description
  knowledge_base_configuration = {
    type = "VECTOR"
    vector_knowledge_base_configuration = {
      embedding_model_arn = "arn:aws:bedrock:${data.aws_region.current.id}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }
  storage_configuration = {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration = {
      collection_arn    = data.aws_opensearchserverless_collection.existing_collection.arn
      vector_index_name = var.existing_opensearch_index_name
      field_mapping = {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  depends_on = [
    time_sleep.wait_for_iam_propagation
  ]

  #lifecycle {
  #  prevent_destroy = true
  #}

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# Bedrock Data Source
# ------------------------------------------------------------------------------
resource "awscc_bedrock_data_source" "tsh-industries_kb_datasource" {
  knowledge_base_id = awscc_bedrock_knowledge_base.bedrock_knowledge_base.id
  name              = "tsh-industries-np-kb-DataSource"

  data_source_configuration = {
    type = "S3"
    s3_configuration = {
      bucket_arn = var.s3_bucket_arn
      inclusion_prefixes = [
        "non_distinct_processes/"
      ]
    }
  }

  #lifecycle {
  #  prevent_destroy = true
  #}
}

# ------------------------------------------------------------------------------
# Lambda Function to Sync Bedrock KB
# ------------------------------------------------------------------------------

# IAM Role for Lambda
resource "aws_iam_role" "bedrock_sync_lambda" {
  name = "${var.prefix}-bedrock-sync-np-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

# IAM Policy for Lambda to call Bedrock
resource "aws_iam_role_policy" "bedrock_sync_lambda_policy" {
  name = "${var.prefix}-bedrock-sync-np-lambda-policy"
  role = aws_iam_role.bedrock_sync_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:StartIngestionJob",
          "bedrock:GetIngestionJob",
          "bedrock:ListIngestionJobs"
        ]
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.prefix}-bedrock-sync-np-lambda*"
      }
    ]
  })
}

# Archive Lambda code
data "archive_file" "bedrock_sync_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda_sync_bedrock.py"
  output_path = "${path.module}/lambda_sync_bedrock.zip"
}

# Lambda Function
resource "aws_lambda_function" "bedrock_sync" {
  filename         = data.archive_file.bedrock_sync_lambda.output_path
  function_name    = "${var.prefix}-bedrock-sync-np-lambda"
  role            = aws_iam_role.bedrock_sync_lambda.arn
  handler         = "lambda_sync_bedrock.lambda_handler"
  source_code_hash = data.archive_file.bedrock_sync_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 60

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = awscc_bedrock_knowledge_base.bedrock_knowledge_base.id
      DATA_SOURCE_ID    = split("|", awscc_bedrock_data_source.tsh-industries_kb_datasource.id)[1]
    }
  }

  tags = {
    Name        = "${var.prefix}-bedrock-sync-lambda"
    Environment = var.environment
  }
}

