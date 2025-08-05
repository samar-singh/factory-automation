# Tools Cleanup Plan

## Current Tools Analysis

### 1. ❌ **analyze_email** - REMOVE
- **Purpose**: Basic pattern matching for email type
- **Why Remove**: `process_complete_order` does this better with AI
- **Status**: REDUNDANT

### 2. ❌ **extract_order_items** - REMOVE  
- **Purpose**: Extract order details with AI
- **Why Remove**: `process_complete_order` includes this functionality
- **Status**: REDUNDANT (keep logic but remove standalone tool)

### 3. ✅ **process_complete_order** - KEEP (PRIMARY)
- **Purpose**: Complete order processing workflow
- **Includes**: Email analysis + extraction + inventory search + routing
- **Status**: ESSENTIAL - This is the main tool

### 4. ✅ **process_tag_image** - KEEP
- **Purpose**: Analyze tag images with Qwen2.5VL
- **Status**: UNIQUE functionality for visual processing

### 5. ✅ **search_inventory** - KEEP
- **Purpose**: ChromaDB semantic search
- **Status**: USEFUL for standalone inventory queries

### 6. ❓ **search_visual** - REVIEW
- **Purpose**: Search using CLIP embeddings
- **Consider**: Merge with process_tag_image or remove if not used
- **Status**: POTENTIALLY REDUNDANT

### 7. ✅ **check_emails** - KEEP
- **Purpose**: Poll Gmail for new emails
- **Status**: ESSENTIAL for email monitoring

### 8. ❓ **get_customer_context** - REVIEW
- **Purpose**: Get customer history
- **Consider**: Could be part of process_complete_order
- **Status**: NICE TO HAVE but could be integrated

### 9. ❌ **make_decision** - REMOVE
- **Purpose**: Simple confidence-based routing
- **Why Remove**: `process_complete_order` handles this internally
- **Status**: REDUNDANT

### 10. ❓ **generate_document** - REVIEW
- **Purpose**: Generate quotes/confirmations
- **Status**: KEEP if document generation is needed

### 11. ❓ **update_order_status** - REVIEW
- **Purpose**: Update order in database
- **Consider**: Should be internal to process_complete_order
- **Status**: Could be internal function

## Recommended Tool Set (After Cleanup)

### Core Tools (4 only):
1. **check_emails** - Monitor inbox
2. **process_complete_order** - Main order processing (includes everything)
3. **process_tag_image** - Visual analysis of attachments
4. **search_inventory** - Quick inventory lookup

### Optional Tools (keep if needed):
5. **generate_document** - Create quotes/invoices
6. **get_customer_context** - Customer history lookup

## Benefits of Cleanup:
- Clearer AI decision making (fewer tools to choose from)
- No confusion about which tool to use
- Single source of truth for order processing
- Easier to maintain and debug