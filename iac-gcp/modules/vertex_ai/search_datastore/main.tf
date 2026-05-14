# modules/vertex_ai/search_datastore/main.tf

# Vertex AI Search Data Store for Process Documents (RAG)
resource "google_discovery_engine_data_store" "process_datastore" {
  project                     = var.project_id
  location                    = "global"
  data_store_id               = "${var.prefix}-process-datastore"
  display_name                = "${var.prefix} Process Documents"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]

  document_processing_config {
    default_parsing_config {
      digital_parsing_config {}
    }
  }
}

# Vertex AI Search Data Store for Non-Process Documents (RAG)
resource "google_discovery_engine_data_store" "nonprocess_datastore" {
  project                     = var.project_id
  location                    = "global"
  data_store_id               = "${var.prefix}-nonprocess-datastore"
  display_name                = "${var.prefix} Non-Process Documents"
  industry_vertical           = "GENERIC"
  content_config              = "CONTENT_REQUIRED"
  solution_types              = ["SOLUTION_TYPE_SEARCH"]

  document_processing_config {
    default_parsing_config {
      digital_parsing_config {}
    }
  }
}

# Search Engine for Process Documents
resource "google_discovery_engine_search_engine" "process_engine" {
  project        = var.project_id
  location       = "global"
  engine_id      = "${var.prefix}-process-engine"
  display_name   = "${var.prefix} Process Search Engine"
  data_store_ids = [google_discovery_engine_data_store.process_datastore.data_store_id]
  collection_id  = "default_collection"

  search_engine_config {
    search_tier    = "SEARCH_TIER_ENTERPRISE"
    search_add_ons = ["SEARCH_ADD_ON_LLM"]
  }

  common_config {
    company_name = "TSH Industries"
  }
}

# Search Engine for Non-Process Documents
resource "google_discovery_engine_search_engine" "nonprocess_engine" {
  project        = var.project_id
  location       = "global"
  engine_id      = "${var.prefix}-nonprocess-engine"
  display_name   = "${var.prefix} Non-Process Search Engine"
  data_store_ids = [google_discovery_engine_data_store.nonprocess_datastore.data_store_id]
  collection_id  = "default_collection"

  search_engine_config {
    search_tier    = "SEARCH_TIER_ENTERPRISE"
    search_add_ons = ["SEARCH_ADD_ON_LLM"]
  }

  common_config {
    company_name = "TSH Industries"
  }
}
