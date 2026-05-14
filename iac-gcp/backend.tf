# IaC-GCP/backend.tf

# Uncomment this block when deploying to GCP with a real state bucket
# terraform {
#   backend "gcs" {
#     bucket = "tsh-industries-terraform-state"
#     prefix = "genai-pipeline"
#   }
# }

# For local testing/validation, use local backend (default)
# To use GCS backend:
# 1. Create the bucket: gsutil mb -l us-central1 gs://tsh-industries-terraform-state
# 2. Uncomment the backend block above
# 3. Run: terraform init -reconfigure
