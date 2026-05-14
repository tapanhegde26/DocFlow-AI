# modules/s3/upload_bucket/outputs.tf
output "bucket_name" {
  value = aws_s3_bucket.upload_bucket.id
}
output "bucket_arn" {
  value = aws_s3_bucket.upload_bucket.arn
}