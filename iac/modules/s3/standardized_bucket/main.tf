# modules/s3/standardized_bucket/main.tf
resource "aws_s3_bucket" "standardized_bucket" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_notification" "standardized_bucket" {
  bucket      = aws_s3_bucket.standardized_bucket.id
  eventbridge = true
  depends_on = [
    aws_s3_bucket.standardized_bucket
  ]
}