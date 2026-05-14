# IaC-GCP/main-hybrid.tf
# GenAI Data Ingestion Pipeline - Hybrid Architecture (Cloud Run + GKE)
# 
# Architecture:
# - Cloud Run: Low-traffic services (6 services)
# - GKE: High-compute services (6 services)

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.25.0"
    }
  }
  required_version = ">= 1.4.0"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Kubernetes provider configured after GKE cluster creation
# Note: For local validation without GCP credentials, this will use placeholder values
# In production, the actual cluster endpoint and token will be used
provider "kubernetes" {
  # Use placeholder values for validation when GCP auth is not available
  # These will be overridden by actual values when deploying to GCP
  host                   = var.skip_gcp_auth ? "https://placeholder.endpoint" : "https://${module.gke_cluster.cluster_endpoint}"
  token                  = var.skip_gcp_auth ? "placeholder-token" : data.google_client_config.default[0].access_token
  cluster_ca_certificate = var.skip_gcp_auth ? "" : base64decode(module.gke_cluster.cluster_ca_certificate)
}

# This data source requires GCP authentication
# It will fail during local validation but work during actual deployment
data "google_client_config" "default" {
  count = var.skip_gcp_auth ? 0 : 1
}

locals {
  common_prefix = "${terraform.workspace}-tsh-industries"
  short_prefix  = "${terraform.workspace}-tsh"  # Short prefix for service accounts (max 30 chars total)
  environment   = var.environment
  labels = {
    environment = var.environment
    project     = "genai-pipeline"
    managed_by  = "terraform"
    architecture = "hybrid"
  }
  
  # Service classification
  cloud_run_services = [
    "detect-file-type",
    "text-standardize", 
    "identify-distinct-process",
    "create-process-docs",
    "read-from-storage",
    "add-llm-tags"
  ]
  
  gke_services = [
    "text-extraction",
    "semantic-chunking",
    "llm-tagging",
    "chunk-sop",
    "generate-embedding",
    "store-to-vector-db"
  ]
}

# Enable required GCP APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "run.googleapis.com",
    "workflows.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
    "aiplatform.googleapis.com",
    "discoveryengine.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "servicenetworking.googleapis.com",
    "vpcaccess.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# =============================================================================
# NETWORKING
# =============================================================================

module "vpc" {
  source = "./modules/vpc"

  project_id    = var.project_id
  prefix        = local.common_prefix
  region        = var.region
  environment   = local.environment
  vpc_cidr      = "10.0.0.0/16"
  subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]

  depends_on = [google_project_service.required_apis]
}

# Secondary ranges for GKE pods and services
resource "google_compute_subnetwork" "gke_subnet" {
  name          = "${local.common_prefix}-gke-subnet"
  project       = var.project_id
  region        = var.region
  network       = module.vpc.network_id
  ip_cidr_range = "10.1.0.0/20"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.2.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.3.0.0/20"
  }

  private_ip_google_access = true

  depends_on = [module.vpc]
}

# =============================================================================
# STORAGE
# =============================================================================

module "raw_sop_bucket" {
  source      = "./modules/cloud_storage/raw_sop_bucket"
  project_id  = var.project_id
  bucket_name = "${local.common_prefix}-raw-sop-upload"
  location    = var.region
  labels      = local.labels
  depends_on  = [google_project_service.required_apis]
}

module "text_extract_bucket" {
  source      = "./modules/cloud_storage/text_extract_bucket"
  project_id  = var.project_id
  bucket_name = "${local.common_prefix}-text-extraction"
  location    = var.region
  labels      = local.labels
  depends_on  = [google_project_service.required_apis]
}

module "standardized_bucket" {
  source      = "./modules/cloud_storage/standardized_bucket"
  project_id  = var.project_id
  bucket_name = "${local.common_prefix}-sop-standardized"
  location    = var.region
  labels      = local.labels
  depends_on  = [google_project_service.required_apis]
}

module "embedding_bucket" {
  source      = "./modules/cloud_storage/embedding_bucket"
  project_id  = var.project_id
  bucket_name = "${local.common_prefix}-sop-embedding"
  location    = var.region
  labels      = local.labels
  depends_on  = [google_project_service.required_apis]
}

# =============================================================================
# ARTIFACT REGISTRY
# =============================================================================

module "artifact_registry" {
  source        = "./modules/artifact_registry"
  project_id    = var.project_id
  repository_id = "${local.common_prefix}-docker-repo"
  location      = var.region
  description   = "Docker repository for GenAI pipeline functions"
  labels        = local.labels
  depends_on    = [google_project_service.required_apis]
}

# =============================================================================
# SECRET MANAGER
# =============================================================================

module "secret_manager" {
  source     = "./modules/secret_manager"
  project_id = var.project_id
  prefix     = local.common_prefix
  labels     = local.labels
  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# GKE CLUSTER (for high-compute services)
# =============================================================================

module "gke_cluster" {
  source = "./modules/gke/cluster"

  project_id             = var.project_id
  prefix                 = local.common_prefix
  region                 = var.region
  vpc_network            = module.vpc.network_self_link
  vpc_subnetwork         = google_compute_subnetwork.gke_subnet.self_link
  pods_range_name        = "pods"
  services_range_name    = "services"
  
  # Node pool configuration
  on_demand_machine_type = var.gke_on_demand_machine_type
  on_demand_min_nodes    = var.gke_on_demand_min_nodes
  on_demand_max_nodes    = var.gke_on_demand_max_nodes
  spot_machine_type      = var.gke_spot_machine_type
  spot_min_nodes         = var.gke_spot_min_nodes
  spot_max_nodes         = var.gke_spot_max_nodes
  
  labels             = local.labels
  deletion_protection = false

  depends_on = [
    google_project_service.required_apis,
    module.vpc,
    google_compute_subnetwork.gke_subnet
  ]
}

# Workload Identity for GKE
module "gke_workload_identity" {
  source = "./modules/gke/workload_identity"

  project_id               = var.project_id
  prefix                   = local.common_prefix
  short_prefix             = local.short_prefix
  k8s_namespace            = "genai-pipeline"
  k8s_service_account_name = "genai-workload-sa"

  depends_on = [module.gke_cluster]
}

# =============================================================================
# CLOUD RUN SERVICES (low-traffic services)
# =============================================================================

# Service Account for Cloud Run
module "cloud_run_service_account" {
  source       = "./modules/service_accounts/cloud_run"
  project_id   = var.project_id
  prefix       = local.common_prefix
  short_prefix = local.short_prefix
}

# detect-file-type (Cloud Run)
module "cloud_run_detect_file_type" {
  source           = "./modules/cloud_run/pre_formatting/detect_file_type"
  project_id       = var.project_id
  prefix           = local.common_prefix
  region           = var.region
  repository_url   = module.artifact_registry.repository_url
  service_account  = module.cloud_run_service_account.email
  vpc_connector_id = module.vpc.vpc_connector_id
  raw_sop_bucket   = module.raw_sop_bucket.bucket_name
  depends_on       = [module.artifact_registry, module.vpc]
}

# text-standardize (Cloud Run)
module "cloud_run_text_standardize" {
  source              = "./modules/cloud_run/pre_formatting/text_standardize"
  project_id          = var.project_id
  prefix              = local.common_prefix
  region              = var.region
  repository_url      = module.artifact_registry.repository_url
  service_account     = module.cloud_run_service_account.email
  vpc_connector_id    = module.vpc.vpc_connector_id
  text_extract_bucket = module.text_extract_bucket.bucket_name
  depends_on          = [module.artifact_registry, module.vpc]
}

# identify-distinct-process (Cloud Run)
module "cloud_run_identify_distinct_process" {
  source              = "./modules/cloud_run/pre_formatting/identify_distinct_process"
  project_id          = var.project_id
  prefix              = local.common_prefix
  region              = var.region
  repository_url      = module.artifact_registry.repository_url
  service_account     = module.cloud_run_service_account.email
  vpc_connector_id    = module.vpc.vpc_connector_id
  text_extract_bucket = module.text_extract_bucket.bucket_name
  depends_on          = [module.artifact_registry, module.vpc]
}

# create-process-docs (Cloud Run)
module "cloud_run_create_process_docs" {
  source              = "./modules/cloud_run/pre_formatting/create_process_docs"
  project_id          = var.project_id
  prefix              = local.common_prefix
  region              = var.region
  repository_url      = module.artifact_registry.repository_url
  service_account     = module.cloud_run_service_account.email
  vpc_connector_id    = module.vpc.vpc_connector_id
  standardized_bucket = module.standardized_bucket.bucket_name
  db_secret_id        = module.secret_manager.db_credentials_secret_id
  db_connection_name  = module.cloud_sql.connection_name
  depends_on          = [module.artifact_registry, module.vpc, module.cloud_sql]
}

# read-from-storage (Cloud Run)
module "cloud_run_read_from_storage" {
  source           = "./modules/cloud_run/data_ingestion/read_from_storage"
  project_id       = var.project_id
  prefix           = local.common_prefix
  region           = var.region
  repository_url   = module.artifact_registry.repository_url
  service_account  = module.cloud_run_service_account.email
  vpc_connector_id = module.vpc.vpc_connector_id
  depends_on       = [module.artifact_registry, module.vpc]
}

# add-llm-tags (Cloud Run)
module "cloud_run_add_llm_tags" {
  source              = "./modules/cloud_run/data_ingestion/add_llm_tags"
  project_id          = var.project_id
  prefix              = local.common_prefix
  region              = var.region
  repository_url      = module.artifact_registry.repository_url
  service_account     = module.cloud_run_service_account.email
  vpc_connector_id    = module.vpc.vpc_connector_id
  standardized_bucket = module.standardized_bucket.bucket_name
  db_secret_id        = module.secret_manager.db_credentials_secret_id
  db_connection_name  = module.cloud_sql.connection_name
  depends_on          = [module.artifact_registry, module.vpc, module.cloud_sql]
}

# =============================================================================
# GKE SERVICE ENDPOINTS (for workflow routing)
# =============================================================================

# Internal load balancer for GKE services
resource "kubernetes_service" "gke_internal_lb" {
  metadata {
    name      = "genai-internal-lb"
    namespace = "genai-pipeline"
    annotations = {
      "cloud.google.com/load-balancer-type" = "Internal"
    }
  }

  spec {
    type = "LoadBalancer"
    
    selector = {
      "app.kubernetes.io/part-of" = "genai-pipeline"
    }

    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }
  }

  depends_on = [module.gke_cluster]
}

# =============================================================================
# PUB/SUB
# =============================================================================

module "pubsub_pre_formatting" {
  source     = "./modules/pubsub/pre_formatting_topic"
  project_id = var.project_id
  prefix     = local.common_prefix
  labels     = local.labels
  depends_on = [google_project_service.required_apis]
}

module "pubsub_data_ingestion" {
  source     = "./modules/pubsub/data_ingestion_topic"
  project_id = var.project_id
  prefix     = local.common_prefix
  labels     = local.labels
  depends_on = [google_project_service.required_apis]
}

module "pubsub_vector_process" {
  source     = "./modules/pubsub/vector_process_topic"
  project_id = var.project_id
  prefix     = local.common_prefix
  labels     = local.labels
  depends_on = [google_project_service.required_apis]
}

module "pubsub_vector_nonprocess" {
  source     = "./modules/pubsub/vector_nonprocess_topic"
  project_id = var.project_id
  prefix     = local.common_prefix
  labels     = local.labels
  depends_on = [google_project_service.required_apis]
}

# =============================================================================
# CLOUD WORKFLOWS (Hybrid routing)
# =============================================================================

module "workflow_service_account" {
  source       = "./modules/service_accounts/workflows"
  project_id   = var.project_id
  prefix       = local.common_prefix
  short_prefix = local.short_prefix
}

module "workflow_pre_formatting_hybrid" {
  source = "./modules/cloud_workflows/pre_formatting_workflow_hybrid"

  project_id      = var.project_id
  prefix          = local.common_prefix
  region          = var.region
  service_account = module.workflow_service_account.email

  # Cloud Run services
  detect_file_type_url          = module.cloud_run_detect_file_type.service_url
  text_standardize_url          = module.cloud_run_text_standardize.service_url
  identify_distinct_process_url = module.cloud_run_identify_distinct_process.service_url
  create_process_docs_url       = module.cloud_run_create_process_docs.service_url
  
  # GKE services (internal endpoints)
  text_extraction_url   = "http://text-extraction.genai-pipeline.svc.cluster.local"
  semantic_chunking_url = "http://semantic-chunking.genai-pipeline.svc.cluster.local"

  depends_on = [
    module.cloud_run_detect_file_type,
    module.cloud_run_text_standardize,
    module.cloud_run_identify_distinct_process,
    module.cloud_run_create_process_docs,
    module.gke_cluster
  ]
}

module "workflow_data_ingestion_hybrid" {
  source = "./modules/cloud_workflows/data_ingestion_workflow_hybrid"

  project_id      = var.project_id
  prefix          = local.common_prefix
  region          = var.region
  service_account = module.workflow_service_account.email

  # Cloud Run services
  read_from_storage_url = module.cloud_run_read_from_storage.service_url
  add_llm_tags_url      = module.cloud_run_add_llm_tags.service_url
  
  # GKE services
  llm_tagging_url = "http://llm-tagging.genai-pipeline.svc.cluster.local"

  depends_on = [
    module.cloud_run_read_from_storage,
    module.cloud_run_add_llm_tags,
    module.gke_cluster
  ]
}

module "workflow_vectorindex_hybrid" {
  source = "./modules/cloud_workflows/vectorindex_workflow_hybrid"

  project_id      = var.project_id
  prefix          = local.common_prefix
  region          = var.region
  service_account = module.workflow_service_account.email

  # Cloud Run services
  read_sop_url = module.cloud_run_read_from_storage.service_url
  
  # GKE services
  chunk_sop_url      = "http://chunk-sop.genai-pipeline.svc.cluster.local"
  generate_embed_url = "http://generate-embedding.genai-pipeline.svc.cluster.local"
  store_vector_url   = "http://store-to-vector-db.genai-pipeline.svc.cluster.local"

  depends_on = [
    module.cloud_run_read_from_storage,
    module.gke_cluster
  ]
}

# =============================================================================
# VERTEX AI
# =============================================================================

module "vertex_ai_vector_search" {
  source              = "./modules/vertex_ai/vector_search_index"
  project_id          = var.project_id
  prefix              = local.common_prefix
  region              = var.region
  labels              = local.labels
  embedding_dimension = 768
  depends_on          = [google_project_service.required_apis]
}

module "vertex_ai_search" {
  source                  = "./modules/vertex_ai/search_datastore"
  project_id              = var.project_id
  prefix                  = local.common_prefix
  region                  = var.region
  standardized_bucket     = module.standardized_bucket.bucket_name
  text_extract_bucket     = module.text_extract_bucket.bucket_name
  depends_on = [
    google_project_service.required_apis,
    module.standardized_bucket,
    module.text_extract_bucket
  ]
}

# =============================================================================
# CLOUD SQL
# =============================================================================

module "cloud_sql" {
  source           = "./modules/cloud_sql"
  project_id       = var.project_id
  prefix           = local.common_prefix
  region           = var.region
  database_name    = "tsh-industries_db"
  database_user    = "tsh-industries_admin"
  vpc_network_id   = module.vpc.network_id
  private_ip_range = module.vpc.private_ip_range_name
  labels           = local.labels
  depends_on       = [google_project_service.required_apis, module.vpc]
}

# =============================================================================
# API GATEWAY
# =============================================================================

module "api_gateway_service_account" {
  source       = "./modules/service_accounts/api_gateway"
  project_id   = var.project_id
  prefix       = local.common_prefix
  short_prefix = local.short_prefix
}

module "api_gateway" {
  source          = "./modules/api_gateway"
  project_id      = var.project_id
  prefix          = local.common_prefix
  region          = var.region
  service_account = module.api_gateway_service_account.email
  depends_on      = [google_project_service.required_apis]
}
