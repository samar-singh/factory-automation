#!/usr/bin/env python3
"""Simple test for human review system"""

import asyncio

from dotenv import load_dotenv

from factory_automation.factory_agents.human_interaction_manager import (
    HumanInteractionManager,
)
from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient

# Load environment
load_dotenv()


async def test_human_review():
    """Test the human review system"""
    print("🧪 Testing Human Review System\n")

    # Initialize components
    print("1️⃣ Initializing components...")
    manager = HumanInteractionManager()
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client=chromadb_client)

    # Test email
    test_email_data = {
        "id": "test-001",
        "from": "test@example.com",
        "to": "orders@company.com",
        "subject": "Test Order for Human Review",
        "body": """Please provide:
- 100 pieces of unknown tag XYZ123
- 50 pieces of random label ABC456

Thanks!""",
        "attachments": [],
    }

    print("2️⃣ Processing test email through orchestrator...")
    result = await orchestrator.process_email(test_email_data)
    print(f"Result: {result}\n")

    # Check review queue
    print("3️⃣ Checking review queue...")
    reviews = await manager.get_pending_reviews()
    print(f"Found {len(reviews)} pending reviews")

    if reviews:
        review = reviews[0]
        print("\n📋 Review Details:")
        print(f"ID: {review.request_id}")
        print(f"Customer: {review.customer_email}")
        print(f"Subject: {review.subject}")
        print(f"Confidence: {review.confidence_score:.1%}")
        print(f"Status: {review.status.value}")
        print(f"Items: {review.items}")

        # Simulate human decision
        print("\n4️⃣ Simulating human decision (defer)...")
        decision_result = await manager.submit_review_decision(
            request_id=review.request_id,
            decision="defer",
            notes="Need more information about these tags",
        )
        print(f"Decision result: {decision_result}")

        # Check queue again
        print("\n5️⃣ Checking queue after defer...")
        reviews_after = await manager.get_pending_reviews()
        print(f"Reviews in queue: {len(reviews_after)}")

        if reviews_after:
            print(f"First review status: {reviews_after[0].status.value}")
    else:
        print("❌ No reviews created - check if confidence threshold is working")


if __name__ == "__main__":
    asyncio.run(test_human_review())
