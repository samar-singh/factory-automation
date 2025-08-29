-- Migration: Add action_audit table for two-tier action system
-- Date: 2025-01-23
-- Plan: PLAN-2025-01-TWOTIER Phase 1

-- Create action_audit table
CREATE TABLE IF NOT EXISTS action_audit (
    id SERIAL PRIMARY KEY,
    action_id VARCHAR(100) UNIQUE NOT NULL,
    workflow_id VARCHAR(100) NOT NULL,
    order_id VARCHAR(50) REFERENCES orders(order_number),
    
    -- Action classification
    action_type VARCHAR(50) NOT NULL,  -- 'reversible' or 'irreversible'
    action_category VARCHAR(50) NOT NULL,  -- 'email_send', 'db_update', etc.
    action_name VARCHAR(100) NOT NULL,
    
    -- Action details
    description TEXT,
    details JSONB,
    
    -- Rollback capability
    can_rollback INTEGER DEFAULT 0,  -- Boolean: 0=False, 1=True
    rollback_data JSONB,
    rolled_back INTEGER DEFAULT 0,
    rolled_back_at TIMESTAMP,
    
    -- Execution tracking
    executed INTEGER DEFAULT 0,
    executed_at TIMESTAMP,
    execution_result JSONB,
    
    -- Approval tracking
    requires_approval INTEGER DEFAULT 0,
    approved INTEGER,  -- NULL=pending, 1=approved, 0=rejected
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    
    -- Metadata
    confidence FLOAT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_action_audit_workflow_id ON action_audit(workflow_id);
CREATE INDEX IF NOT EXISTS idx_action_audit_order_id ON action_audit(order_id);
CREATE INDEX IF NOT EXISTS idx_action_audit_action_type ON action_audit(action_type);
CREATE INDEX IF NOT EXISTS idx_action_audit_executed ON action_audit(executed);
CREATE INDEX IF NOT EXISTS idx_action_audit_requires_approval ON action_audit(requires_approval);
CREATE INDEX IF NOT EXISTS idx_action_audit_created_at ON action_audit(created_at);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_action_audit_updated_at 
    BEFORE UPDATE ON action_audit 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add comment on table
COMMENT ON TABLE action_audit IS 'Audit trail for all orchestrator actions with rollback capability for reversible actions';

-- Add comments on key columns
COMMENT ON COLUMN action_audit.action_type IS 'reversible: can be rolled back, irreversible: requires approval and cannot be undone';
COMMENT ON COLUMN action_audit.action_category IS 'Type of action: email_send, db_update, inventory_check, api_call, etc.';
COMMENT ON COLUMN action_audit.requires_approval IS '1 for irreversible actions that need human approval';
COMMENT ON COLUMN action_audit.can_rollback IS '1 for reversible actions that can be undone';

-- Verification query (run to check table was created)
-- SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'action_audit';