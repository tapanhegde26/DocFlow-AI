# modules/cloud_storage/raw_sop_bucket/outputs.tf

output "bucket_name" {
  description = "Name of the bucket"
  value       = google_storage_bucket.raw_sop.name
}

output "bucket_url" {
  description = "URL of the bucket"
  value       = google_storage_bucket.raw_sop.url
}

output "bucket_self_link" {
  description = "Self link of the bucket"
  value       = google_storage_bucket.raw_sop.self_link
}
