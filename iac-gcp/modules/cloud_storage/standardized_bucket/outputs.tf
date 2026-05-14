# modules/cloud_storage/standardized_bucket/outputs.tf

output "bucket_name" {
  description = "Name of the bucket"
  value       = google_storage_bucket.standardized.name
}

output "bucket_url" {
  description = "URL of the bucket"
  value       = google_storage_bucket.standardized.url
}

output "bucket_self_link" {
  description = "Self link of the bucket"
  value       = google_storage_bucket.standardized.self_link
}
