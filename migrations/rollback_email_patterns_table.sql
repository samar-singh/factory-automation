-- Rollback Migration: Remove email_patterns table
-- Date: 2024-12-14
-- Description: Rollback script to remove email_patterns table if needed

-- Drop the indexes first
DROP INDEX IF EXISTS idx_sender_recipient_intent;

-- Drop the table
DROP TABLE IF EXISTS email_patterns;

-- Note: This will permanently delete all pattern learning data
-- Make sure to backup the data before running this rollback if needed