#!/usr/bin/env python3
"""Create a test review for debugging row selection"""

import asyncio
import uuid
from datetime import datetime

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
    Priority,
    ReviewRequest,
    ReviewStatus,
)


async def create_test_review():
    """Create a test review directly"""
    print("🧪 Creating Test Review for Row Selection\n")

    # Use the shared manager instance
    manager = HumanInteractionManager()

    # Create a test review
    test_review = ReviewRequest(
        request_id=f"REV-TEST-{datetime.now().strftime('%H%M%S')}",
        email_id=f"email-{uuid.uuid4().hex[:8]}",
        customer_email="rowtest@example.com",
        subject="Test Review for Row Selection",
        items=[
            {
                "item_id": "ITEM-001",
                "tag_code": "TEST123",
                "quantity": 100,
                "tag_type": "test",
            }
        ],
        search_results=[
            {
                "name": "Test Tag",
                "code": "TEST123",
                "brand": "Test Brand",
                "similarity_score": 0.45,
                "price": 10,
                "stock": 1000,
            }
        ],
        confidence_score=0.45,  # Low confidence to ensure human review
        priority=Priority.MEDIUM,
        status=ReviewStatus.PENDING,
        created_at=datetime.now(),
        order_id=f"ORD-TEST-{datetime.now().strftime('%H%M%S')}",
    )

    # Add directly to pending reviews
    manager.pending_reviews[test_review.request_id] = test_review

    print(f"✅ Created test review: {test_review.request_id}")
    print(f"Customer: {test_review.customer_email}")
    print(f"Confidence: {test_review.confidence_score:.1%}")

    # Verify it's in the queue
    reviews = await manager.get_pending_reviews()
    print(f"\n📋 Total reviews in queue: {len(reviews)}")

    if reviews:
        print("\nNow you can:")
        print("1. Go to http://127.0.0.1:7860")
        print("2. Navigate to Human Review tab")
        print("3. Click 'Refresh Queue'")
        print("4. Click on the test review row")
        print("5. The 'Selected Review' field should update")
        print("6. Click 'Open Selected Review' to view details")


if __name__ == "__main__":
    asyncio.run(create_test_review())
