# Migration Guide: Orchestrator V1 to V2

## Overview

This guide helps you migrate from the traditional orchestrator (v1) to the AI-powered orchestrator (v2) using a phased approach.

## Phase 1: Testing & Validation (Weeks 1-2)

### 1. Enable Comparison Logging

Add to your `.env` file:

```bash
ENABLE_COMPARISON_LOGGING=true
USE_AI_ORCHESTRATOR=false  # Start with v1
```

### 2. Process Test Emails

Run a variety of emails through v1:

- Simple order requests
- Complex orders with special instructions
- Payment confirmations
- Order modifications
- Follow-up queries

### 3. Switch to V2 and Repeat

```bash
USE_AI_ORCHESTRATOR=true  # Switch to v2
```

Process the same emails again.

### 4. Generate Comparison Report

```python
from utils.comparison_logger import comparison_logger

report = comparison_logger.generate_comparison_report()
print(report)
```

## Phase 2: Gradual Migration

### 1. Route by Complexity

Create a hybrid router that uses email characteristics:

```python
def should_use_v2(email_data):
    """Determine if email should use v2 based on complexity."""
    # Use v2 for complex cases
    if any([
        "urgent" in email_data.get("subject", "").lower(),
        "modify" in email_data.get("body", "").lower(),
        "special" in email_data.get("body", "").lower(),
        len(email_data.get("attachments", [])) > 2
    ]):
        return True
    return False
```

### 2. Monitor Performance

Check the comparison logs regularly:

```bash
# View summary
cat orchestrator_comparison_logs/comparison_summary.csv

# Check specific email processing
ls orchestrator_comparison_logs/*.json
```

### 3. Cost Monitoring

V2 uses GPT-4 which costs more. Monitor your usage:

- V1: ~$0.001 per email (GPT-3.5 for sub-agents)
- V2: ~$0.01-0.05 per email (GPT-4 for orchestration)

## Phase 3: Full Migration

### 1. Update Configuration

Once satisfied with v2 performance:

```bash
USE_AI_ORCHESTRATOR=true
ENABLE_COMPARISON_LOGGING=false  # Disable logging
```

### 2. Remove V1 Code

```bash
# Backup first
cp factory_automation/agents/orchestrator.py factory_automation/agents/orchestrator_v1_backup.py

# Replace with v2
mv factory_automation/agents/orchestrator_v2.py factory_automation/agents/orchestrator.py

# Update imports in main.py
# Remove the conditional import logic
```

### 3. Update Documentation

- Update CLAUDE.md to reflect v2 as the primary orchestrator
- Update API documentation
- Train team on new capabilities

## Benefits of V2

1. **Context Awareness**: Understands email threads and customer history
2. **Flexible Routing**: No hardcoded if-else chains
3. **Natural Language**: Handles "urgent order with 10% discount"
4. **Error Recovery**: Better at handling ambiguous requests
5. **Learning**: Improves with more context

## Rollback Plan

If issues arise with v2:

1. Set `USE_AI_ORCHESTRATOR=false`
2. Restart the application
3. Investigate issues in comparison logs
4. Adjust v2 instructions if needed

## Key Differences

| Feature | V1 (Traditional) | V2 (AI-Powered) |
|---------|------------------|-----------------|
| Decision Making | Rule-based | Context-aware |
| Flexibility | Limited | Highly flexible |
| Cost | Low | Higher |
| Speed | Fast | Slightly slower |
| Complexity Handling | Basic | Advanced |
| Maintenance | Code changes needed | Instruction updates |

## Monitoring Commands

```bash
# Check which version is running
grep "orchestrator" logs/app.log | tail -20

# Compare success rates
python -c "from utils.comparison_logger import comparison_logger; print(comparison_logger.generate_comparison_report())"

# View cost analysis
grep "api_cost" orchestrator_comparison_logs/comparison_summary.csv | awk -F',' '{sum+=$5} END {print "Total cost: $"sum}'
```

## Support

For issues during migration:

1. Check comparison logs for specific failures
2. Review orchestrator instructions in orchestrator_v2.py
3. Adjust prompts based on failure patterns
4. Consider hybrid approach for specific email types
