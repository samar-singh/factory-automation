# Human Interaction System Guide

## Overview

The Human Interaction System provides a human-in-the-loop workflow for handling orders with medium confidence (60-80%). This ensures quality control while maintaining automation efficiency.

## Architecture

### Components

1. **HumanInteractionManager** (`factory_agents/human_interaction_manager.py`)
   - Manages review requests and decisions
   - Tracks review status and metrics
   - Handles priority escalation

2. **OrchestratorWithHuman** (`factory_agents/orchestrator_with_human.py`)
   - Enhanced orchestrator with human tools
   - Monitors review completions
   - Processes human decisions

3. **HumanReviewInterface** (`factory_ui/human_review_interface.py`)
   - Gradio-based review dashboard
   - Queue management interface
   - Decision submission UI

## Confidence-Based Routing

The system automatically routes orders based on confidence scores:

- **>80% Confidence**: Auto-approved, processed immediately
- **60-80% Confidence**: Sent to human review queue
- **<60% Confidence**: Flagged for alternatives or clarification

## Review Workflow

### 1. Review Request Creation

When the orchestrator encounters a 60-80% confidence match:

```python
review = await human_manager.create_review_request(
    email_data=email_dict,
    search_results=search_results,
    confidence_score=confidence_score,
    extracted_items=items
)
```

### 2. Priority Assignment

Reviews are automatically prioritized based on:
- **URGENT**: Contains urgent keywords or very low confidence (<65%)
- **HIGH**: Low confidence (65-70%)
- **MEDIUM**: Moderate confidence (70-75%)
- **LOW**: Higher confidence (75-80%)

### 3. Human Review Process

Reviewers can:
- **Approve**: Order proceeds to processing
- **Reject**: Customer receives rejection notice
- **Clarify**: Request more information
- **Alternative**: Suggest alternative items

### 4. Decision Processing

The orchestrator automatically processes completed reviews:

```python
if review.status == "approved":
    # Generate quotation and process order
elif review.status == "rejected":
    # Send rejection email
elif review.status == "alternative_suggested":
    # Send alternatives to customer
```

## User Interface

### Launch Combined System

```bash
python launch_with_human_review.py
```

Access at: http://localhost:7860

### Interface Tabs

1. **AI Order Processing**: Main automated processing
2. **Human Review Dashboard**: Manual review interface
3. **System Status**: Monitoring and metrics

### Review Queue Features

- Filter by priority (Urgent/High/Medium/Low)
- View pending review statistics
- Open specific reviews
- Track review history

## API Integration

### Create Review via API

```python
from factory_automation.factory_agents.human_interaction_manager import HumanInteractionManager

manager = HumanInteractionManager()

# Register notification handler (optional)
async def notify(review):
    print(f"New review: {review.request_id}")
    
manager.register_notification_handler(notify)

# Create review
review = await manager.create_review_request(
    email_data={...},
    search_results=[...],
    confidence_score=70.0,
    extracted_items=[...]
)
```

### Submit Decision

```python
result = await manager.submit_review_decision(
    request_id="REV-20250103-0001",
    decision="approve",
    notes="Looks good, proceed with order"
)
```

### Get Statistics

```python
stats = manager.get_review_statistics()
print(f"Pending: {stats['total_pending']}")
print(f"Avg review time: {stats['average_review_time_seconds']}s")
```

## Testing

Run the test suite:

```bash
python test_human_interaction.py
```

This tests:
- Review creation and assignment
- Decision submission
- Priority escalation
- Statistics tracking
- Orchestrator integration

## Configuration

### Notification Handlers

Register custom notification handlers for Slack, email, etc.:

```python
async def slack_notifier(review):
    # Send to Slack
    pass

manager.register_notification_handler(slack_notifier)
```

### Custom Thresholds

Modify confidence thresholds in `orchestrator_with_human.py`:

```python
AUTO_APPROVE_THRESHOLD = 80
MANUAL_REVIEW_MIN = 60
MANUAL_REVIEW_MAX = 80
```

## Metrics & Monitoring

The system tracks:
- Total pending/completed reviews
- Average review time
- Status breakdown (approved/rejected/etc)
- Priority distribution
- Oldest pending review

Export data for analysis:

```python
data = manager.export_review_data()
# Contains all pending and completed reviews with metrics
```

## Best Practices

1. **Review Promptly**: High priority reviews should be addressed within 15 minutes
2. **Add Notes**: Always include decision rationale in notes
3. **Suggest Alternatives**: For low matches, provide 2-3 alternatives
4. **Monitor Queue**: Keep pending reviews under 10 for optimal flow
5. **Escalate When Needed**: Use escalation for time-sensitive orders

## Troubleshooting

### Common Issues

1. **Reviews not appearing**: Check orchestrator is running
2. **Can't submit decision**: Verify review ID is correct
3. **Statistics not updating**: Refresh the interface

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Email notifications for new reviews
- [ ] Slack/Teams integration
- [ ] Auto-assignment based on reviewer expertise
- [ ] ML-based confidence improvement
- [ ] Review time SLA tracking
- [ ] Customer preference learning