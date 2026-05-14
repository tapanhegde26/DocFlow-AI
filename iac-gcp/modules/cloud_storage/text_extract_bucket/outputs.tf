# modules/cloud_storage/text_extract_bucket/outputs.tf

output "bucket_name" {
  description = "Name of the bucket"
  value       = google_storage_bucket.text_extract.name
}

output "bucket_url" {
  description = "URL of the bucket"
  value       = google_storage_bucket.text_extract.url
}

output "bucket_self_link" {
  description = "Self link of the bucket"
  value       = google_storage_bucket.text_extract.self_link
}
