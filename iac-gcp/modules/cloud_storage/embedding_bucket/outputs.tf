# modules/cloud_storage/embedding_bucket/outputs.tf

output "bucket_name" {
  description = "Name of the bucket"
  value       = google_storage_bucket.embedding.name
}

output "bucket_url" {
  description = "URL of the bucket"
  value       = google_storage_bucket.embedding.url
}

output "bucket_self_link" {
  description = "Self link of the bucket"
  value       = google_storage_bucket.embedding.self_link
}
