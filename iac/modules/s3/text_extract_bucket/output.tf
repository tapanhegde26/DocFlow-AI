# modules/s3/text_extract_bucket/outputs.tf
output "bucket_name" {
  value = aws_s3_bucket.text_extract_bucket.id
}
output "bucket_arn" {
  value = aws_s3_bucket.text_extract_bucket.arn
}