# Review Decision Storage Guide

## Current Storage Locations

### 1. **In-Memory Storage** (Active)
Review decisions are currently stored in memory within the `HumanInteractionManager`:

```python
self.completed_reviews: Dict[str, ReviewRequest] = {}
```

**Pros:**
- Fast access
- Full review details preserved
- Easy to query

**Cons:**
- ❌ Lost when system restarts
- ❌ Not shared between instances
- ❌ No permanent record

### 2. **Database Tables** (Available but not used)
PostgreSQL tables exist but aren't connected to the review system:

- **approval_queue** table - Could store review decisions
- **orders** table - Stores order status
- **email_logs** table - Could track review communications

### 3. **Export Functionality** (Manual)
The UI provides export to JSON:
- Go to "Review History" tab
- Click "📥 Export Data"
- Saves to `/tmp/review_data_YYYYMMDD_HHMMSS.json`

## What Gets Saved

Each review decision contains:
```python
{
    "request_id": "REV-20250805-224316-0001",
    "customer_email": "customer@example.com",
    "subject": "Order Subject",
    "confidence_score": 0.75,
    "decision": "approve",  # or reject/clarify/alternative/defer
    "review_notes": "Looks good to process",
    "reviewed_at": "2025-08-05 22:45:00",
    "status": "approved",
    "alternative_items": []  # If alternatives suggested
}
```

## How to Make Storage Permanent

### Option 1: Add Database Persistence (Recommended)
```python
# In submit_review_decision method:
# Save to database
approval = ApprovalQueue(
    order_id=review.order_id,
    approval_type="human_review",
    details={
        "review_id": request_id,
        "confidence": review.confidence_score,
        "items": review.items,
        "decision": decision,
        "notes": notes
    },
    status=decision,
    approved_by="human_reviewer",
    approved_at=datetime.now()
)
session.add(approval)
session.commit()
```

### Option 2: Auto-Export to Files
```python
# After each decision
import json
from pathlib import Path

reviews_dir = Path("review_history")
reviews_dir.mkdir(exist_ok=True)

with open(reviews_dir / f"{request_id}.json", "w") as f:
    json.dump(review.dict(), f, indent=2, default=str)
```

### Option 3: Add to Order Status
Update the Order record with review decision:
```python
order.status = "approved" if decision == "approve" else "rejected"
order.review_notes = notes
order.reviewed_at = datetime.now()
```

## Current Workarounds

### 1. Manual Export
Periodically export review history from UI

### 2. Log Mining
Review decisions are logged:
```bash
grep "completed with decision" debug_session.log
```

### 3. Session Persistence
Keep the system running to maintain history

## Future Implementation

To properly save review decisions:

1. **Add ReviewDecision model** to database
2. **Update submit_review_decision** to save to DB
3. **Add review_history endpoint** to query past decisions
4. **Create audit trail** for compliance

Would you like me to implement permanent storage for review decisions?