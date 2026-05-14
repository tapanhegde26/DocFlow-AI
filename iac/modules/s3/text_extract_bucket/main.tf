# modules/s3/text_extract/main.tf
resource "aws_s3_bucket" "text_extract_bucket" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

# S3 Bucket Notification
resource "aws_s3_bucket_notification" "text_extract_bucket" {
  bucket      = aws_s3_bucket.text_extract_bucket.id
  eventbridge = true
  depends_on = [aws_s3_bucket.text_extract_bucket]
}

# S3 Bucket Policy to allow EventBridge
resource "aws_s3_bucket_policy" "eventbridge_policy" {
  bucket = aws_s3_bucket.text_extract_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeAccess"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = [
          "s3:GetBucketNotification",
          "s3:PutBucketNotification"
        ]
        Resource = aws_s3_bucket.text_extract_bucket.arn
      }
    ]
  })
}