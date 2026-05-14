terraform {
  required_version = ">= 1.4.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

locals {
  tags = {
    Environment = var.environment
    Name        = "AI-KB"
  }
//Sai//Added vars prefix and also added in vars.tf to avoid existing bucket error//
  origin_bucket_name = var.bucket_name != "" ? var.bucket_name : "${var.prefix}-${var.site_name}-${lower(var.environment)}-origin"
  logs_bucket_name   = var.logs_bucket_name != "" ? var.logs_bucket_name : "${var.prefix}-${var.site_name}-${lower(var.environment)}-cf-logs"
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_origin_request_policy" "ua_referrer_headers" {
  name = "Managed-UserAgentRefererHeaders"
}

data "aws_cloudfront_response_headers_policy" "cors_and_security" {
  name = "Managed-CORS-and-SecurityHeadersPolicy"
}

# --- S3: Origin bucket (private)
resource "aws_s3_bucket" "origin" {
  bucket = local.origin_bucket_name
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "origin_pab" {
  bucket                  = aws_s3_bucket.origin.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- S3: Logging bucket (standard logs)
resource "aws_s3_bucket" "logs" {
  bucket = local.logs_bucket_name
  tags   = local.tags
}

# Logging target buckets require ACLs; set ownership/ACL for CloudFront standard logs
resource "aws_s3_bucket_ownership_controls" "logs_ownership" {
  bucket = aws_s3_bucket.logs.id
  rule { object_ownership = "BucketOwnerPreferred" }
}

resource "aws_s3_bucket_acl" "logs_acl" {
  bucket = aws_s3_bucket.logs.id
  acl    = "log-delivery-write"
  depends_on = [aws_s3_bucket_ownership_controls.logs_ownership]
}

# --- Block public access on logs bucket as well (defense-in-depth)
resource "aws_s3_bucket_public_access_block" "logs_pab" {  # ADD ME
  bucket                  = aws_s3_bucket.logs.id         # ADD ME
  block_public_acls       = true                          # ADD ME
  block_public_policy     = true                          # ADD ME
  ignore_public_acls      = true                          # ADD ME
  restrict_public_buckets = true                          # ADD ME
}                                                         # ADD ME

# --- Optional lifecycle to expire logs after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "logs_expiration" {  # ADD ME
  bucket = aws_s3_bucket.logs.id                                      # ADD ME
  rule {                                                              # ADD ME
    id     = "expire-logs"                                            # ADD ME
    status = "Enabled"                                                # ADD ME
    expiration { days = 90 }                                          # ADD ME
    filter { prefix = "" }                                            # ADD ME
  }                                                                   # ADD ME
}

# --- CloudFront Origin Access Control (OAC)
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "${var.prefix}-${var.site_name}-${var.environment}-oac"
  description                       = "OAC for ${var.site_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# --- WAFv2 (CLOUDFRONT scope) in us-east-1
resource "aws_wafv2_web_acl" "this" {
  provider    = aws.us_east_1
  name        = "${var.prefix}-${var.site_name}-${var.environment}-waf"
  description = "Web ACL for ${var.site_name}"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # Add managed rules later if desired

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.prefix}-${var.site_name}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = local.tags
}

# --- CloudFront Distribution
resource "aws_cloudfront_distribution" "this" {
  comment             = var.comment != "" ? var.comment : "${var.prefix} ${var.site_name} (${var.environment})"
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = var.price_class
  default_root_object = var.default_root_object

  web_acl_id = aws_wafv2_web_acl.this.arn

  origin {
    domain_name = aws_s3_bucket.origin.bucket_regional_domain_name
    origin_id   = "s3-${aws_s3_bucket.origin.id}"

    s3_origin_config {
      origin_access_identity = "" # using OAC
    }

    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-${aws_s3_bucket.origin.id}"
    viewer_protocol_policy = "redirect-to-https"  # Redirect HTTP -> HTTPS

    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    compress         = true

    # Attach managed cache/origin request policies
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.ua_referrer_headers.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.cors_and_security.id

  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  logging_config {
    bucket          = aws_s3_bucket.logs.bucket_domain_name
    include_cookies = false # cookie logging off
    prefix          = "${var.site_name}/"
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  # SPA-friendly error responses
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  tags = local.tags

  depends_on = [
    aws_s3_bucket_public_access_block.origin_pab,
    aws_s3_bucket_acl.logs_acl,
    aws_cloudfront_origin_access_control.oac,
    aws_wafv2_web_acl.this,
    aws_s3_bucket_public_access_block.logs_pab,
    aws_s3_bucket_lifecycle_configuration.logs_expiration
  ]
}

# --- S3 Bucket Policy: allow ONLY this CloudFront distribution (OAC)
resource "aws_s3_bucket_policy" "origin_policy" {
  bucket = aws_s3_bucket.origin.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Sid       = "AllowCloudFrontServiceReadOnly",
      Effect    = "Allow",
      Principal = { Service = "cloudfront.amazonaws.com" },
      Action    = ["s3:GetObject"],
      Resource  = ["arn:${data.aws_partition.current.partition}:s3:::${aws_s3_bucket.origin.id}/*"],
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = "arn:${data.aws_partition.current.partition}:cloudfront::${data.aws_caller_identity.current.account_id}:distribution/${aws_cloudfront_distribution.this.id}"
        }
      }
    }]
  })
}

# --- CloudWatch Log Group (for your own use)
resource "aws_cloudwatch_log_group" "cf_group" {
  name              = "/aws/cloudfront/${aws_cloudfront_distribution.this.id}"
  retention_in_days = 14
  tags              = local.tags
}
