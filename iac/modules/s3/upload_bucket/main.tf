# modules/s3/upload_bucket/main.tf
resource "aws_s3_bucket" "upload_bucket" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Name     = "AI-KB"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_notification" "upload_bucket" {
  bucket      = aws_s3_bucket.upload_bucket.id
  eventbridge = true
}