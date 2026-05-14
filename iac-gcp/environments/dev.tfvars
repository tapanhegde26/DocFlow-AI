# =============================================================================
# TSH Industries GenAI Pipeline - Development Environment
# =============================================================================
# Minimal resource configuration for testing and development
# Estimated cost: ~$50-100/month (within free trial credits)
# =============================================================================

# -----------------------------------------------------------------------------
# Project Configuration
# -----------------------------------------------------------------------------
project_id = "tsh-industries-genai-dev"
region     = "us-central1"

# Set to true for local validation without GCP credentials
# Set to false when deploying to actual GCP
skip_gcp_auth = true

# -----------------------------------------------------------------------------
# Environment Settings
# -----------------------------------------------------------------------------
environment = "dev"
labels = {
  environment = "dev"
  project     = "tsh-industries-genai"
  managed_by  = "terraform"
  cost_center = "development"
}

# -----------------------------------------------------------------------------
# VPC Configuration (Minimal)
# -----------------------------------------------------------------------------
vpc_config = {
  create_vpc         = true
  vpc_name           = "tsh-industries-dev-vpc"
  subnet_cidr        = "10.0.0.0/24"
  pods_cidr          = "10.1.0.0/16"
  services_cidr      = "10.2.0.0/20"
  connector_cidr     = "10.8.0.0/28"
  enable_private_ip  = true
  enable_nat         = true
}

# -----------------------------------------------------------------------------
# Cloud Storage Buckets
# -----------------------------------------------------------------------------
storage_config = {
  location      = "US"
  storage_class = "STANDARD"
  versioning    = false  # Disable for dev to save costs
  lifecycle_rules = {
    delete_after_days = 30  # Auto-delete old files in dev
  }
}

# -----------------------------------------------------------------------------
# Cloud Run Services (Minimal Resources)
# -----------------------------------------------------------------------------
cloud_run_config = {
  # Minimal resources for development
  cpu    = "1"
  memory = "512Mi"
  
  # Scale to zero when not in use (cost saving)
  min_instances = 0
  max_instances = 2
  
  # Longer timeout for debugging
  timeout_seconds = 300
  
  # Concurrency
  max_concurrent_requests = 10
}

# Individual service overrides (only for services that need more resources)
cloud_run_services = {
  detect_file_type = {
    cpu           = "1"
    memory        = "512Mi"
    min_instances = 0
    max_instances = 2
  }
  
  document_processor = {
    cpu           = "1"
    memory        = "1Gi"  # Needs more memory for PDF processing
    min_instances = 0
    max_instances = 2
  }
  
  chunking_service = {
    cpu           = "1"
    memory        = "512Mi"
    min_instances = 0
    max_instances = 2
  }
  
  embedding_service = {
    cpu           = "1"
    memory        = "1Gi"
    min_instances = 0
    max_instances = 2
  }
  
  llm_tagging = {
    cpu           = "1"
    memory        = "512Mi"
    min_instances = 0
    max_instances = 2
  }
  
  rag_query = {
    cpu           = "1"
    memory        = "1Gi"
    min_instances = 0
    max_instances = 2
  }
  
  metadata_service = {
    cpu           = "1"
    memory        = "512Mi"
    min_instances = 0
    max_instances = 2
  }
  
  error_handler = {
    cpu           = "0.5"
    memory        = "256Mi"
    min_instances = 0
    max_instances = 1
  }
}

# -----------------------------------------------------------------------------
# Cloud SQL (Minimal - Consider disabling for local testing)
# -----------------------------------------------------------------------------
cloud_sql_config = {
  enabled           = true  # Set to false to skip Cloud SQL and save ~$30/month
  tier              = "db-f1-micro"  # Smallest instance (~$10/month)
  disk_size_gb      = 10
  disk_type         = "PD_HDD"  # HDD is cheaper than SSD
  availability_type = "ZONAL"   # No HA for dev
  backup_enabled    = false     # No backups for dev
  
  database_version  = "POSTGRES_15"
  database_name     = "tsh-industries_metadata"
  
  # Maintenance window (off-hours)
  maintenance_window = {
    day  = 7  # Sunday
    hour = 3  # 3 AM
  }
  
  # Database flags for dev
  database_flags = {
    log_min_duration_statement = "1000"  # Log slow queries > 1s
  }
}

# -----------------------------------------------------------------------------
# GKE Configuration (DISABLED for dev - use Cloud Run only)
# -----------------------------------------------------------------------------
gke_config = {
  enabled = false  # Enable only if you need GKE for testing
  
  # If enabled, use minimal config:
  cluster_name = "tsh-industries-dev-cluster"
  
  # Use Autopilot for simpler management (pay per pod)
  enable_autopilot = true
  
  # Or use Standard with minimal nodes:
  node_pools = {
    default = {
      machine_type   = "e2-small"  # Smallest general-purpose
      min_node_count = 0
      max_node_count = 2
      disk_size_gb   = 30
      preemptible    = true  # Use preemptible for 80% cost savings
    }
  }
}

# -----------------------------------------------------------------------------
# Vertex AI Configuration
# -----------------------------------------------------------------------------
vertex_ai_config = {
  # Embeddings
  embedding_model = "text-embedding-004"
  embedding_dimensions = 768
  
  # LLM for tagging
  llm_model = "gemini-1.5-flash"  # Flash is cheaper than Pro
  llm_temperature = 0.1
  llm_max_tokens = 1024
  
  # Vector Search (DISABLED for dev - use Qdrant locally)
  vector_search_enabled = false
  
  # If enabled:
  vector_search_config = {
    index_display_name = "tsh-industries-dev-index"
    dimensions         = 768
    approximate_neighbors_count = 10
    shard_size         = "SHARD_SIZE_SMALL"
    machine_type       = "e2-standard-2"  # Smallest
    min_replica_count  = 1
    max_replica_count  = 1
  }
}

# -----------------------------------------------------------------------------
# Pub/Sub Configuration
# -----------------------------------------------------------------------------
pubsub_config = {
  # Message retention (shorter for dev)
  message_retention_duration = "600s"  # 10 minutes
  
  # Acknowledgement deadline
  ack_deadline_seconds = 60
  
  # Dead letter policy
  max_delivery_attempts = 3
  
  # Retry policy
  minimum_backoff = "10s"
  maximum_backoff = "60s"
}

# -----------------------------------------------------------------------------
# Eventarc Configuration
# -----------------------------------------------------------------------------
eventarc_config = {
  # Retry policy for triggers
  max_retry_attempts = 3
  min_retry_delay    = "1s"
  max_retry_delay    = "60s"
}

# -----------------------------------------------------------------------------
# Cloud Workflows Configuration
# -----------------------------------------------------------------------------
workflows_config = {
  # Logging level
  log_level = "LOG_ALL_STEPS"  # Verbose logging for dev
  
  # Execution timeout
  execution_timeout = "3600s"  # 1 hour
}

# -----------------------------------------------------------------------------
# Secret Manager
# -----------------------------------------------------------------------------
secrets_config = {
  # Automatic replication for dev (simpler)
  replication_type = "automatic"
}

# -----------------------------------------------------------------------------
# API Gateway (Optional for dev)
# -----------------------------------------------------------------------------
api_gateway_config = {
  enabled = false  # Enable if you need external API access
}

# -----------------------------------------------------------------------------
# Monitoring & Logging
# -----------------------------------------------------------------------------
monitoring_config = {
  # Log retention (shorter for dev to save costs)
  log_retention_days = 7
  
  # Disable expensive monitoring features
  enable_trace_sampling = false
  trace_sampling_rate   = 0.0
  
  # Basic alerting only
  enable_alerting = false
}

# -----------------------------------------------------------------------------
# Security Configuration
# -----------------------------------------------------------------------------
security_config = {
  # Use default service accounts for simplicity in dev
  use_workload_identity = false
  
  # Allow all internal traffic
  allow_internal_traffic = true
  
  # Disable VPC Service Controls for dev
  enable_vpc_sc = false
}

# -----------------------------------------------------------------------------
# Cost Control Settings
# -----------------------------------------------------------------------------
cost_control = {
  # Auto-shutdown idle resources
  enable_auto_shutdown = true
  idle_timeout_minutes = 30
  
  # Budget alerts
  monthly_budget_usd = 100
  alert_thresholds   = [0.5, 0.8, 1.0]  # 50%, 80%, 100%
}
