# modules/api_gateway/main.tf

# API Gateway API
resource "google_api_gateway_api" "api" {
  provider = google-beta
  project  = var.project_id
  api_id   = "${var.prefix}-api"

  labels = var.labels
}

# API Gateway API Config
resource "google_api_gateway_api_config" "api_config" {
  provider      = google-beta
  project       = var.project_id
  api           = google_api_gateway_api.api.api_id
  api_config_id = "${var.prefix}-api-config"

  openapi_documents {
    document {
      path     = "openapi.yaml"
      contents = base64encode(local.openapi_spec)
    }
  }

  gateway_config {
    backend_config {
      google_service_account = var.service_account
    }
  }

  labels = var.labels

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Gateway
resource "google_api_gateway_gateway" "gateway" {
  provider   = google-beta
  project    = var.project_id
  region     = var.region
  api_config = google_api_gateway_api_config.api_config.id
  gateway_id = "${var.prefix}-gateway"

  labels = var.labels
}

locals {
  openapi_spec = <<-EOF
swagger: "2.0"
info:
  title: "${var.prefix} GenAI Pipeline API"
  description: "API for GenAI Data Ingestion Pipeline"
  version: "1.0.0"
schemes:
  - "https"
produces:
  - "application/json"
securityDefinitions:
  api_key:
    type: "apiKey"
    name: "x-api-key"
    in: "header"
paths:
  /health:
    get:
      summary: "Health check endpoint"
      operationId: "healthCheck"
      responses:
        200:
          description: "OK"
      x-google-backend:
        address: "${var.health_check_url}"
        deadline: 30.0
  /chat:
    post:
      summary: "Chat endpoint for RAG queries"
      operationId: "chat"
      security:
        - api_key: []
      parameters:
        - name: "body"
          in: "body"
          required: true
          schema:
            type: "object"
            properties:
              query:
                type: "string"
              user_id:
                type: "string"
              use_agent:
                type: "boolean"
      responses:
        200:
          description: "Successful response"
        401:
          description: "Unauthorized"
      x-google-backend:
        address: "${var.chat_handler_url}"
        deadline: 600.0
  /review:
    get:
      summary: "Get review items"
      operationId: "getReviewItems"
      security:
        - api_key: []
      responses:
        200:
          description: "Successful response"
      x-google-backend:
        address: "${var.review_handler_url}"
        deadline: 60.0
    post:
      summary: "Submit review"
      operationId: "submitReview"
      security:
        - api_key: []
      parameters:
        - name: "body"
          in: "body"
          required: true
          schema:
            type: "object"
      responses:
        200:
          description: "Successful response"
      x-google-backend:
        address: "${var.review_handler_url}"
        deadline: 60.0
EOF
}
