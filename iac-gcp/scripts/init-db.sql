-- =============================================================================
-- TSH Industries GenAI Pipeline - Database Initialization Script
-- =============================================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Documents Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_type VARCHAR(50),
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    bucket_name VARCHAR(255),
    
    -- Processing status
    status VARCHAR(50) DEFAULT 'pending',
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT documents_status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'retrying'))
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

-- =============================================================================
-- Document Chunks Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_size INTEGER,
    
    -- Chunk metadata
    start_page INTEGER,
    end_page INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    
    -- Embedding info
    embedding_id VARCHAR(255),
    embedding_model VARCHAR(100),
    embedded_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_id ON document_chunks(embedding_id);

-- =============================================================================
-- Document Tags Table (LLM-generated)
-- =============================================================================
CREATE TABLE IF NOT EXISTS document_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Tag information
    tag_name VARCHAR(255) NOT NULL,
    tag_value TEXT,
    tag_type VARCHAR(50),  -- 'category', 'entity', 'topic', 'sentiment', etc.
    confidence_score DECIMAL(5,4),
    
    -- LLM metadata
    llm_model VARCHAR(100),
    prompt_version VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tags_document_id ON document_tags(document_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag_name ON document_tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_tags_tag_type ON document_tags(tag_type);

-- =============================================================================
-- Processing Jobs Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Job info
    job_type VARCHAR(50) NOT NULL,  -- 'detect', 'process', 'chunk', 'embed', 'tag'
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    
    -- Execution details
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Error handling
    error_message TEXT,
    error_stack TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Workflow tracking
    workflow_execution_id VARCHAR(255),
    parent_job_id UUID REFERENCES processing_jobs(id),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT jobs_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_document_id ON processing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_workflow_id ON processing_jobs(workflow_execution_id);

-- =============================================================================
-- RAG Queries Table (for analytics)
-- =============================================================================
CREATE TABLE IF NOT EXISTS rag_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Query info
    query_text TEXT NOT NULL,
    query_embedding_id VARCHAR(255),
    
    -- Results
    result_count INTEGER,
    top_document_ids UUID[],
    response_text TEXT,
    
    -- Performance metrics
    embedding_latency_ms INTEGER,
    search_latency_ms INTEGER,
    llm_latency_ms INTEGER,
    total_latency_ms INTEGER,
    
    -- User context (optional)
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    
    -- Feedback
    feedback_rating INTEGER,
    feedback_text TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_queries_created_at ON rag_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON rag_queries(user_id);

-- =============================================================================
-- System Configuration Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Insert default configuration
INSERT INTO system_config (key, value, description) VALUES
    ('chunking', '{"chunk_size": 1000, "chunk_overlap": 200, "strategy": "recursive"}', 'Document chunking configuration'),
    ('embedding', '{"model": "text-embedding-004", "dimensions": 768, "batch_size": 100}', 'Embedding model configuration'),
    ('llm_tagging', '{"model": "gemini-1.5-flash", "temperature": 0.1, "max_tokens": 1024}', 'LLM tagging configuration'),
    ('rag', '{"top_k": 10, "similarity_threshold": 0.7, "rerank": true}', 'RAG query configuration')
ON CONFLICT (key) DO NOTHING;

-- =============================================================================
-- Audit Log Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID,
    action VARCHAR(20) NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_table_name ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_record_id ON audit_log(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON audit_log(changed_at);

-- =============================================================================
-- Update Trigger Function
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_jobs_updated_at
    BEFORE UPDATE ON processing_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Helpful Views
-- =============================================================================

-- Document processing summary
CREATE OR REPLACE VIEW v_document_summary AS
SELECT 
    d.id,
    d.file_name,
    d.file_type,
    d.status,
    d.created_at,
    COUNT(DISTINCT dc.id) as chunk_count,
    COUNT(DISTINCT dt.id) as tag_count,
    BOOL_OR(dc.embedding_id IS NOT NULL) as has_embeddings
FROM documents d
LEFT JOIN document_chunks dc ON d.id = dc.document_id
LEFT JOIN document_tags dt ON d.id = dt.document_id
GROUP BY d.id, d.file_name, d.file_type, d.status, d.created_at;

-- Processing statistics
CREATE OR REPLACE VIEW v_processing_stats AS
SELECT 
    job_type,
    status,
    COUNT(*) as count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    SUM(retry_count) as total_retries
FROM processing_jobs
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY job_type, status;

-- =============================================================================
-- Grant Permissions (for application user)
-- =============================================================================
-- In production, create a separate app user with limited permissions
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

COMMENT ON DATABASE tsh_industries_metadata IS 'TSH Industries GenAI Pipeline - Metadata Database';
