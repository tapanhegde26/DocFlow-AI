# modules/s3/standardized_bucket/outputs.tf
output "bucket_name" {
  value = aws_s3_bucket.standardized_bucket.id
}
output "bucket_arn" {
  value = aws_s3_bucket.standardized_bucket.arn
}