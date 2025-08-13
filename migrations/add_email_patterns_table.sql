-- Migration: Add email_patterns table for intelligent email routing
-- Date: 2024-12-14
-- Description: Stores sender patterns for learning-based email classification

-- Create the email_patterns table
CREATE TABLE IF NOT EXISTS email_patterns (
    id SERIAL PRIMARY KEY,
    sender_email VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_description TEXT,
    intent_type VARCHAR(50) NOT NULL,
    count INTEGER DEFAULT 1,
    confidence FLOAT DEFAULT 0.5,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional learning fields
    subject_keywords TEXT, -- JSON string of common keywords
    avg_response_time FLOAT,
    auto_approved_count INTEGER DEFAULT 0,
    manual_review_count INTEGER DEFAULT 0
);

-- Create indexes for efficient querying
CREATE INDEX idx_sender_recipient_intent 
ON email_patterns(sender_email, recipient_email, intent_type);

-- Create unique constraint to prevent duplicates
ALTER TABLE email_patterns 
ADD CONSTRAINT uq_sender_recipient_intent 
UNIQUE (sender_email, recipient_email, intent_type);

-- Add comments for documentation
COMMENT ON TABLE email_patterns IS 'Stores email sender patterns for intelligent routing and classification';
COMMENT ON COLUMN email_patterns.sender_email IS 'Email address of the sender';
COMMENT ON COLUMN email_patterns.recipient_email IS 'Business email address that received the email';
COMMENT ON COLUMN email_patterns.recipient_description IS 'Description/purpose of the recipient email address';
COMMENT ON COLUMN email_patterns.intent_type IS 'Classification of email intent (NEW_ORDER, PAYMENT, INQUIRY, etc.)';
COMMENT ON COLUMN email_patterns.count IS 'Number of times this pattern has been observed';
COMMENT ON COLUMN email_patterns.confidence IS 'Confidence score for this pattern (0.0 to 1.0)';
COMMENT ON COLUMN email_patterns.subject_keywords IS 'JSON array of common keywords from email subjects';
COMMENT ON COLUMN email_patterns.avg_response_time IS 'Average response time for this type of email';
COMMENT ON COLUMN email_patterns.auto_approved_count IS 'Number of times auto-approved based on this pattern';
COMMENT ON COLUMN email_patterns.manual_review_count IS 'Number of times required manual review';