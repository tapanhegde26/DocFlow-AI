#!/bin/bash
# =============================================================================
# TSH Industries GenAI Pipeline - Local Development Setup Script
# =============================================================================
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="tsh-industries-local"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed. Please install it first."
        return 1
    fi
    log_success "$1 is installed"
}

# -----------------------------------------------------------------------------
# Prerequisites Check
# -----------------------------------------------------------------------------
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=0
    
    check_command "docker" || missing=1
    check_command "docker-compose" || check_command "docker" || missing=1
    check_command "curl" || missing=1
    check_command "jq" || log_warn "jq not found (optional, for JSON parsing)"
    
    if [ $missing -eq 1 ]; then
        log_error "Missing required dependencies. Please install them and try again."
        exit 1
    fi
    
    # Check Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
    
    log_success "All prerequisites met!"
}

# -----------------------------------------------------------------------------
# Start Services
# -----------------------------------------------------------------------------
start_services() {
    log_info "Starting local development environment..."
    
    cd "$ROOT_DIR"
    
    # Start infrastructure services first
    log_info "Starting infrastructure services (Pub/Sub, MinIO, PostgreSQL, Qdrant)..."
    docker-compose up -d pubsub-emulator minio postgres redis qdrant
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Initialize MinIO buckets
    log_info "Initializing MinIO buckets..."
    docker-compose up minio-init
    
    # Start monitoring tools
    log_info "Starting monitoring tools (Adminer)..."
    docker-compose up -d adminer
    
    log_success "Infrastructure services started!"
    
    # Print service URLs
    echo ""
    log_info "Service URLs:"
    echo "  - MinIO Console:    http://localhost:9001 (minioadmin/minioadmin)"
    echo "  - MinIO API:        http://localhost:9000"
    echo "  - PostgreSQL:       localhost:5432 (tsh-industries/localdevpassword)"
    echo "  - Adminer (DB UI):  http://localhost:8088"
    echo "  - Pub/Sub Emulator: localhost:8085"
    echo "  - Qdrant:           http://localhost:6333"
    echo "  - Redis:            localhost:6379"
    echo ""
    echo "  To list Pub/Sub topics:"
    echo "    curl http://localhost:8085/v1/projects/tsh-industries-local/topics"
}

# -----------------------------------------------------------------------------
# Start Application Services
# -----------------------------------------------------------------------------
start_app_services() {
    log_info "Building and starting application services..."
    
    cd "$ROOT_DIR"
    
    # Build all services
    docker-compose build detect-file-type document-processor chunking-service \
        embedding-service llm-tagging-service rag-query-service
    
    # Start services
    docker-compose up -d detect-file-type document-processor chunking-service \
        embedding-service llm-tagging-service rag-query-service
    
    log_success "Application services started!"
    
    echo ""
    log_info "Application Service URLs:"
    echo "  - Detect File Type:    http://localhost:8081"
    echo "  - Document Processor:  http://localhost:8082"
    echo "  - Chunking Service:    http://localhost:8083"
    echo "  - Embedding Service:   http://localhost:8084"
    echo "  - LLM Tagging:         http://localhost:8085"
    echo "  - RAG Query:           http://localhost:8086"
}

# -----------------------------------------------------------------------------
# Create Pub/Sub Topics and Subscriptions
# -----------------------------------------------------------------------------
setup_pubsub() {
    log_info "Setting up Pub/Sub topics and subscriptions..."
    
    PUBSUB_HOST="http://localhost:8085"
    
    # Topics
    topics=("data-ingestion" "document-processing" "chunking" "embedding" "llm-tagging" "dead-letter")
    
    for topic in "${topics[@]}"; do
        log_info "Creating topic: $topic"
        curl -s -X PUT "${PUBSUB_HOST}/v1/projects/${PROJECT_ID}/topics/${topic}" || true
    done
    
    # Subscriptions (using simple approach for shell compatibility)
    create_subscription() {
        local sub_name=$1
        local topic_name=$2
        log_info "Creating subscription: $sub_name -> $topic_name"
        curl -s -X PUT "${PUBSUB_HOST}/v1/projects/${PROJECT_ID}/subscriptions/${sub_name}" \
            -H "Content-Type: application/json" \
            -d "{\"topic\": \"projects/${PROJECT_ID}/topics/${topic_name}\"}" || true
    }
    
    create_subscription "data-ingestion-sub" "data-ingestion"
    create_subscription "document-processing-sub" "document-processing"
    create_subscription "chunking-sub" "chunking"
    create_subscription "embedding-sub" "embedding"
    create_subscription "llm-tagging-sub" "llm-tagging"
    create_subscription "dead-letter-sub" "dead-letter"
    
    log_success "Pub/Sub setup complete!"
}

# -----------------------------------------------------------------------------
# Initialize Database
# -----------------------------------------------------------------------------
init_database() {
    log_info "Initializing database schema..."
    
    # Wait for PostgreSQL to be ready
    until docker-compose exec -T postgres pg_isready -U tsh-industries -d tsh-industries_metadata; do
        log_info "Waiting for PostgreSQL..."
        sleep 2
    done
    
    # Run migrations if they exist
    if [ -f "$ROOT_DIR/scripts/init-db.sql" ]; then
        docker-compose exec -T postgres psql -U tsh-industries -d tsh-industries_metadata -f /docker-entrypoint-initdb.d/init.sql
        log_success "Database initialized!"
    else
        log_warn "No init-db.sql found, skipping database initialization"
    fi
}

# -----------------------------------------------------------------------------
# Test Pipeline
# -----------------------------------------------------------------------------
test_pipeline() {
    log_info "Testing the pipeline with a sample document..."
    
    # Create a test file
    echo "This is a test document for the TSH Industries GenAI pipeline." > /tmp/test-document.txt
    
    # Upload to MinIO
    log_info "Uploading test document to MinIO..."
    docker run --rm --network tsh-industries-network \
        -v /tmp/test-document.txt:/tmp/test-document.txt \
        minio/mc sh -c "
            mc alias set local http://minio:9000 minioadmin minioadmin && \
            mc cp /tmp/test-document.txt local/raw-documents/test-document.txt
        "
    
    log_success "Test document uploaded!"
    
    # Trigger the detect-file-type service
    log_info "Triggering detect-file-type service..."
    curl -X POST http://localhost:8081 \
        -H "Content-Type: application/json" \
        -d '{
            "message": {
                "data": "'$(echo -n '{"bucket":"raw-documents","name":"test-document.txt"}' | base64)'"
            }
        }'
    
    echo ""
    log_success "Pipeline test initiated! Check the logs with: docker-compose logs -f"
}

# -----------------------------------------------------------------------------
# Stop Services
# -----------------------------------------------------------------------------
stop_services() {
    log_info "Stopping all services..."
    cd "$ROOT_DIR"
    docker-compose down
    log_success "All services stopped!"
}

# -----------------------------------------------------------------------------
# Clean Up
# -----------------------------------------------------------------------------
cleanup() {
    log_info "Cleaning up all data and containers..."
    cd "$ROOT_DIR"
    docker-compose down -v --remove-orphans
    log_success "Cleanup complete!"
}

# -----------------------------------------------------------------------------
# Show Logs
# -----------------------------------------------------------------------------
show_logs() {
    cd "$ROOT_DIR"
    docker-compose logs -f "$@"
}

# -----------------------------------------------------------------------------
# Status
# -----------------------------------------------------------------------------
show_status() {
    log_info "Service Status:"
    cd "$ROOT_DIR"
    docker-compose ps
}

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
show_help() {
    echo "TSH Industries GenAI Pipeline - Local Development Setup"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  start       Start infrastructure services (Pub/Sub, MinIO, PostgreSQL, etc.)"
    echo "  start-all   Start all services including application services"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  status      Show status of all services"
    echo "  logs        Show logs (optionally specify service name)"
    echo "  test        Run a test through the pipeline"
    echo "  setup-pubsub Setup Pub/Sub topics and subscriptions"
    echo "  init-db     Initialize the database schema"
    echo "  cleanup     Stop services and remove all data"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start infrastructure"
    echo "  $0 start-all          # Start everything"
    echo "  $0 logs detect-file-type  # View logs for specific service"
    echo "  $0 test               # Run pipeline test"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    case "${1:-help}" in
        start)
            check_prerequisites
            start_services
            setup_pubsub
            ;;
        start-all)
            check_prerequisites
            start_services
            setup_pubsub
            init_database
            start_app_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            start_services
            ;;
        status)
            show_status
            ;;
        logs)
            shift
            show_logs "$@"
            ;;
        test)
            test_pipeline
            ;;
        setup-pubsub)
            setup_pubsub
            ;;
        init-db)
            init_database
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
