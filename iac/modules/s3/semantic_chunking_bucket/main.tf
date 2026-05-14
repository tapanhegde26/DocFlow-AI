# modules/s3/embedding_bucket/main.tf
resource "aws_s3_bucket" "semantic_chunking_bucket" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}
