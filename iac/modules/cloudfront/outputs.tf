output "distribution_id" {
  value       = aws_cloudfront_distribution.this.id
  description = "CloudFront distribution ID"
}

output "distribution_domain_name" {
  value       = aws_cloudfront_distribution.this.domain_name
  description = "CloudFront distribution DNS name"
}

output "origin_bucket_name" {
  value       = aws_s3_bucket.origin.id
  description = "Origin S3 bucket name"
}

output "origin_bucket_arn" {
  description = "ARN of the origin bucket"
  value       = aws_s3_bucket.origin.arn
}

# Public access block (origin)
output "origin_bucket_public_access_block" {
  description = "Public access block settings for the origin bucket (should all be true)"
  value = {
    block_public_acls       = aws_s3_bucket_public_access_block.origin_pab.block_public_acls
    block_public_policy     = aws_s3_bucket_public_access_block.origin_pab.block_public_policy
    ignore_public_acls      = aws_s3_bucket_public_access_block.origin_pab.ignore_public_acls
    restrict_public_buckets = aws_s3_bucket_public_access_block.origin_pab.restrict_public_buckets
  }
}

# Bucket policy JSON applied to the origin bucket (OAC-only access)
output "origin_bucket_policy_json" {
  description = "JSON bucket policy that restricts S3 object access to this CloudFront distribution via OAC"
  value       = aws_s3_bucket_policy.origin_policy.policy
}

# The exact SourceArn used in the policy condition
output "cloudfront_source_arn" {
  description = "The CloudFront distribution ARN used in the origin bucket policy condition"
  value       = "arn:${data.aws_partition.current.partition}:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${aws_cloudfront_distribution.this.id}"
}

output "logs_bucket_name" {
  value       = aws_s3_bucket.logs.id
  description = "S3 bucket for CloudFront standard logs"
}

output "waf_arn" {
  value       = aws_wafv2_web_acl.this.arn
  description = "WAFv2 Web ACL ARN"
}

output "cloudwatch_log_group" {
  value       = aws_cloudwatch_log_group.cf_group.name
  description = "Created CloudWatch log group (CF does not write here automatically)"
}
