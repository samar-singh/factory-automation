-- Migration: Add recommendation queue and batch processing tables
-- Date: 2025-01-13
-- Purpose: Support human review system with batch processing

-- Recommendation queue table
CREATE TABLE IF NOT EXISTS recommendation_queue (
    queue_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50),
    customer_email VARCHAR(255) NOT NULL,
    recommendation_type VARCHAR(50) NOT NULL, -- EMAIL, DOCUMENT, INVENTORY, DATABASE
    recommendation_data JSONB NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('urgent', 'high', 'medium', 'low')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_review', 'approved', 'rejected', 'executed', 'failed')),
    batch_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(255),
    executed_at TIMESTAMP,
    execution_result JSONB,
    error_message TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_number) ON DELETE SET NULL
);

-- Index for efficient queries
CREATE INDEX idx_recommendation_queue_status ON recommendation_queue(status);
CREATE INDEX idx_recommendation_queue_priority ON recommendation_queue(priority);
CREATE INDEX idx_recommendation_queue_customer ON recommendation_queue(customer_email);
CREATE INDEX idx_recommendation_queue_batch ON recommendation_queue(batch_id);
CREATE INDEX idx_recommendation_queue_created ON recommendation_queue(created_at DESC);

-- Batch processing table
CREATE TABLE IF NOT EXISTS batch_operations (
    batch_id VARCHAR(50) PRIMARY KEY,
    batch_name VARCHAR(255),
    batch_type VARCHAR(20) DEFAULT 'manual' CHECK (batch_type IN ('daily', 'manual', 'urgent', 'scheduled')),
    total_items INTEGER DEFAULT 0,
    approved_items TEXT[], -- Array of queue_ids
    rejected_items TEXT[], -- Array of queue_ids
    modified_items JSONB, -- Map of queue_id to modifications
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_review', 'processing', 'completed', 'failed', 'rolled_back')),
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(255),
    executed_at TIMESTAMP,
    executed_by VARCHAR(255),
    completed_at TIMESTAMP,
    execution_time_ms INTEGER,
    results JSONB,
    error_log TEXT[],
    rollback_available BOOLEAN DEFAULT TRUE,
    rollback_executed_at TIMESTAMP
);

-- Index for batch operations
CREATE INDEX idx_batch_operations_status ON batch_operations(status);
CREATE INDEX idx_batch_operations_type ON batch_operations(batch_type);
CREATE INDEX idx_batch_operations_created ON batch_operations(created_at DESC);

-- Document generation log
CREATE TABLE IF NOT EXISTS document_generation_log (
    document_id SERIAL PRIMARY KEY,
    queue_id VARCHAR(50),
    order_id VARCHAR(50),
    document_type VARCHAR(50) NOT NULL, -- proforma_invoice, quotation, order_confirmation
    document_number VARCHAR(50) UNIQUE,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    template_used VARCHAR(100),
    template_version VARCHAR(20),
    generated_at TIMESTAMP DEFAULT NOW(),
    generated_by VARCHAR(255),
    generation_time_ms INTEGER,
    sent_to_customer BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    customer_email VARCHAR(255),
    metadata JSONB,
    FOREIGN KEY (queue_id) REFERENCES recommendation_queue(queue_id) ON DELETE SET NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_number) ON DELETE SET NULL
);

-- Index for document log
CREATE INDEX idx_document_log_order ON document_generation_log(order_id);
CREATE INDEX idx_document_log_type ON document_generation_log(document_type);
CREATE INDEX idx_document_log_customer ON document_generation_log(customer_email);

-- Inventory change log (mirrors Excel change log)
CREATE TABLE IF NOT EXISTS inventory_change_log (
    change_id SERIAL PRIMARY KEY,
    queue_id VARCHAR(50),
    batch_id VARCHAR(50),
    order_id VARCHAR(50),
    tag_code VARCHAR(50) NOT NULL,
    field_changed VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_type VARCHAR(20) CHECK (change_type IN ('update', 'addition', 'deletion')),
    change_date TIMESTAMP DEFAULT NOW(),
    approved_by VARCHAR(255),
    excel_file VARCHAR(255),
    excel_sheet VARCHAR(100),
    excel_row INTEGER,
    excel_log_created BOOLEAN DEFAULT FALSE,
    excel_log_file VARCHAR(255),
    notes TEXT,
    FOREIGN KEY (queue_id) REFERENCES recommendation_queue(queue_id) ON DELETE SET NULL,
    FOREIGN KEY (batch_id) REFERENCES batch_operations(batch_id) ON DELETE SET NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_number) ON DELETE SET NULL
);

-- Index for change log
CREATE INDEX idx_inventory_change_tag ON inventory_change_log(tag_code);
CREATE INDEX idx_inventory_change_order ON inventory_change_log(order_id);
CREATE INDEX idx_inventory_change_batch ON inventory_change_log(batch_id);
CREATE INDEX idx_inventory_change_date ON inventory_change_log(change_date DESC);

-- Queue metrics view for dashboard
CREATE OR REPLACE VIEW queue_metrics AS
SELECT 
    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE status = 'in_review') as in_review_count,
    COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
    COUNT(*) FILTER (WHERE status = 'executed') as executed_count,
    COUNT(*) FILTER (WHERE priority = 'urgent') as urgent_count,
    COUNT(*) FILTER (WHERE priority = 'high') as high_count,
    AVG(CASE 
        WHEN reviewed_at IS NOT NULL AND created_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (reviewed_at - created_at))/60 
        ELSE NULL 
    END) as avg_review_time_minutes,
    AVG(confidence_score) as avg_confidence_score
FROM recommendation_queue
WHERE created_at > NOW() - INTERVAL '7 days';

-- Batch metrics view
CREATE OR REPLACE VIEW batch_metrics AS
SELECT 
    batch_type,
    COUNT(*) as batch_count,
    AVG(total_items) as avg_items_per_batch,
    AVG(CASE 
        WHEN array_length(approved_items, 1) IS NOT NULL 
        THEN array_length(approved_items, 1)::FLOAT / NULLIF(total_items, 0) * 100
        ELSE 0 
    END) as avg_approval_rate,
    AVG(execution_time_ms) as avg_execution_time_ms
FROM batch_operations
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY batch_type;

-- Add comments for documentation
COMMENT ON TABLE recommendation_queue IS 'Stores all AI orchestrator recommendations pending human review';
COMMENT ON TABLE batch_operations IS 'Groups recommendations into batches for efficient processing';
COMMENT ON TABLE document_generation_log IS 'Tracks all generated documents (invoices, quotations, etc.)';
COMMENT ON TABLE inventory_change_log IS 'Audit trail for all inventory modifications';

COMMENT ON COLUMN recommendation_queue.recommendation_type IS 'Type of recommendation: EMAIL, DOCUMENT, INVENTORY, DATABASE';
COMMENT ON COLUMN recommendation_queue.recommendation_data IS 'JSON data containing the full recommendation details';
COMMENT ON COLUMN batch_operations.modified_items IS 'JSON map of queue_id to user modifications before approval';