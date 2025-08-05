# 🚀 How to Run Factory Automation System

## Prerequisites

1. **Python Environment**
   ```bash
   # Activate virtual environment
   source .venv/bin/activate
   ```

2. **Set API Keys**
   ```bash
   # Required for AI orchestrator
   export OPENAI_API_KEY="your-openai-api-key"
   
   # Optional: For visual analysis (when implemented)
   export TOGETHER_API_KEY="your-together-api-key"
   ```

3. **Verify Installation**
   ```bash
   # Check dependencies
   pip list | grep -E "openai|gradio|chromadb"
   ```

## 🎯 Quick Start Options

### Option 1: Full System (Recommended)
```bash
# Run the complete system with all features
python run_factory_automation.py
```
- Opens browser automatically at http://localhost:7860
- Starts orchestrator in background
- Enables all features

### Option 2: Test Mode
```bash
# Run tests to see the flow in action
python test_human_interaction.py
```
- Demonstrates complete workflow
- No UI needed
- Good for understanding the flow

### Option 3: Manual Components

#### Start Web Interface Only
```bash
python launch_with_human_review.py
```

#### Start Human Review Dashboard Only
```bash
python -m factory_automation.factory_ui.human_review_interface
```

## 📋 Workflow Examples

### Example 1: High Confidence Order (>80%)
```python
# This order will be auto-approved
"Need 500 Allen Solly black woven tags, size 2x1 inches"
→ Confidence: 85%
→ Auto-approved
→ Quotation generated immediately
```

### Example 2: Medium Confidence Order (60-80%)
```python
# This order needs human review
"Looking for eco-friendly tags similar to what we ordered last time"
→ Confidence: 72%
→ Sent to human review queue
→ Reviewer approves/suggests alternatives
→ Decision processed automatically
```

### Example 3: Low Confidence Order (<60%)
```python
# This order needs clarification
"Need some special holographic tags with embedded chips"
→ Confidence: 45%
→ System suggests alternatives
→ Requests clarification from customer
```

## 🖥️ Using the Web Interface

### Main Dashboard (http://localhost:7860)

1. **Order Processing Tab**
   - Enter order text in the input box
   - Click "Process Order"
   - View confidence score and routing decision

2. **Human Review Tab**
   - See pending reviews queue
   - Open review for details
   - Make decision (Approve/Reject/Alternative)
   - Submit with notes

3. **System Status Tab**
   - Monitor pending reviews
   - View completion statistics
   - Check system health

## 🧪 Testing Specific Scenarios

### Test Human Review Flow
```bash
# Creates orders with different confidence levels
python test_human_interaction.py
```

### Test with Mock Gmail
```bash
# Simulates email arrival and processing
python test_agentic_orchestrator.py
```

### Debug Mode
```bash
# Run with detailed logging
python debug_human_interaction.py
```

## 📊 Monitoring the System

### View Logs
```bash
# Real-time logs
tail -f factory_automation.log

# Filter for errors
grep ERROR factory_automation.log

# Watch human review activity
grep "review request" factory_automation.log
```

### Check Database
```bash
# View ChromaDB contents
python -c "from factory_automation.factory_database.vector_db import ChromaDBClient; db = ChromaDBClient(); print(f'Items in DB: {db.collection.count()}')"
```

### Review Metrics
```python
from factory_automation.factory_agents.human_interaction_manager import HumanInteractionManager

manager = HumanInteractionManager()
stats = manager.get_review_statistics()
print(f"Pending: {stats['total_pending']}")
print(f"Completed: {stats['total_completed']}")
print(f"Avg review time: {stats['average_review_time_seconds']}s")
```

## 🔄 Complete Flow Walkthrough

1. **Email Arrives**
   ```
   Customer sends: "Need 500 black tags with logo"
   ```

2. **AI Processing**
   ```
   - Extracts: quantity=500, type=black tags, logo=yes
   - Searches inventory: finds "Black Woven Tag" at 75% match
   ```

3. **Confidence Routing**
   ```
   75% confidence → Human Review Queue
   ```

4. **Human Review**
   ```
   - Reviewer sees order details
   - Checks inventory matches
   - Approves with note: "Standard black tags suitable"
   ```

5. **Automated Action**
   ```
   - Orchestrator detects approval
   - Generates quotation
   - Sends to customer
   - Updates order status
   ```

## 🛠️ Troubleshooting

### Issue: "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-..."
```

### Issue: "Port 7860 already in use"
```bash
# Kill existing process
lsof -i:7860 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Or use different port
python launch_with_human_review.py --port 7861
```

### Issue: "No module named 'agents'"
```bash
pip install openai-agents-sdk
```

### Issue: "ChromaDB connection error"
```bash
# Reset database
rm -rf chroma_data/
python -c "from factory_automation.factory_database.vector_db import ChromaDBClient; ChromaDBClient()"
```

## 📝 Configuration

### Adjust Confidence Thresholds
Edit `factory_automation/factory_agents/orchestrator_with_human.py`:
```python
AUTO_APPROVE_THRESHOLD = 80  # Change to 85 for stricter
MANUAL_REVIEW_MIN = 60      # Change to 70 for fewer reviews
```

### Change Email Poll Interval
Edit `factory_automation/factory_config/settings.py`:
```python
email_poll_interval = 30  # Check every 30 seconds instead of 60
```

## 🎮 Interactive Demo Mode

For a quick demo without real emails:
```bash
# Start in demo mode
python run_factory_automation.py

# In the web interface:
1. Go to "Order Processing" tab
2. Enter: "Need 1000 Allen Solly tags, black color, 2x1 inch"
3. Click "Process Order"
4. Watch the confidence score and routing decision
5. If sent to review, switch to "Human Review" tab
6. Open the review and make a decision
```

## 📈 Production Deployment

For production use:
```bash
# Use environment file
cp .env.example .env
# Edit .env with production values

# Run with production settings
export ENVIRONMENT=production
python run_factory_automation.py

# Or use Docker (when available)
docker-compose up
```

## 🔗 Quick Links

- Main App: http://localhost:7860
- API Docs: http://localhost:7860/docs (if enabled)
- Logs: `./factory_automation.log`
- Database: `./chroma_data/`
- Config: `./factory_automation/factory_config/`

## 💡 Tips

1. **Start with test mode** to understand the flow
2. **Use high confidence examples** first (>80%)
3. **Try medium confidence** (60-80%) to see human review
4. **Monitor logs** for debugging
5. **Check System Status tab** regularly

## Need Help?

- Run tests: `python test_human_interaction.py`
- Check logs: `tail -f factory_automation.log`
- Debug mode: `python debug_human_interaction.py`
- View this guide: `cat HOW_TO_RUN.md`