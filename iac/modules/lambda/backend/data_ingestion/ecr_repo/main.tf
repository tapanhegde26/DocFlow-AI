locals {
  tags = {
    Environment = var.environment
    Name        = var.project_name
  }
}

resource "aws_ecr_repository" "repository" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability
  force_delete         = var.force_delete

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  tags = merge(local.tags, var.additional_tags)
}

resource "aws_ecr_lifecycle_policy" "lifecycle_policy" {
  count      = var.enable_lifecycle_policy ? 1 : 0
  repository = aws_ecr_repository.repository.name

  policy = jsonencode({
    rules = [{
      rulePriority = var.lifecycle_rule_priority
      description  = var.lifecycle_rule_description
      selection = {
        tagStatus   = var.lifecycle_tag_status
        countType   = var.lifecycle_count_type
        countNumber = var.lifecycle_count_number
      }
      action = { type = "expire" }
    }]
  })
}
