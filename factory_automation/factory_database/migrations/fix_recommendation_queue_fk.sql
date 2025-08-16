-- Fix the foreign key constraint to allow NULL values for testing
-- Date: 2025-01-13

-- Drop the existing foreign key constraint
ALTER TABLE recommendation_queue 
DROP CONSTRAINT IF EXISTS recommendation_queue_order_id_fkey;

-- Re-add the foreign key with ON DELETE SET NULL (allows NULL values)
ALTER TABLE recommendation_queue
ADD CONSTRAINT recommendation_queue_order_id_fkey 
FOREIGN KEY (order_id) 
REFERENCES orders(order_number) 
ON DELETE SET NULL;