data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name        = var.encryption_policy_name
  type        = "encryption"
  description = "Encryption policy for ${var.collection_name}"
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.collection_name}"
        ],
        ResourceType = "collection"
      }
    ],
    AWSOwnedKey = true
  })
}

# OpenSearch Serverless Network Policies
resource "aws_opensearchserverless_security_policy" "network_policy" {
  name        = var.network_policy_name
  type        = "network"
  description = "Network policy for ${var.collection_name}"
  policy = jsonencode([
    {
      Description = "VPC access for collection endpoint",
      Rules = [
        {
          ResourceType = "collection",
          Resource = [
            "collection/${var.collection_name}"
          ]
        }
      ],
      AllowFromPublic = true
    },
    {
      Description = "Public access for dashboards",
      Rules = [
        {
          ResourceType = "dashboard",
          Resource = [
            "collection/${var.collection_name}"
          ]
        }
      ],
      AllowFromPublic = true
    }
  ])
}

# OpenSearch Serverless Data Access Policies
resource "aws_opensearchserverless_access_policy" "data_access_policy" {
  name        = var.data_access_policy_name
  type        = "data"
  description = "Data access policy for ${var.collection_name}"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index",
          Resource = [
            "index/${var.collection_name}/*"
          ],
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
          ResourceType = "collection",
          Resource = [
            "collection/${var.collection_name}"
          ],
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        }
      ],
      Principal = compact(concat(var.principals, var.bedrock_kb_role_arn != "" ? [var.bedrock_kb_role_arn] : []))
    }
  ])
}

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "collection" {
  name = var.collection_name
  type = var.collection_type
  depends_on = [
    aws_opensearchserverless_security_policy.encryption_policy,
    aws_opensearchserverless_security_policy.network_policy,
    aws_opensearchserverless_access_policy.data_access_policy
  ]

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

resource "aws_cloudwatch_log_group" "opensearch_logs" {
  name              = "/aws/aoss/${var.collection_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
}

# Wait for collection to be active
resource "time_sleep" "wait_for_collection" {
  depends_on      = [aws_opensearchserverless_collection.collection]
  create_duration = "120s"
}

# Make script executable
resource "null_resource" "make_script_executable" {
  provisioner "local-exec" {
    command = "chmod +x ${path.module}/create_index.sh"
  }

  triggers = {
    script_hash = filemd5("${path.module}/create_index.sh")
  }
}

resource "null_resource" "create_opensearch_index" {
  depends_on = [
    aws_opensearchserverless_collection.collection,
    aws_opensearchserverless_access_policy.data_access_policy,
    time_sleep.wait_for_collection
  ]

  provisioner "local-exec" {
    command = "${path.module}/create_index.sh '${aws_opensearchserverless_collection.collection.collection_endpoint}' '${var.index_name}' '${data.aws_region.current.id}'"
  }

  provisioner "local-exec" {
    when    = destroy
    command = "echo 'Index cleanup would go here if needed'"
  }

  triggers = {
    collection_id = aws_opensearchserverless_collection.collection.id
    index_name    = var.index_name
    timestamp     = timestamp()
  }
}
