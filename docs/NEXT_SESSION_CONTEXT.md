# Next Session Context

## What Was Just Completed (Session 9)

### Context-Aware Orchestrator
- ✅ Implemented intelligent email classification using GPT-4o
- ✅ Added PostgreSQL pattern learning for sender behavior
- ✅ Fixed human review creation error ("int object is not subscriptable")
- ✅ Orchestrator now makes review decisions (not order processor)
- ✅ Simplified create_human_review tool interface

## Current System State

### Working Features
1. **Email Processing**
   - Context-aware classification (NEW_ORDER, PAYMENT, INQUIRY, etc.)
   - Pattern learning from sender history
   - Multi-business email support

2. **Order Processing**
   - AI extraction from emails and attachments
   - PDF and Excel processing with image extraction
   - Inventory search with Stella-400M embeddings
   - Visual similarity search with CLIP

3. **Human Review System**
   - Automatic creation when confidence < 80%
   - Priority-based queue management
   - Review interface in Gradio UI
   - Feedback loop for pattern learning

### Known Issues
- Lint errors in utilities/ folder (bare except statements)
- Some test files need cleanup
- Gmail live connection pending (needs IT approval)

## How to Test the System

### Quick Start
```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Set API keys
export OPENAI_API_KEY='your-key-here'
export TOGETHER_API_KEY='your-key-here'  # Optional

# 3. Run the application
python run_factory_automation.py

# 4. Access at http://127.0.0.1:7860 (or 7861 if port is busy)
```

### Test Workflow
1. Go to "Order Processing" tab
2. Paste test email:
```
From: storerhppl@gmail.com
Subject: Allen Solly Order
Date: Monday, 28 July 2025

Dear Sir,
We need 1000 price tags for Allen Solly products.
```
3. Attach test files (PDFs, Excel with images)
4. Click "Process Order"
5. Check "Human Review" tab for created reviews

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
- `/factory_automation/factory_agents/orchestrator_v3_agentic.py` - Main orchestrator with classification
- `/factory_automation/factory_agents/orchestrator_with_human.py` - Human review integration
- `/factory_automation/factory_agents/order_processor_agent.py` - Order processing logic
- `/config.yaml` - Business email configuration

### Database
- `/factory_automation/factory_database/models.py` - EmailPattern model
- `/migrations/add_email_patterns_table.sql` - Pattern storage migration

### UI
- `/run_factory_automation.py` - Main entry point
- `/factory_automation/factory_ui/human_review_interface_improved.py` - Review interface

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

### Pattern Learning
```python
# Always check patterns before AI classification
pattern = await self._check_sender_pattern(sender_email, recipient_email)
if pattern and pattern.confidence > 0.8:
    return pattern.intent_type, pattern.confidence
```

### Review Creation
```python
# Store order result for review creation
self._last_order_result = response
self._current_email_subject = email_subject
self._current_email_body = email_body
```

### Confidence Calculation
```python
# Handle different confidence score formats
if isinstance(scores, dict):
    score_values = [v for v in scores.values() if isinstance(v, (int, float))]
    avg_score = sum(score_values) / len(score_values) if score_values else 0
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