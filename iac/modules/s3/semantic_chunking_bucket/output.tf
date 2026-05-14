# modules/s3/text_extract_bucket/outputs.tf
output "bucket_name" {
  value = aws_s3_bucket.semantic_chunking_bucket.id
}
output "bucket_arn" {
  value = aws_s3_bucket.semantic_chunking_bucket.arn
}