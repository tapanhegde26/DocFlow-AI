# modules/s3/embedding_bucket/outputs.tf
output "bucket_name" {
  value = aws_s3_bucket.embedding_bucket.id
}
output "bucket_arn" {
  value = aws_s3_bucket.embedding_bucket.arn
}