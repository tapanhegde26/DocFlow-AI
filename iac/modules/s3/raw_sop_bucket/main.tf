# S3 Bucket
resource "aws_s3_bucket" "upload_bucket" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
  }
}

# S3 Bucket Notification
resource "aws_s3_bucket_notification" "upload_bucket" {
  bucket      = aws_s3_bucket.upload_bucket.id
  eventbridge = true
  depends_on = [aws_s3_bucket.upload_bucket]
}

# Create "raw_files" folder by uploading a placeholder object
resource "aws_s3_object" "raw_files_folder" {
  bucket       = aws_s3_bucket.upload_bucket.id
  key          = "raw_files/test.txt"
  content      = "This file ensures the raw_files folder exists in S3 console"
  content_type = "text/plain"

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
    Purpose     = "Folder placeholder"
  }
}

# Create "extracted-text" folder by uploading a placeholder object
resource "aws_s3_object" "extracted_text_folder" {
  bucket       = aws_s3_bucket.upload_bucket.id
  key          = "extracted-text/test.txt"
  content      = "This file ensures the extracted-text folder exists in S3 console"
  content_type = "text/plain"

  tags = {
    Name        = "AI-KB"
    Environment = var.environment
    Purpose     = "Folder placeholder"
  }
}

# S3 Bucket Policy to allow EventBridge
resource "aws_s3_bucket_policy" "eventbridge_policy" {
  bucket = aws_s3_bucket.upload_bucket.id

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
        Resource = aws_s3_bucket.upload_bucket.arn
      }
    ]
  })
}
