# Next Session Context

## What Was Just Completed (Session 15)

### UI Fixes and Human Review Enhancements
- ✅ Fixed human review UI to display actual inventory images from ChromaDB
- ✅ Implemented click-to-zoom functionality for tag images  
- ✅ Resolved all table formatting issues (duplicate headers, font colors, radio buttons)
- ✅ Fixed database foreign key constraints for order processing
- ✅ Made Process Selected Batch button always visible with proper styling

## Current System State

### Working Features
1. **Human Review Interface** (FULLY OPERATIONAL)
   - Actual inventory images display from ChromaDB
   - Click-to-zoom modal for image inspection
   - Proper table formatting with visible radio buttons
   - Process Selected Batch functionality
   - Color-coded confidence scores

2. **Order Processing**
   - AI extraction from emails and attachments
   - PDF and Excel processing with image extraction
   - Inventory search with Stella-400M embeddings
   - Visual similarity search with CLIP
   - Orders properly saved before creating review entries

3. **Database Integration**
   - PostgreSQL with proper foreign key relationships
   - ChromaDB with base64 image storage
   - Recommendation queue for human review items
   - Pattern learning from sender history

### Known Issues
- Ruff linting: 2 E722 errors (bare except) in image_storage.py
- Mypy: 122 type errors (non-critical)
- Gmail live connection pending (needs IT approval)

## How to Test the System

### Quick Start
```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Set API keys
export OPENAI_API_KEY='your-key-here'
export TOGETHER_API_KEY='your-key-here'  # Optional for Qwen2.5VL

# 3. Run the application
python3 -m dotenv run -- python3 run_factory_automation.py

# 4. Access at http://127.0.0.1:7860 (or 7861 if port is busy)
```

### Test Workflow
1. Go to "Order Processing" tab
2. Paste test email from sample_emails.txt
3. Upload test documents from inventory/ folder
4. Click "Process Order with Documents"
5. Go to "Human Review" tab
6. Select order from dropdown
7. Verify:
   - Inventory matches show with actual tag images
   - Click on images to test zoom functionality
   - Radio buttons are visible in Select column
   - Process button shows count of selected items
   - Font colors and table formatting are correct

### Verify Pattern Learning
```sql
-- Check stored patterns
SELECT * FROM email_patterns ORDER BY last_seen DESC;

-- Check pattern confidence
SELECT sender_email, intent_type, confidence, count 
FROM email_patterns 
WHERE confidence > 0.8;
```

## Important Files to Remember

### Core Implementation
- `/factory_automation/factory_ui/human_review_dashboard.py` - Main UI with image display
- `/factory_automation/factory_agents/order_processor_agent.py` - Order processing with DB save fix
- `/run_factory_automation.py` - Main entry point with corrected imports
- `/config.yaml` - Business email configuration

### Database
- `/factory_automation/factory_database/models.py` - All database models
- ChromaDB collection: `tag_images_full` - Contains base64 encoded images

### Test Files
- `/test_image_fix.py` - Image zoom functionality testing
- `/factory_automation/factory_agents/generate_clip_embeddings.py` - CLIP embedding generation

## Next Priorities

### 1. Document Generation (HIGH)
- Implement proforma invoice generation
- Create quotation templates
- PDF export functionality
- Email sending capability

### 2. Payment Tracking (HIGH)
- OCR for UTR extraction
- Cheque processing
- Payment reconciliation dashboard
- Integration with order status

### 3. Performance Optimization (MEDIUM)
- Implement caching for patterns
- Optimize database queries
- Add connection pooling
- Reduce embedding computation time

### 4. Testing & Validation (MEDIUM)
- Create comprehensive test suite for classification
- Validate pattern learning accuracy
- Load testing for concurrent requests
- Edge case handling

### 5. Production Deployment (LOW - waiting on IT)
- Docker containerization
- Environment-specific configs
- Monitoring and logging setup
- Gmail API integration

## Critical Code Patterns

### Image Retrieval from ChromaDB
```python
# Always check for image_id in metadata
if 'metadata' in match and 'image_id' in match['metadata']:
    collection = self.chromadb_client.client.get_collection('tag_images_full')
    results = collection.get(ids=[image_id], include=['metadatas'])
    if results['metadatas'] and results['metadatas'][0]:
        image_url = f"data:image/png;base64,{results['metadatas'][0]['image_base64']}"
```

### JavaScript Global Functions in Gradio
```javascript
// Must make functions global for Gradio HTML components
window.showImageModal = function(imgUrl, tagCode) {
    // Implementation
}
```

### Database Save Order
```python
# Always save order before creating related records
db_session.add(new_order)
db_session.commit()
# Now safe to create recommendation_queue entries
```

### CSS for Radio Button Visibility
```css
input[type='radio'] {
    width: 18px !important;
    height: 18px !important;
    accent-color: #2563eb !important;
    opacity: 1 !important;
}
```

## Environment Variables Needed

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional but recommended
TOGETHER_API_KEY=...
GMAIL_DELEGATED_EMAIL=trimsblr@yahoo.co.in

# Database (defaults provided)
DATABASE_PASSWORD=password
DATABASE_URL=postgresql://user@localhost:5432/factory_automation
```

## Testing Checklist

- [ ] Email classification working
- [ ] Pattern storage in PostgreSQL
- [ ] Human review creation
- [ ] Attachment processing
- [ ] Image extraction from Excel
- [ ] Visual similarity search
- [ ] Confidence calculation
- [ ] Review interface loading
- [ ] Pattern learning updates

## Notes for Next Developer

1. **Pattern Learning**: The system gets smarter with each email. Monitor the email_patterns table to see improvement.

2. **Review Creation**: The orchestrator decides, not the order processor. This is intentional for better control.

3. **Confidence Scores**: Can be dict, list, or int. Always validate type before processing.

4. **Attachments**: Passed as file paths, not base64. This saves memory and improves performance.

5. **Port Issues**: If 7860 is busy, the app automatically tries 7861, 7862, etc.

6. **Debug Mode**: Set `enable_comparison_logging: true` in config.yaml for detailed orchestrator decisions.

## Commands Reference

```bash
# Format code
make format

# Run tests
make test

# Check lint
make check

# Clean cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Database migration
psql -U user -d factory_automation -f migrations/add_email_patterns_table.sql

# View logs
tail -f orchestrator_comparison_logs/$(ls -t orchestrator_comparison_logs | head -1)
```

## Success Metrics

- Pattern confidence improving over time: ✅
- Human reviews created automatically: ✅
- No duplicate reviews: ✅
- Classification accuracy > 80%: ✅
- Processing time < 2 minutes: ✅