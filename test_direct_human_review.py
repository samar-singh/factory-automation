"""Direct test of human review creation"""

import asyncio
import json

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)


async def test_direct_human_review():
    # Create human interaction manager
    human_manager = HumanInteractionManager()

    # Create a review request directly
    print("=== CREATING HUMAN REVIEW REQUEST DIRECTLY ===")

    email_data = {
        "message_id": "test-001",
        "from": "interface.scs02@gmail.com",
        "subject": "ORDER FOR FIT TAG 31570 QTY",
    }

    search_results = [
        {
            "tag_code": "TBPRTAG0082N",
            "description": "PETER ENGLAND SPORT COLLECTION TAG",
            "similarity_score": 0.75,  # 75% match - should trigger human review
            "brand": "Peter England",
        },
        {
            "tag_code": "TBPCTAG0532N",
            "description": "PEC reversible Hang tag-Navy",
            "similarity_score": 0.65,  # 65% match - should trigger human review
            "brand": "Peter England",
        },
    ]

    extracted_items = [
        {
            "item_id": "ITEM-001",
            "tag_code": "TBPRTAG0082N",
            "quantity": 31570,
            "tag_type": "fit_tag",
        },
        {
            "item_id": "ITEM-002",
            "tag_code": "TBPCTAG0532N",
            "quantity": 8750,
            "tag_type": "reversible_tag",
        },
    ]

    # Create the review
    review = await human_manager.create_review_request(
        email_data=email_data,
        search_results=search_results,
        confidence_score=0.70,  # 70% average confidence
        extracted_items=extracted_items,
    )

    print("\nReview Created:")
    print(f"- ID: {review.request_id}")
    print(f"- Customer: {review.customer_email}")
    print(f"- Confidence: {review.confidence_score:.2%}")
    print(f"- Priority: {review.priority.value}")
    print(f"- Status: {review.status.value}")

    # Check pending reviews
    print("\n=== CHECKING PENDING REVIEWS ===")
    pending = await human_manager.get_pending_reviews()
    print(f"Total pending reviews: {len(pending)}")

    for r in pending:
        print(f"\nReview {r.request_id}:")
        print(f"  Customer: {r.customer_email}")
        print(f"  Confidence: {r.confidence_score:.2%}")
        print(f"  Items: {len(r.items)}")
        print(f"  Search Results: {len(r.search_results)}")

    # Test the review queue
    print("\n=== TESTING REVIEW QUEUE ===")
    if not human_manager.review_queue.empty():
        print(f"Queue size: {human_manager.review_queue.qsize()}")
        # Get item from queue (don't remove)
        queued_review = await human_manager.review_queue.get()
        print(f"First in queue: {queued_review.request_id}")
        # Put it back
        await human_manager.review_queue.put(queued_review)
    else:
        print("Queue is empty!")

    # Simulate human review
    print("\n=== SIMULATING HUMAN REVIEW ===")

    # Option 1: Approve
    decision = await human_manager.submit_review_decision(
        request_id=review.request_id,
        decision="approve",
        notes="Items match inventory with acceptable confidence. Process order.",
    )

    print(f"Decision result: {json.dumps(decision, indent=2)}")

    # Check statistics
    stats = human_manager.get_review_statistics()
    print("\n=== FINAL STATISTICS ===")
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(test_direct_human_review())
