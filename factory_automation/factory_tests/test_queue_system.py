"""Test the recommendation queue system"""

import asyncio

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)
from factory_automation.factory_models.order_models import (
    OrderPriority,
    QueuedRecommendation,
    RecommendationType,
)


async def test_queue_operations():
    """Test basic queue operations"""

    print("\n=== Testing Recommendation Queue System ===\n")

    # Initialize manager
    manager = HumanInteractionManager()

    # 1. Create test recommendations
    print("1. Creating test recommendations...")

    test_recommendations = [
        QueuedRecommendation(
            order_id=None,  # Use NULL for testing without creating orders
            customer_email="customer1@example.com",
            recommendation_type=RecommendationType.EMAIL_RESPONSE,
            recommendation_data={
                "email_draft": {
                    "subject": "Re: Order for Allen Solly Tags",
                    "body": "Thank you for your order. Please find the proforma invoice attached.",
                },
                "inventory_matches": [
                    {"tag_code": "TBAL001", "name": "Main Tag", "quantity": 100}
                ],
            },
            confidence_score=0.85,
            priority=OrderPriority.HIGH,
        ),
        QueuedRecommendation(
            order_id=None,
            customer_email="customer2@example.com",
            recommendation_type=RecommendationType.DOCUMENT_GENERATION,
            recommendation_data={
                "document_type": "proforma_invoice",
                "items": [{"tag_code": "TBAL002", "quantity": 50, "price": 25}],
            },
            confidence_score=0.92,
            priority=OrderPriority.MEDIUM,
        ),
        QueuedRecommendation(
            order_id=None,
            customer_email="customer3@example.com",
            recommendation_type=RecommendationType.INVENTORY_UPDATE,
            recommendation_data={
                "updates": [
                    {
                        "tag_code": "TBAL003",
                        "field": "quantity",
                        "old_value": 200,
                        "new_value": 150,
                    }
                ],
            },
            confidence_score=0.45,
            priority=OrderPriority.URGENT,
        ),
    ]

    # Add to queue
    queue_ids = []
    for rec in test_recommendations:
        queue_id = manager.add_to_recommendation_queue(rec)
        queue_ids.append(queue_id)
        print(
            f"  Added: {queue_id} ({rec.recommendation_type.value}, Priority: {rec.priority.value})"
        )

    print(f"\n✅ Added {len(queue_ids)} recommendations to queue")

    # 2. Get pending recommendations
    print("\n2. Retrieving pending recommendations...")

    pending = manager.get_pending_recommendations(limit=10)
    print(f"  Found {len(pending)} pending recommendations:")

    for item in pending:
        print(
            f"  - {item['queue_id']}: {item['recommendation_type']} "
            f"(Priority: {item['priority']}, Confidence: {item['confidence_score']:.2f})"
        )

    # 3. Create a batch
    print("\n3. Creating batch from queue items...")

    if len(pending) >= 2:
        batch_queue_ids = [pending[0]["queue_id"], pending[1]["queue_id"]]
        batch_id = manager.create_batch_from_queue(
            queue_ids=batch_queue_ids, batch_name="Test Batch", batch_type="manual"
        )
        print(f"  Created batch: {batch_id} with {len(batch_queue_ids)} items")

        # 4. Get batch for review
        print("\n4. Getting batch for review...")

        batch = manager.get_batch_for_review(batch_id)
        if batch:
            print(f"  Batch: {batch['batch_id']}")
            print(f"  Name: {batch['batch_name']}")
            print(f"  Items: {batch['total_items']}")
            print(f"  Status: {batch['status']}")

            # 5. Approve batch items
            print("\n5. Approving batch items...")

            approved = [batch["items"][0]["queue_id"]] if batch["items"] else []
            rejected = (
                [batch["items"][1]["queue_id"]] if len(batch["items"]) > 1 else []
            )

            success = manager.approve_batch_items(
                batch_id=batch_id,
                approved_queue_ids=approved,
                rejected_queue_ids=rejected,
                modifications={"note": "Test approval"},
            )

            if success:
                print(
                    f"  ✅ Batch reviewed: {len(approved)} approved, {len(rejected)} rejected"
                )
            else:
                print("  ❌ Failed to approve batch items")

    # 6. Check queue metrics
    print("\n6. Checking queue metrics...")

    from sqlalchemy import text

    from factory_automation.factory_database.connection import engine

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM queue_metrics")).first()
        if result:
            print(f"  Pending: {result[0]}")
            print(f"  In Review: {result[1]}")
            print(f"  Approved: {result[2]}")
            print(f"  Executed: {result[3]}")
            print(f"  Urgent Priority: {result[4]}")
            print(
                f"  Average Confidence: {result[7]:.2f}"
                if result[7]
                else "  Average Confidence: N/A"
            )

    print("\n=== Queue System Test Complete ===\n")


if __name__ == "__main__":
    asyncio.run(test_queue_operations())
