# modules/vertex_ai/vector_search_index/main.tf

# Vertex AI Vector Search Index for Process Documents
resource "google_vertex_ai_index" "process_index" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.prefix}-process-index"
  description  = "Vector search index for process documents"

  metadata {
    contents_delta_uri = "gs://${var.prefix}-vector-index-data/process/"
    config {
      dimensions                  = var.embedding_dimension
      approximate_neighbors_count = 150
      shard_size                  = "SHARD_SIZE_SMALL"
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"

  labels = var.labels
}

# Vertex AI Vector Search Index for Non-Process Documents
resource "google_vertex_ai_index" "nonprocess_index" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.prefix}-nonprocess-index"
  description  = "Vector search index for non-process documents"

  metadata {
    contents_delta_uri = "gs://${var.prefix}-vector-index-data/nonprocess/"
    config {
      dimensions                  = var.embedding_dimension
      approximate_neighbors_count = 150
      shard_size                  = "SHARD_SIZE_SMALL"
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 1000
          leaf_nodes_to_search_percent = 10
        }
      }
    }
  }

  index_update_method = "STREAM_UPDATE"

  labels = var.labels
}

# Index Endpoint for Process Documents
resource "google_vertex_ai_index_endpoint" "process_endpoint" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.prefix}-process-endpoint"
  description  = "Index endpoint for process document vector search"

  network = var.vpc_network

  labels = var.labels
}

# Index Endpoint for Non-Process Documents
resource "google_vertex_ai_index_endpoint" "nonprocess_endpoint" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.prefix}-nonprocess-endpoint"
  description  = "Index endpoint for non-process document vector search"

  network = var.vpc_network

  labels = var.labels
}

# Deploy Process Index to Endpoint
resource "google_vertex_ai_index_endpoint_deployed_index" "process_deployed" {
  index_endpoint       = google_vertex_ai_index_endpoint.process_endpoint.id
  index                = google_vertex_ai_index.process_index.id
  deployed_index_id    = "${replace(var.prefix, "-", "_")}_process_deployed"
  display_name         = "${var.prefix}-process-deployed"

  dedicated_resources {
    machine_spec {
      machine_type = "e2-standard-2"
    }
    min_replica_count = 1
    max_replica_count = 5
  }

  automatic_resources {
    min_replica_count = 1
    max_replica_count = 5
  }
}

# Deploy Non-Process Index to Endpoint
resource "google_vertex_ai_index_endpoint_deployed_index" "nonprocess_deployed" {
  index_endpoint       = google_vertex_ai_index_endpoint.nonprocess_endpoint.id
  index                = google_vertex_ai_index.nonprocess_index.id
  deployed_index_id    = "${replace(var.prefix, "-", "_")}_nonprocess_deployed"
  display_name         = "${var.prefix}-nonprocess-deployed"

  dedicated_resources {
    machine_spec {
      machine_type = "e2-standard-2"
    }
    min_replica_count = 1
    max_replica_count = 5
  }

  automatic_resources {
    min_replica_count = 1
    max_replica_count = 5
  }
}

# GCS bucket for vector index data
resource "google_storage_bucket" "vector_index_data" {
  name          = "${var.prefix}-vector-index-data"
  project       = var.project_id
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  labels = var.labels
}
