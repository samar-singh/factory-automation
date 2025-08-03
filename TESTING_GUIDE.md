# Complete System Testing Guide

## 🚀 Quick Start

```bash
# Activate environment and run the main test
source .venv/bin/activate
python test_complete_system.py
```

## 📋 What You Can Test

### 1. **Email Processing Flow** (End-to-End)
- Mock emails arrive → AI analyzes → Extracts order → Searches inventory → Makes decision → Generates response

### 2. **Available Mock Emails**
1. **Allen Solly** - Order for 500 black tags
2. **Myntra** - Urgent sustainable tags with Excel attachment
3. **H&M** - Payment confirmation with UTR
4. **Zara** - Sample request for leather tags
5. **Follow-up** - Previous order reference

### 3. **Test Scenarios**

#### A. Simple Order Test
```bash
python test_simple_agentic.py
```
- Tests basic order processing
- Shows AI decision-making
- Displays trace information

#### B. Full System Test
```bash
python test_agentic_orchestrator.py
```
Menu options:
1. **Test autonomous email processing** - Process mock emails
2. **Test individual tools** - Test each AI tool separately
3. **Test monitoring loop** - Continuous email checking
4. **Compare approaches** - See workflow vs agentic
5. **View trace results** - See AI action history
6. **Launch trace UI** - Visual monitoring dashboard

#### C. Gradio UI Test
```bash
python launch_ai_app.py
```
- Full web interface at http://localhost:7860
- Three tabs: Inventory Search, Order Processing, System Status
- Test with natural language queries

## 🔍 Testing Each Component

### 1. **Mock Email System**
```bash
python test_mock_email_system.py
```
- View all mock emails
- Add custom emails
- Test email parsing

### 2. **ChromaDB Search**
```bash
python test_system.py
```
- Test inventory search
- Check embedding accuracy
- Verify RAG functionality

### 3. **AI Orchestration**
```bash
# Already tested above, but for specific AI testing:
python test_with_mock_email.py
```

### 4. **Trace Monitoring**
- **OpenAI Platform**: https://platform.openai.com/traces
- **Local Dashboard**: Run test and select option 6
- **Export Traces**: Available in dashboard

## 📊 Expected Results

### Successful Email Processing:
```
✅ Email analyzed → Type: order, Urgent: true
✅ Items extracted → 500 black tags with silver thread  
✅ Inventory searched → Found: Black Woven Tag (85% match)
✅ Decision made → Auto-approved
✅ Action taken → Generate quotation
```

### AI Tool Sequence:
1. `analyze_email` - Understands intent
2. `extract_order_items` - Gets structured data
3. `search_inventory` - Finds matches in ChromaDB
4. `get_customer_context` - Checks history
5. `make_decision` - Approves/reviews
6. `generate_document` - Creates quotation

## 🧪 Advanced Testing

### 1. **Test Different Email Types**
```python
# In test console, modify email type:
test_email = {
    "subject": "Payment for Order #123",
    "body": "Payment sent. UTR: 1234567890",
    "from": "customer@example.com"
}
```

### 2. **Test Edge Cases**
- Ambiguous orders
- Multiple items
- No exact matches
- Urgent vs normal
- Missing information

### 3. **Performance Testing**
```bash
# Run monitoring for extended period
python test_agentic_orchestrator.py
# Select option 3 - runs 3 cycles
```

## 🔧 Troubleshooting

### Common Issues:

1. **"No module named 'agents'"**
   ```bash
   source .venv/bin/activate
   uv pip install openai-agents
   ```

2. **"OPENAI_API_KEY not found"**
   - Check `.env` file has the key
   - Run `source .venv/bin/activate`

3. **"No matches in inventory"**
   ```bash
   # Re-ingest inventory data
   python ingest_inventory.py
   ```

4. **Trace not appearing**
   - Wait 10-30 seconds
   - Check https://platform.openai.com/traces
   - Ensure API key has trace permissions

## 📈 Monitoring Results

### View Traces:
1. **OpenAI Platform**: Real-time AI decisions
2. **Local Dashboard**: Detailed tool usage
3. **Console Output**: Immediate feedback

### Metrics to Check:
- Tool call count
- Decision confidence
- Processing time
- Error rate

## 🎯 Testing Checklist

- [ ] Mock email processing works
- [ ] AI makes autonomous decisions
- [ ] Tools are called in correct sequence
- [ ] Inventory search returns results
- [ ] Decisions match confidence thresholds
- [ ] Traces appear in OpenAI platform
- [ ] Local trace monitoring works
- [ ] Gradio UI loads and responds
- [ ] Different email types handled correctly
- [ ] Error cases handled gracefully

## 💡 Next Steps

1. **Test with real Gmail** (when configured)
2. **Add more inventory data**
3. **Test Qwen2.5VL visual analysis**
4. **Deploy to production**

## 🆘 Quick Commands

```bash
# Main test
python test_complete_system.py

# Simple test
python test_simple_agentic.py

# Full menu
python test_agentic_orchestrator.py

# UI test
python launch_ai_app.py

# View traces
https://platform.openai.com/traces
```